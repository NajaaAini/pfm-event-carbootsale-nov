import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime
from style import apply_style
from components import page_header, load_sheet_safe, log_action, convert_df_to_csv

st.set_page_config(page_title="Admin Panel", layout="wide")
apply_style()

# ============================================================
# SEMAKAN LOG MASUK
# ============================================================
if not st.session_state.get("is_admin", False):
    st.error("Sila log masuk di sidebar kiri.")
    st.stop()

page_header()

ADMIN_NAME = st.session_state.get("admin_name", "Admin")

# ============================================================
# KONFIGURASI
# ============================================================
CAR_BOOT_LIMIT = st.secrets["event"]["total_car_boot"]
FB_OVERALL_LIMIT = st.secrets["event"]["total_fb"]
FB_CATEGORY_LIMIT = st.secrets["event"]["fb_per_category"]
OTHERS_LIMIT = st.secrets["event"]["total_others"]
EVENT_DATE = date.fromisoformat(st.secrets["event"]["event_date"])
PAYMENT_DEADLINE_DAYS = 2

FB_CATEGORIES = [
    "Local Food", "Dessert", "Coffee/Air", "Grill and BBQ",
    "Deep-Fry", "Italian/Western Food", "Japanese Food", "Chinese Food",
]

COL_NAME = "Nama/Name"
COL_PHONE = "Nombor Telefon/Phone Number"
COL_TYPE = "Kategori Produk/Product Category"
COL_CAT = "F&B CATEGORY"
COL_PLATE = "Plate Number"

PROOF_COL = "Upload Bukti Bayaran"

VALID_STATUSES = ["Pending", "Approved", "Rejected", "Cancelled"]

CAT_CARBOOT = "Car Boot Sales"
CAT_FB = "F&B"


# ============================================================
# HELPER — Normalize Status & Phone
# ============================================================
def normalize_status(raw):
    if raw is None or pd.isna(raw) or str(raw).strip() == "":
        return "Pending"
    s = str(raw).strip().title()
    aliases = {
        "Menunggu": "Pending", "Waiting": "Pending", "New": "Pending",
        "Approve": "Approved", "Reject": "Rejected",
        "Cancel": "Cancelled", "Canceled": "Cancelled",
    }
    s = aliases.get(s, s)
    return s if s in VALID_STATUSES else "Pending"


def clean_phone_raw(raw):
    """Bersihkan nombor telefon — buang petik, .0."""
    if raw is None or pd.isna(raw):
        return ""
    s = str(raw).strip()
    s = s.lstrip("'")
    if s.endswith(".0"):
        s = s[:-2]
    return s.strip()


def normalize_phone(raw):
    """Normalize untuk WhatsApp — tambah 60 depan."""
    if raw is None or pd.isna(raw):
        return ""
    digits = "".join(filter(str.isdigit, str(raw)))
    if not digits:
        return ""
    digits = digits.lstrip("0")
    if digits.startswith("60") and len(digits) >= 11:
        return digits
    if digits.startswith("1") and len(digits) >= 9:
        return "60" + digits
    return "60" + digits if not digits.startswith("60") else digits


def format_phone_display(raw):
    """Format untuk display — 011-2363 6997."""
    cleaned = clean_phone_raw(raw)
    if not cleaned:
        return "-"

    if cleaned.startswith("0") and cleaned[1:].isdigit():
        digits = cleaned
    else:
        digits = "".join(filter(str.isdigit, cleaned))
        if digits.startswith("60"):
            digits = "0" + digits[2:]
        elif digits.startswith("1"):
            digits = "0" + digits

    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]} {digits[7:]}"
    elif len(digits) == 10:
        return f"{digits[:2]}-{digits[2:6]} {digits[6:]}"
    return digits


# ============================================================
# SAMBUNGAN DATA
# ============================================================
conn = st.connection("gsheets", type=GSheetsConnection)
df = load_sheet_safe(conn, "Vendors", ttl=60)

if df is None:
    st.stop()

df["Paid"] = df["Paid"].fillna(False).astype(bool)
df["Status"] = df["Status"].apply(normalize_status)

# FIX: Paksa column telefon jadi string bersih
if COL_PHONE in df.columns:
    df[COL_PHONE] = df[COL_PHONE].apply(clean_phone_raw)

# FIX: Pastikan Notes wujud + dtype string
if "Notes" not in df.columns:
    df["Notes"] = ""
df["Notes"] = df["Notes"].astype("object").fillna("").astype(str)

# ============================================================
# LOAD PAYMENTS
# ============================================================
payments_df = load_sheet_safe(conn, "Payments", ttl=60)
if payments_df is None or payments_df.empty:
    payments_df = pd.DataFrame(
        columns=["Timestamp", "Plate Number", PROOF_COL, "FolderUrl"]
    )

for col in ["Timestamp", "Plate Number", PROOF_COL, "FolderUrl"]:
    if col not in payments_df.columns:
        payments_df[col] = ""

payments_df["_plate_norm"] = (
    payments_df["Plate Number"].astype(str).str.upper().str.replace(" ", "")
)


def get_vendor_proof(plate):
    normalized = str(plate).upper().replace(" ", "")
    matched = payments_df[payments_df["_plate_norm"] == normalized]
    if matched.empty:
        return "", "", ""
    try:
        matched = matched.sort_values("Timestamp", ascending=False)
    except Exception:
        pass
    latest = matched.iloc[0]
    return (
        str(latest.get(PROOF_COL, "") or ""),
        str(latest.get("FolderUrl", "") or ""),
        str(latest.get("Timestamp", "") or ""),
    )


# ============================================================
# FUNGSI BANTUAN
# ============================================================
def committed(**filters):
    mask = pd.Series(True, index=df.index)
    for col, val in filters.items():
        mask &= (df[col] == val)
    mask &= df["Status"].isin(["Approved", "Pending"])
    return df[mask].shape[0]


def others_committed():
    mask = ~df[COL_TYPE].isin([CAT_CARBOOT, CAT_FB])
    mask &= df["Status"].isin(["Approved", "Pending"])
    return df[mask].shape[0]


def safe_update(conn, df):
    """Update Sheet dengan paksa Notes + Phone jadi string."""
    if "Notes" in df.columns:
        df["Notes"] = df["Notes"].astype("object").fillna("").astype(str)
    if COL_PHONE in df.columns:
        df[COL_PHONE] = df[COL_PHONE].astype("object").fillna("").astype(str)
    conn.update(data=df)


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================
with st.sidebar:
    st.markdown("---")
    section = st.radio(
        "Pergi ke:",
        options=[
            "🏠 Semua Section",
            "1️⃣ Papan Pemantauan Kuota",
            "2️⃣ Tarikh Akhir Bayaran",
            "3️⃣ Pendaftaran Baru",
            "4️⃣ Rekod Bayaran",
        ],
        label_visibility="collapsed",
        key="admin_nav",
    )
    st.markdown("---")

show_all = section == "🏠 Semua Section"


def show_section(label):
    return show_all or section == label


# ============================================================
# DIALOG PENGESAHAN
# ============================================================
@st.dialog("Sahkan Tindakan")
def confirm_approve_dialog(plate, vendor_name):
    st.write("Anda akan **meluluskan** permohonan ini:")
    st.markdown(f"**No. Plate:** `{plate}`  \n**Nama:** {vendor_name}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Luluskan", type="primary", use_container_width=True):
            df.loc[df[COL_PLATE] == plate, "Status"] = "Approved"
            df.loc[df[COL_PLATE] == plate, "Notes"] = ""
            safe_update(conn, df)
            log_action(conn, ADMIN_NAME, "APPROVE", plate, f"Lulus: {vendor_name}")
            st.toast(f"✅ {plate} telah diluluskan", icon="✅")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()


@st.dialog("Sahkan Tindakan")
def confirm_reject_dialog(plate, vendor_name):
    st.write("Anda akan **menolak** permohonan ini:")
    st.markdown(f"**No. Plate:** `{plate}`  \n**Nama:** {vendor_name}")

    existing_row = df[df[COL_PLATE] == plate]
    existing_reason = ""
    if not existing_row.empty:
        existing_val = existing_row.iloc[0].get("Notes", "")
        if pd.notna(existing_val) and str(existing_val).strip():
            existing_reason = str(existing_val).strip()

    reject_reason = st.text_area(
        "Sebab Penolakan (vendor akan nampak)",
        value=existing_reason,
        placeholder="Contoh: Slot kategori anda telah penuh.",
        height=120,
        key=f"reject_reason_{plate}",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Tolak", type="primary", use_container_width=True):
            if not reject_reason.strip():
                st.warning("⚠️ Sila masukkan sebab penolakan.")
            else:
                df.loc[df[COL_PLATE] == plate, "Status"] = "Rejected"
                df.loc[df[COL_PLATE] == plate, "Notes"] = reject_reason.strip()
                safe_update(conn, df)
                log_action(
                    conn, ADMIN_NAME, "REJECT", plate,
                    f"Tolak: {vendor_name} — Sebab: {reject_reason[:100]}"
                )
                st.toast(f"❌ {plate} telah ditolak", icon="❌")
                st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()


@st.dialog("Sahkan Pembatalan")
def confirm_cancel_all_dialog(count):
    st.warning(f"Anda akan membatalkan **{count}** vendor yang belum bayar.")
    st.write("Tindakan ini tidak boleh diundur.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Batalkan Semua", type="primary", use_container_width=True):
            df.loc[(df["Status"] == "Approved") & (~df["Paid"]), "Status"] = "Cancelled"
            safe_update(conn, df)
            log_action(conn, ADMIN_NAME, "CANCEL_ALL", "-", f"{count} vendor dibatalkan")
            st.toast(f"✅ {count} vendor telah dibatalkan", icon="✅")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()


@st.dialog("Edit Maklumat Vendor")
def edit_vendor_dialog(plate):
    vendor = df[df[COL_PLATE] == plate].iloc[0]
    st.caption(f"Mengedit vendor: **{plate}**")

    new_name = st.text_input("Nama", value=str(vendor.get(COL_NAME, "")))
    new_phone = st.text_input(
        "Telefon",
        value=format_phone_display(vendor.get(COL_PHONE, "")),
        help="Boleh tulis 0123456789 atau 012-345 6789.",
    )

    type_options = ["Car Boot Sales", "F&B", "Arts & Crafts / Toys"]
    current_type = str(vendor.get(COL_TYPE, "Car Boot Sales"))
    type_index = type_options.index(current_type) if current_type in type_options else 0
    new_type = st.selectbox("Kategori Produk", options=type_options, index=type_index)

    if new_type == "F&B":
        current_cat = str(vendor.get(COL_CAT, ""))
        cat_index = FB_CATEGORIES.index(current_cat) if current_cat in FB_CATEGORIES else 0
        new_cat = st.selectbox("F&B Category", options=FB_CATEGORIES, index=cat_index)
    else:
        new_cat = ""

    new_plate = st.text_input("No. Plate", value=str(vendor.get(COL_PLATE, "")))

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Simpan", type="primary", use_container_width=True):
            idx = df[df[COL_PLATE] == plate].index[0]
            df.at[idx, COL_NAME] = new_name
            df.at[idx, COL_PHONE] = clean_phone_raw(new_phone)
            df.at[idx, COL_TYPE] = new_type
            df.at[idx, COL_CAT] = new_cat
            df.at[idx, COL_PLATE] = new_plate

            safe_update(conn, df)
            log_action(conn, ADMIN_NAME, "EDIT", plate, f"Nama: {new_name}, Plate: {new_plate}")
            st.toast(f"✅ {plate} telah dikemaskini", icon="✅")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()


@st.dialog("Sahkan Padam")
def confirm_delete_dialog(plate, vendor_name):
    st.warning("Anda akan **memadam** rekod vendor ini:")
    st.markdown(f"**No. Plate:** `{plate}`  \n**Nama:** {vendor_name}")
    st.write("")
    st.error("⚠️ **Tindakan ini tidak boleh diundur.** Data akan dibuang dari Google Sheet.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Padam", type="primary", use_container_width=True):
            global df
            df = df[df[COL_PLATE] != plate].reset_index(drop=True)
            safe_update(conn, df)
            log_action(conn, ADMIN_NAME, "DELETE", plate, f"Padam: {vendor_name}")
            st.toast(f"🗑️ {plate} telah dipadam", icon="🗑️")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()


# ============================================================
# 📞 WHATSAPP GROUP — ATAS PAGE (sentiasa nampak)
# ============================================================
try:
    wa_group = st.secrets["event"]["whatsapp_group"]
except Exception:
    wa_group = ""

if wa_group:
    st.markdown(f"""
    <div style="
        background-color: #f2ebe0;
        border: 1px solid #e8dcc7;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    ">
        <div>
            <div style="font-weight: 600; color: #292524; font-size: 1rem;">💬 WhatsApp Group Vendor</div>
            <div style="color: #78716c; font-size: 0.85rem; margin-top: 0.25rem;">Hantar mesej terus dalam group</div>
        </div>
        <a href="{wa_group}" target="_blank" style="
            background-color: #78350f;
            color: #ffffff;
            padding: 0.6rem 1.25rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            white-space: nowrap;
        ">Buka Group →</a>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# SECTION 1 — PAPAN PEMANTAUAN KUOTA
# ============================================================
if show_section("1️⃣ Papan Pemantauan Kuota"):
    st.markdown("## 1️⃣ Papan Pemantauan Kuota")

    cb_committed = committed(**{COL_TYPE: CAT_CARBOOT})
    fb_committed = committed(**{COL_TYPE: CAT_FB})
    ot_committed = others_committed()

    total_committed = cb_committed + fb_committed + ot_committed
    total_limit = CAR_BOOT_LIMIT + FB_OVERALL_LIMIT + OTHERS_LIMIT

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Car Boot", f"{cb_committed} / {CAR_BOOT_LIMIT}")
    c2.metric("F&B", f"{fb_committed} / {FB_OVERALL_LIMIT}")
    c3.metric("Others", f"{ot_committed} / {OTHERS_LIMIT}")
    c4.metric("TOTAL", f"{total_committed} / {total_limit}")

    pc1, pc2, pc3, pc4 = st.columns(4)
    with pc1:
        st.markdown("**Car Boot**")
        st.progress(min(cb_committed / CAR_BOOT_LIMIT, 1.0), text=f"{cb_committed}/{CAR_BOOT_LIMIT}")
    with pc2:
        st.markdown("**F&B**")
        st.progress(min(fb_committed / FB_OVERALL_LIMIT, 1.0), text=f"{fb_committed}/{FB_OVERALL_LIMIT}")
    with pc3:
        st.markdown("**Others**")
        st.progress(min(ot_committed / OTHERS_LIMIT, 1.0), text=f"{ot_committed}/{OTHERS_LIMIT}")
    with pc4:
        st.markdown("**TOTAL**")
        st.progress(min(total_committed / total_limit, 1.0), text=f"{total_committed}/{total_limit}")

    st.caption(f"📅 Tarikh Event: **{EVENT_DATE.strftime('%d %b %Y')}**")

    st.markdown(f"**Pecahan Kategori F&B (had: {FB_CATEGORY_LIMIT} setiap satu)**")

    rows = []
    for cat in FB_CATEGORIES:
        a = df[(df[COL_TYPE] == CAT_FB) & (df[COL_CAT] == cat) & (df["Status"] == "Approved")].shape[0]
        p = df[(df[COL_TYPE] == CAT_FB) & (df[COL_CAT] == cat) & (df["Status"] == "Pending")].shape[0]
        committed_n = a + p
        left = max(0, FB_CATEGORY_LIMIT - committed_n)

        if left == 0:
            status_text = "🔴 Penuh"
        elif left <= 2:
            status_text = "🟡 Hampir Penuh"
        else:
            status_text = "🟢 Tersedia"

        rows.append({
            "Status": status_text, "Kategori": cat, "Diluluskan": a, "Menunggu": p,
            "Total": committed_n, "Limit": FB_CATEGORY_LIMIT, "Slot Baki": left,
        })

    fb_df = pd.DataFrame(rows)
    st.dataframe(fb_df, hide_index=True, use_container_width=True)

    try:
        import plotly.express as px
        approved_fb = df[(df[COL_TYPE] == CAT_FB) & (df["Status"] == "Approved")]
        if not approved_fb.empty:
            st.markdown("**Kategori F&B (Diluluskan)**")
            fig = px.pie(approved_fb, names=COL_CAT, hole=0.4,
                         color_discrete_sequence=px.colors.sequential.Oranges_r)
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
            st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        pass

    st.divider()


# ============================================================
# SECTION 2 — TARIKH AKHIR BAYARAN
# ============================================================
cutoff_date = EVENT_DATE - timedelta(days=PAYMENT_DEADLINE_DAYS)

if show_section("2️⃣ Tarikh Akhir Bayaran"):
    st.markdown("## 2️⃣ Tarikh Akhir Bayaran")
    st.caption(f"Vendor yang belum bayar akan dibatalkan selepas **{cutoff_date.strftime('%d %b %Y')}**.")

    today = date.today()
    if today > cutoff_date:
        expired = df[(df["Status"] == "Approved") & (~df["Paid"])]
        if not expired.empty:
            st.warning(f"{len(expired)} vendor belum membuat bayaran selepas tarikh akhir.")
            expired_display = expired[[COL_PLATE, COL_NAME, COL_PHONE, COL_TYPE, COL_CAT]].copy()
            expired_display[COL_PHONE] = expired_display[COL_PHONE].apply(format_phone_display)
            st.dataframe(expired_display, hide_index=True, use_container_width=True)
            if st.button("Batalkan Semua Yang Belum Bayar", type="primary"):
                confirm_cancel_all_dialog(len(expired))
        else:
            st.success("Semua vendor yang diluluskan telah membuat bayaran.")
    else:
        days_left = (cutoff_date - today).days
        st.info(f"Tarikh akhir — {days_left} hari lagi.")

    st.divider()


# ============================================================
# LINK GOOGLE FORM RESPONSES
# ============================================================
if show_section("3️⃣ Permohonan Menunggu"):
    try:
        form_url = st.secrets["event"].get("google_form_responses_url", "")
    except Exception:
        form_url = ""

    if form_url:
        st.markdown(f"""
        <div style="
            background-color: #f2ebe0;
            border: 1px solid #e8dcc7;
            border-radius: 10px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
        ">
            <div>
                <div style="font-weight: 600; color: #292524; font-size: 0.95rem;">📋 Response Google Form</div>
                <div style="color: #78716c; font-size: 0.85rem; margin-top: 0.25rem;">Buka Responses tab untuk tengok/edit/delete response asal</div>
            </div>
            <a href="{form_url}" target="_blank" style="
                background-color: #78350f;
                color: #ffffff;
                padding: 0.55rem 1.1rem;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                font-size: 0.9rem;
                white-space: nowrap;
            ">Buka Form</a>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# SECTION 3 — PERMOHONAN MENUNGGU (DROPDOWN FILTER)
# ============================================================
if show_section("3️⃣ Permohonan Menunggu"):
    st.markdown("## 3️⃣ Permohonan Menunggu")
    st.caption("Semak & luluskan permohonan vendor baru.")

    pending_df = df[df["Status"] == "Pending"]

    if pending_df.empty:
        st.info("Tiada permohonan yang menunggu.")
    else:
        # === DROPDOWN FILTER KATEGORI ===
        f_col1, f_col2, f_col3 = st.columns([2, 2, 1])

        with f_col1:
            type_options = ["Semua"] + sorted(pending_df[COL_TYPE].dropna().unique().tolist())
            type_filter = st.selectbox(
                "Tapis Kategori Produk",
                options=type_options,
                key="pending_type_filter"
            )

        with f_col2:
            search_query = st.text_input(
                "Cari (No. Plate / Nama / Telefon)",
                placeholder="Contoh: NNA1806 atau Ali",
                key="pending_search"
            ).strip()

        with f_col3:
            sort_options = ["Terbaru", "Terlama", "Nama A-Z"]
            sort_by = st.selectbox("Susun", options=sort_options, key="pending_sort")

        # Apply filter
        filtered = pending_df.copy()

        if type_filter != "Semua":
            filtered = filtered[filtered[COL_TYPE] == type_filter]

        if search_query:
            q = search_query.lower()
            filtered = filtered[
                filtered[COL_PLATE].astype(str).str.lower().str.contains(q, na=False)
                | filtered[COL_NAME].astype(str).str.lower().str.contains(q, na=False)
                | filtered[COL_PHONE].astype(str).str.lower().str.contains(q, na=False)
            ]

        if sort_by == "Terbaru":
            try: filtered = filtered.sort_values("Timestamp", ascending=False)
            except Exception: pass
        elif sort_by == "Terlama":
            try: filtered = filtered.sort_values("Timestamp", ascending=True)
            except Exception: pass
        elif sort_by == "Nama A-Z":
            filtered = filtered.sort_values(COL_NAME, ascending=True)

        st.caption(
            f"Menunjukkan **{len(filtered)}** daripada **{len(pending_df)}** permohonan menunggu. "
            f"(Filter: **{type_filter}**)"
        )

        # Download CSV
        csv_data = convert_df_to_csv(filtered)
        st.download_button(
            "📥 Muat Turun CSV (Senarai Menunggu)",
            data=csv_data,
            file_name=f"pending_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

        if filtered.empty:
            st.warning("Tiada permohonan sepadan dengan tapisan anda.")
        else:
            # === TABLE ===
            display_filtered = filtered[[COL_PLATE, COL_NAME, COL_PHONE, COL_TYPE, COL_CAT]].copy()
            display_filtered[COL_PHONE] = display_filtered[COL_PHONE].apply(format_phone_display)
            st.dataframe(display_filtered, hide_index=True, use_container_width=True)

            st.markdown("---")

            # === URUS SATU-SATU ===
            st.markdown("**Pilih vendor untuk diurus:**")

            selected_plate = st.selectbox(
                "Pilih No. Plate",
                filtered[COL_PLATE].tolist(),
                key="pending_selected"
            )

            if selected_plate:
                vendor = df[df[COL_PLATE] == selected_plate].iloc[0]
                v_type = vendor[COL_TYPE]
                v_cat = vendor.get(COL_CAT, "")

                # Info kuota ikut kategori
                if v_type == CAT_FB:
                    a = df[(df[COL_TYPE] == CAT_FB) & (df[COL_CAT] == v_cat) & (df["Status"] == "Approved")].shape[0]
                    p = df[(df[COL_TYPE] == CAT_FB) & (df[COL_CAT] == v_cat) & (df["Status"] == "Pending")].shape[0]
                    remaining = FB_CATEGORY_LIMIT - (a + p)
                    if remaining > 0:
                        st.info(f"Kategori **{v_cat}**: {remaining} slot lagi.")
                    else:
                        st.warning(f"Kategori **{v_cat}** telah penuh.")
                elif v_type == CAT_CARBOOT:
                    st.info(f"Car Boot Total: {cb_committed} / {CAR_BOOT_LIMIT}")
                else:
                    ot_c = others_committed()
                    st.info(f"Others Total: {ot_c} / {OTHERS_LIMIT}")

                st.markdown(
                    f"**Vendor:** {vendor[COL_NAME]}  \n"
                    f"**Jenis:** {v_type}  \n"
                    f"**Kategori F&B:** {v_cat or '-'}  \n"
                    f"**Telefon:** {format_phone_display(vendor[COL_PHONE])}"
                )

                current_notes = vendor.get("Notes", "") if pd.notna(vendor.get("Notes")) else ""
                new_notes = st.text_area("Nota Admin (pilihan)", value=current_notes, key=f"notes_{selected_plate}")

                c1, c2, c3, c4, c5 = st.columns(5)
                with c1:
                    if st.button("Luluskan", type="primary", use_container_width=True, key=f"approve_{selected_plate}"):
                        ok = True
                        if v_type == CAT_FB:
                            a = df[(df[COL_TYPE] == CAT_FB) & (df[COL_CAT] == v_cat) & (df["Status"] == "Approved")].shape[0]
                            if a >= FB_CATEGORY_LIMIT:
                                st.error(f"Kategori '{v_cat}' telah penuh."); ok = False
                            elif fb_committed >= FB_OVERALL_LIMIT:
                                st.error("F&B keseluruhan telah penuh."); ok = False
                        elif v_type == CAT_CARBOOT:
                            if cb_committed >= CAR_BOOT_LIMIT:
                                st.error("Car Boot telah penuh."); ok = False
                        else:
                            if others_committed() >= OTHERS_LIMIT:
                                st.error("Others telah penuh."); ok = False

                        if ok:
                            confirm_approve_dialog(selected_plate, vendor[COL_NAME])
                with c2:
                    if st.button("Tolak", use_container_width=True, key=f"reject_{selected_plate}"):
                        confirm_reject_dialog(selected_plate, vendor[COL_NAME])
                with c3:
                    if st.button("Edit", use_container_width=True, key=f"edit_{selected_plate}"):
                        edit_vendor_dialog(selected_plate)
                with c4:
                    if st.button("Simpan Nota", use_container_width=True, key=f"savenotes_{selected_plate}"):
                        df.loc[df[COL_PLATE] == selected_plate, "Notes"] = str(new_notes)
                        safe_update(conn, df)
                        st.toast("Nota disimpan", icon="📝")
                        st.rerun()
                with c5:
                    if st.button("Padam", use_container_width=True, key=f"delete_{selected_plate}"):
                        confirm_delete_dialog(selected_plate, vendor[COL_NAME])

    st.divider()


# ============================================================
# SECTION 4 — PEMANTAUAN BAYARAN
# ============================================================
if show_section("4️⃣ Rekod Bayaran"):
    st.markdown("## 4️⃣ Rekod Bayaran")
    st.caption("Tandakan 'Sudah Bayar' untuk vendor yang telah membuat bayaran.")

    col_ref, _ = st.columns([1, 4])
    with col_ref:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    approved_df = df[df["Status"] == "Approved"]

    if approved_df.empty:
        st.info("Belum ada vendor yang diluluskan.")
    else:
        total_approved = len(approved_df)
        total_paid = int(approved_df["Paid"].sum())
        total_unpaid = total_approved - total_paid

        uploaded_count = sum(
            1 for p in approved_df[COL_PLATE] if get_vendor_proof(p)[0]
        )

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Diluluskan", total_approved)
        mc2.metric("Sudah Bayar", total_paid)
        mc3.metric("Belum Bayar", total_unpaid)
        mc4.metric("Bukti Dihantar", uploaded_count)

        st.markdown("---")

        fcol1, fcol2 = st.columns([2, 2])
        with fcol1:
            payment_filter = st.selectbox(
                "Filter",
                options=[
                    "Semua",
                    "Belum Bayar",
                    "Sudah Bayar",
                    "Belum Upload Bukti",
                    "Sudah Upload Bukti",
                ],
                key="payment_filter",
            )
        with fcol2:
            search_payment = st.text_input(
                "Cari (No. Plate / Nama)",
                placeholder="Contoh: NNA1806 atau Ali",
                key="payment_search",
            ).strip().lower()

        if payment_filter == "Belum Bayar":
            view_df = approved_df[~approved_df["Paid"]]
        elif payment_filter == "Sudah Bayar":
            view_df = approved_df[approved_df["Paid"]]
        elif payment_filter == "Belum Upload Bukti":
            view_df = approved_df[
                ~approved_df[COL_PLATE].apply(lambda p: bool(get_vendor_proof(p)[0]))
            ]
        elif payment_filter == "Sudah Upload Bukti":
            view_df = approved_df[
                approved_df[COL_PLATE].apply(lambda p: bool(get_vendor_proof(p)[0]))
            ]
        else:
            view_df = approved_df

        if search_payment:
            view_df = view_df[
                view_df[COL_PLATE].astype(str).str.lower().str.contains(search_payment, na=False)
                | view_df[COL_NAME].astype(str).str.lower().str.contains(search_payment, na=False)
            ]

        st.caption(f"Menunjukkan **{len(view_df)}** daripada **{len(approved_df)}** vendor.")

        if view_df.empty:
            st.info("Tiada vendor sepadan.")
        else:
            with st.form("payment_form"):
                new_paid_status = {}

                for _, row in view_df.iterrows():
                    plate = row[COL_PLATE]
                    proof_url, folder_url, upload_time = get_vendor_proof(plate)

                    cols = st.columns([3, 2, 2, 1])

                    with cols[0]:
                        status_icon = "✅" if proof_url else "⬜"
                        st.markdown(
                            f"{status_icon} **{plate}** — {row[COL_NAME]}  \n"
                            f"<span style='color:#78716c;font-size:0.85rem'>{row[COL_TYPE]}</span>",
                            unsafe_allow_html=True,
                        )

                    with cols[1]:
                        if proof_url:
                            st.markdown(f"[📄 Bukti Bayaran]({proof_url})")
                            if upload_time:
                                st.caption(f"📅 {upload_time}")
                        else:
                            st.caption("_Belum upload bukti_")

                    with cols[2]:
                        if folder_url:
                            st.markdown(f"[📁 Buka Folder]({folder_url})")
                        else:
                            st.caption("—")

                    with cols[3]:
                        new_val = st.checkbox(
                            "Sudah Bayar",
                            value=bool(row["Paid"]),
                            key=f"paid_{plate}",
                        )
                        new_paid_status[plate] = new_val

                    st.markdown(
                        "<hr style='margin:0.75rem 0;border:none;border-top:1px solid #f0e6d6;'>",
                        unsafe_allow_html=True,
                    )

                save_clicked = st.form_submit_button(
                    "💾 Simpan Status Bayaran", type="primary", use_container_width=True
                )

            if save_clicked:
                with st.spinner("Menyimpan..."):
                    changed = 0
                    for plate, is_paid in new_paid_status.items():
                        old_val = bool(df.loc[df[COL_PLATE] == plate, "Paid"].iloc[0])
                        if old_val != is_paid:
                            df.loc[df[COL_PLATE] == plate, "Paid"] = is_paid
                            changed += 1
                            log_action(
                                conn, ADMIN_NAME,
                                "PAID" if is_paid else "UNPAID",
                                plate,
                                f"{'Tanda' if is_paid else 'Buang tanda'} bayaran",
                            )

                    if changed > 0:
                        safe_update(conn, df)
                        st.toast(f"✅ {changed} rekod dikemaskini", icon="💾")
                    else:
                        st.toast("Tiada perubahan", icon="ℹ️")
                    st.rerun()

    st.divider()


# ============================================================
# SECTION 6 — SEMUA VENDOR (PAPAR TERUS, TAKDE EXPANDER)
# ============================================================
if show_all:
    st.markdown("## 5️⃣ Semua Vendor")

    try:
        form_url = st.secrets["event"].get("google_form_responses_url", "")
    except Exception:
        form_url = ""

    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    except Exception:
        sheet_url = ""

    quick_col1, quick_col2 = st.columns(2)
    with quick_col1:
        if form_url:
            st.markdown(f"""
            <a href="{form_url}" target="_blank" style="
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                background-color: #78350f;
                color: #ffffff;
                padding: 0.7rem 1rem;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 600;
                font-size: 0.9rem;
            ">📋 Buka Google Form Responses</a>
            """, unsafe_allow_html=True)

    with quick_col2:
        if sheet_url:
            st.markdown(f"""
            <a href="{sheet_url}" target="_blank" style="
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                background-color: #ffffff;
                color: #78350f;
                padding: 0.7rem 1rem;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 600;
                font-size: 0.9rem;
                border: 1px solid #d6c4a3;
            ">📊 Buka Google Sheet</a>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    st.divider()

    st.markdown("**Tapis mengikut status**")
    status_options = df["Status"].dropna().unique().tolist()
    status_filter = st.multiselect(
        "Tapis mengikut status",
        options=status_options,
        default=status_options,
        label_visibility="collapsed"
    )
    filtered_all = df[df["Status"].isin(status_filter)]

    display_df = filtered_all.copy()
    display_df[COL_PHONE] = display_df[COL_PHONE].apply(format_phone_display)
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    act_col1, act_col2 = st.columns([3, 1])

    with act_col1:
        plate_to_delete = st.selectbox(
            "Pilih No. Plate untuk dipadam",
            options=[""] + filtered_all[COL_PLATE].tolist(),
            key="delete_plate_select"
        )

    with act_col2:
        st.markdown("<div style='height: 1.75rem;'></div>", unsafe_allow_html=True)
        if st.button("🗑️ Padam", type="primary", use_container_width=True):
            if plate_to_delete:
                row = df[df[COL_PLATE] == plate_to_delete]
                name = row.iloc[0][COL_NAME] if not row.empty else "-"
                confirm_delete_dialog(plate_to_delete, name)
            else:
                st.error("Sila pilih No. Plate.")

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    csv_all = convert_df_to_csv(filtered_all)
    st.download_button(
        "📥 Muat Turun CSV (Semua Vendor)",
        data=csv_all,
        file_name=f"vendors_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

    st.divider()

    # ============================================================
    # LOG TINDAKAN ADMIN — PAPAR TERUS
    # ============================================================
    st.markdown("## 6️⃣ Log Tindakan Admin")

    logs = load_sheet_safe(conn, "Log", ttl=60)
    if logs is None or logs.empty:
        st.markdown("""
        <div style="
            background-color: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 10px;
            padding: 1rem 1.25rem;
            color: #0c4a6e;
            font-size: 0.92rem;
        ">
            📭 Belum ada rekod tindakan admin.
        </div>
        """, unsafe_allow_html=True)
    else:
        logs_sorted = logs.sort_values("Timestamp", ascending=False)
        st.dataframe(logs_sorted, hide_index=True, use_container_width=True)

        csv_logs = convert_df_to_csv(logs_sorted)
        st.download_button(
            "📥 Muat Turun Log CSV",
            data=csv_logs,
            file_name=f"log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )
        
