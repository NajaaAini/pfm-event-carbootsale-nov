import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime
from style import apply_style
from components import page_header, load_sheet_safe, log_action

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
COL_ADDON = "ADD ON"

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
    if raw is None or pd.isna(raw):
        return ""
    s = str(raw).strip()
    s = s.lstrip("'")
    if s.endswith(".0"):
        s = s[:-2]
    return s.strip()


def normalize_phone(raw):
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
# HELPER — HARGA
# ============================================================
def get_category_price(vendor_type):
    try:
        if vendor_type == "Car Boot Sales":
            return float(st.secrets["event"]["price_car_boot"])
        elif vendor_type == "F&B":
            return float(st.secrets["event"]["price_fb"])
        else:
            return float(st.secrets["event"]["price_others"])
    except Exception:
        return 0.0


def get_deposit(vendor_type):
    """Deposit refundable — F&B + Others."""
    try:
        if vendor_type == "F&B":
            return float(st.secrets["event"]["deposit_fb"])
        elif vendor_type == "Arts & Crafts / Toys":
            return float(st.secrets["event"].get("deposit_others", 100))
        return 0.0
    except Exception:
        return 0.0


def get_addon_price(addon_str):
    """Sokong format 'RM 18' ATAU nombor mentah '18'."""
    if addon_str is None or pd.isna(addon_str):
        return 0.0
    s = str(addon_str).strip()
    if s == "":
        return 0.0
    try:
        matches = re.findall(r"RM\s*([0-9]+(?:\.[0-9]+)?)", s, flags=re.IGNORECASE)
        if matches:
            return sum(float(m) for m in matches)
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def format_rm(amount):
    try:
        return f"RM {float(amount):,.2f}"
    except (ValueError, TypeError):
        return "RM 0.00"


def get_vendor_total(vendor_type, addon_str):
    """Total untuk 1 vendor."""
    return get_category_price(vendor_type) + get_deposit(vendor_type) + get_addon_price(addon_str)


# ============================================================
# SAMBUNGAN DATA
# ============================================================
conn = st.connection("gsheets", type=GSheetsConnection)
df = load_sheet_safe(conn, "Vendors", ttl=60)

if df is None:
    st.stop()

df["Paid"] = df["Paid"].fillna(False).astype(bool)
df["Status"] = df["Status"].apply(normalize_status)

if COL_PHONE in df.columns:
    df[COL_PHONE] = df[COL_PHONE].apply(clean_phone_raw)

if "Notes" not in df.columns:
    df["Notes"] = ""
df["Notes"] = df["Notes"].astype("object").fillna("").astype(str)

# ============================================================
# LOAD PAYMENTS
# ============================================================
payments_df = load_sheet_safe(conn, "Payments", ttl=60)
if payments_df is None or payments_df.empty:
    payments_df = pd.DataFrame(
        columns=["Timestamp", "Plate Number", PROOF_COL, "FolderUrl",
                 "Pilih parking lot", "Pilih F&B Lot"]
    )

for col in ["Timestamp", "Plate Number", PROOF_COL, "FolderUrl",
            "Pilih parking lot", "Pilih F&B Lot"]:
    if col not in payments_df.columns:
        payments_df[col] = ""

payments_df["_plate_norm"] = (
    payments_df["Plate Number"].astype(str).str.upper().str.replace(" ", "")
)


def _clean_payment_val(v):
    """Bersihkan value dari Sheet Payments — buang nan/none."""
    if v is None or pd.isna(v):
        return ""
    s = str(v).strip()
    if s.lower() in ("nan", "none", "nat", "null"):
        return ""
    return s


def _pick_col(df_, *candidates):
    """Cari nama kolum pertama yang wujud (case-insensitive, abaikan spasi)."""
    norm = {str(c).strip().lower().replace(" ", ""): c for c in df_.columns}
    for cand in candidates:
        key = cand.strip().lower().replace(" ", "")
        if key in norm:
            return norm[key]
    return None


def get_vendor_payment_info(plate):
    """Return dict info payment terkini untuk plate."""
    normalized = str(plate).upper().replace(" ", "")
    matched = payments_df[payments_df["_plate_norm"] == normalized]

    if matched.empty:
        return {
            "proof_url": "",
            "folder_url": "",
            "timestamp": "",
            "parking_lot": "",
            "fnb_lot": "",
        }

    try:
        matched = matched.sort_values("Timestamp", ascending=False)
    except Exception:
        pass

    latest = matched.iloc[0]

    # Cari nama kolum sebenar dalam Sheet Payments
    col_proof   = _pick_col(payments_df, PROOF_COL, "Upload Bukti Bayaran", "Bukti Bayaran")
    col_folder  = _pick_col(payments_df, "FolderUrl", "Folder URL")
    col_ts      = _pick_col(payments_df, "Timestamp", "Tarikh")
    col_parking = _pick_col(payments_df, "Pilih parking lot", "Parking Lot", "Parking")
    col_fnb     = _pick_col(payments_df, "Pilih F&B Lot", "F&B Lot", "FNB Lot", "F&B")

    def _get(col):
        if col is None:
            return ""
        return _clean_payment_val(latest.get(col, ""))

    return {
        "proof_url":   _get(col_proof),
        "folder_url":  _get(col_folder),
        "timestamp":   _get(col_ts),
        "parking_lot": _get(col_parking),
        "fnb_lot":     _get(col_fnb),
    }


# Backward-compat
def get_vendor_proof(plate):
    info = get_vendor_payment_info(plate)
    return info["proof_url"], info["folder_url"], info["timestamp"]


# ============================================================
# FUNGSI BANTUAN — kiraan kuota
# ============================================================
def count_approved(**filters):
    mask = pd.Series(True, index=df.index)
    for col, val in filters.items():
        mask &= (df[col] == val)
    mask &= (df["Status"] == "Approved")
    return df[mask].shape[0]


def count_pending(**filters):
    mask = pd.Series(True, index=df.index)
    for col, val in filters.items():
        mask &= (df[col] == val)
    mask &= (df["Status"] == "Pending")
    return df[mask].shape[0]


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


def others_approved():
    mask = ~df[COL_TYPE].isin([CAT_CARBOOT, CAT_FB])
    mask &= (df["Status"] == "Approved")
    return df[mask].shape[0]


def others_pending():
    mask = ~df[COL_TYPE].isin([CAT_CARBOOT, CAT_FB])
    mask &= (df["Status"] == "Pending")
    return df[mask].shape[0]


def safe_update(conn, df):
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
            "1️⃣ Dashboard",
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
        if st.button("Ya, Luluskan", type="primary", use_container_width=True, key="dlg_approve_yes"):
            df.loc[df[COL_PLATE] == plate, "Status"] = "Approved"
            df.loc[df[COL_PLATE] == plate, "Notes"] = ""
            safe_update(conn, df)
            log_action(conn, ADMIN_NAME, "APPROVE", plate, f"Lulus: {vendor_name}")
            st.toast(f"✅ {plate} telah diluluskan", icon="✅")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True, key="dlg_approve_no"):
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
        if st.button("Ya, Tolak", type="primary", use_container_width=True, key="dlg_reject_yes"):
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
        if st.button("Batal", use_container_width=True, key="dlg_reject_no"):
            st.rerun()


@st.dialog("Sahkan Pembatalan")
def confirm_cancel_all_dialog(count):
    st.warning(f"Anda akan membatalkan **{count}** vendor yang belum bayar.")
    st.write("Tindakan ini tidak boleh diundur.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Batalkan Semua", type="primary", use_container_width=True, key="dlg_cancel_yes"):
            df.loc[(df["Status"] == "Approved") & (~df["Paid"]), "Status"] = "Cancelled"
            safe_update(conn, df)
            log_action(conn, ADMIN_NAME, "CANCEL_ALL", "-", f"{count} vendor dibatalkan")
            st.toast(f"✅ {count} vendor telah dibatalkan", icon="✅")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True, key="dlg_cancel_no"):
            st.rerun()


@st.dialog("Edit Maklumat Vendor")
def edit_vendor_dialog(plate):
    vendor = df[df[COL_PLATE] == plate].iloc[0]
    st.caption(f"Mengedit vendor: **{plate}**")

    new_name = st.text_input("Nama", value=str(vendor.get(COL_NAME, "")), key="edit_name")
    new_phone = st.text_input(
        "Telefon",
        value=format_phone_display(vendor.get(COL_PHONE, "")),
        help="Boleh tulis 0123456789 atau 012-345 6789.",
        key="edit_phone",
    )

    type_options = ["Car Boot Sales", "F&B", "Arts & Crafts / Toys"]
    current_type = str(vendor.get(COL_TYPE, "Car Boot Sales"))
    type_index = type_options.index(current_type) if current_type in type_options else 0
    new_type = st.selectbox("Kategori Produk", options=type_options, index=type_index, key="edit_type")

    if new_type == "F&B":
        current_cat = str(vendor.get(COL_CAT, ""))
        cat_index = FB_CATEGORIES.index(current_cat) if current_cat in FB_CATEGORIES else 0
        new_cat = st.selectbox("F&B Category", options=FB_CATEGORIES, index=cat_index, key="edit_cat")
    else:
        new_cat = ""

    new_plate = st.text_input("No. Plate", value=str(vendor.get(COL_PLATE, "")), key="edit_plate")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Simpan", type="primary", use_container_width=True, key="edit_save"):
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
        if st.button("Batal", use_container_width=True, key="edit_cancel"):
            st.rerun()


@st.dialog("Sahkan Padam")
def confirm_delete_dialog(plate, vendor_name):
    st.warning("Anda akan **memadam** rekod vendor ini:")
    st.markdown(f"**No. Plate:** `{plate}`  \n**Nama:** {vendor_name}")
    st.write("")
    st.error("⚠️ **Tindakan ini tidak boleh diundur.** Data akan dibuang dari Google Sheet.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Padam", type="primary", use_container_width=True, key="dlg_delete_yes"):
            global df
            df = df[df[COL_PLATE] != plate].reset_index(drop=True)
            safe_update(conn, df)
            log_action(conn, ADMIN_NAME, "DELETE", plate, f"Padam: {vendor_name}")
            st.toast(f"🗑️ {plate} telah dipadam", icon="🗑️")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True, key="dlg_delete_no"):
            st.rerun()


# ============================================================
# 📞 WHATSAPP GROUP — ATAS PAGE
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
# SECTION 1 — DASHBOARD
# ============================================================
if show_section("1️⃣ Dashboard"):
    st.markdown("## 1️⃣ Dashboard")
    with st.expander("🔍 DEBUG — Total Price Breakdown", expanded=False):
    st.write("**Secrets `event`:**", dict(st.secrets["event"]))

    test_row = df.iloc[0] if not df.empty else None
    if test_row is not None:
        v_type = test_row.get(COL_TYPE, "")
        v_addon = test_row.get(COL_ADDON, "")
        st.write("**Sample vendor:**", test_row.get(COL_NAME, ""))
        st.write("**Kategori (raw):**", repr(v_type))
        st.write("**ADD ON (raw):**", repr(v_addon))
        st.write("**Category price:**", get_category_price(v_type))
        st.write("**Deposit:**", get_deposit(v_type))
        st.write("**Addon price:**", get_addon_price(v_addon))
        st.write("**TOTAL:**", get_vendor_total(v_type, v_addon))
        

    cb_approved = count_approved(**{COL_TYPE: CAT_CARBOOT})
    fb_approved = count_approved(**{COL_TYPE: CAT_FB})
    ot_approved = others_approved()

    cb_pending = count_pending(**{COL_TYPE: CAT_CARBOOT})
    fb_pending = count_pending(**{COL_TYPE: CAT_FB})
    ot_pending = others_pending()

    total_approved = cb_approved + fb_approved + ot_approved
    total_pending = cb_pending + fb_pending + ot_pending
    total_limit = CAR_BOOT_LIMIT + FB_OVERALL_LIMIT + OTHERS_LIMIT

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Car Boot",
        f"{cb_approved} / {CAR_BOOT_LIMIT}",
        f"⏳ {cb_pending} pending" if cb_pending > 0 else None,
        delta_color="off",
    )
    c2.metric(
        "F&B",
        f"{fb_approved} / {FB_OVERALL_LIMIT}",
        f"⏳ {fb_pending} pending" if fb_pending > 0 else None,
        delta_color="off",
    )
    c3.metric(
        "Others",
        f"{ot_approved} / {OTHERS_LIMIT}",
        f"⏳ {ot_pending} pending" if ot_pending > 0 else None,
        delta_color="off",
    )
    c4.metric(
        "TOTAL",
        f"{total_approved} / {total_limit}",
        f"⏳ {total_pending} pending" if total_pending > 0 else None,
        delta_color="off",
    )

    cb_committed = cb_approved + cb_pending
    fb_committed = fb_approved + fb_pending
    ot_committed = ot_approved + ot_pending
    total_committed = total_approved + total_pending

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

    st.caption(
        f"📅 Tarikh Event: **{EVENT_DATE.strftime('%d %b %Y')}** &nbsp;|&nbsp; "
        f"✅ = Approved &nbsp; ⏳ = Pending"
    )

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
            "Status": status_text, "Kategori": cat, "Approved": a, "Pending": p,
            "Total": committed_n, "Limit": FB_CATEGORY_LIMIT, "Slot Baki": left,
        })

    fb_df = pd.DataFrame(rows)
    st.dataframe(fb_df, hide_index=True, use_container_width=True)

    try:
        import plotly.express as px
        approved_fb = df[(df[COL_TYPE] == CAT_FB) & (df["Status"] == "Approved")]
        if not approved_fb.empty:
            st.markdown("**Kategori F&B (Approved)**")
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
# SECTION 3 — PERMOHONAN MENUNGGU (CARD VIEW)
# ============================================================
if show_section("3️⃣ Permohonan Menunggu"):
    st.markdown("## 3️⃣ Permohonan Menunggu")
    st.caption("Semak & luluskan permohonan vendor baru.")

    pending_df = df[df["Status"] == "Pending"]

    if pending_df.empty:
        st.info("Tiada permohonan yang menunggu.")
    else:
        f_col1, f_col2 = st.columns([2, 2])

        with f_col1:
            type_options = ["Semua"] + sorted(pending_df[COL_TYPE].dropna().unique().tolist())
            type_filter = st.selectbox("Kategori", options=type_options, key="pending_type_filter")

        with f_col2:
            search_query = st.text_input(
                "Cari (No. Plate / Nama / Telefon)",
                placeholder="Contoh: PNL123 atau Nurul",
                key="pending_search"
            ).strip()

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

        st.caption(
            f"Menunjukkan **{len(filtered)}** daripada **{len(pending_df)}** permohonan menunggu. "
            f"(Filter: **{type_filter}**)"
        )

        if filtered.empty:
            st.warning("Tiada permohonan sepadan dengan tapisan anda.")
        else:
            for _, row in filtered.iterrows():
                plate = row[COL_PLATE]
                name = row[COL_NAME]
                v_type = row[COL_TYPE]
                v_cat = row.get(COL_CAT, "")
                phone = format_phone_display(row[COL_PHONE])

                cat_str = f" / {v_cat}" if pd.notna(v_cat) and str(v_cat).strip() else ""

                with st.container(border=True):
                    st.markdown(
                        f"<div style='font-size: 1rem; font-weight: 600; color: #292524; margin-bottom: 0.25rem;'>"
                        f"📋 {plate} — {name}"
                        f"</div>"
                        f"<div style='font-size: 0.9rem; color: #57534e; margin-bottom: 0.15rem;'>"
                        f"{v_type}{cat_str}"
                        f"</div>"
                        f"<div style='font-size: 0.85rem; color: #78716c; margin-bottom: 0.5rem;'>"
                        f"📞 {phone}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    v_total = get_vendor_total(v_type, row.get(COL_ADDON, ""))
                    if v_total > 0:
                        st.caption(f"💰 Total: {format_rm(v_total)}")

                    b1, b2, b3, _ = st.columns([1, 1, 1, 3])

                    with b1:
                        if st.button("✓ Lulus", type="primary", use_container_width=True, key=f"approve_{plate}"):
                            confirm_approve_dialog(plate, name)

                    with b2:
                        if st.button("✗ Tolak", use_container_width=True, key=f"reject_{plate}"):
                            confirm_reject_dialog(plate, name)

                    with b3:
                        if st.button("✎ Edit", use_container_width=True, key=f"edit_{plate}"):
                            edit_vendor_dialog(plate)

    st.divider()


# ============================================================
# SECTION 4 — REKOD BAYARAN (F&B / Car Boot / Others)
# ============================================================
if show_section("4️⃣ Rekod Bayaran"):
    st.markdown("## 4️⃣ Rekod Bayaran")
    st.caption("Tandakan 'Sudah Bayar' untuk vendor yang telah membuat bayaran.")

    approved_df = df[df["Status"] == "Approved"]

    if approved_df.empty:
        st.info("Belum ada vendor yang diluluskan.")
    else:
        # ---------- Ringkasan atas ----------
        total_paid = int(approved_df["Paid"].sum())
        total_unpaid = len(approved_df) - total_paid

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Diluluskan", len(approved_df))
        mc2.metric("Sudah Bayar", total_paid)
        mc3.metric("Belum Bayar", total_unpaid)

        st.markdown("---")

        # ---------- Filter bukti (global) ----------
        payment_filter = st.selectbox(
            "Filter Bukti",
            options=["Semua", "Belum Upload Bukti", "Sudah Upload Bukti"],
            key="payment_filter",
        )

        def apply_proof_filter(d):
            if payment_filter == "Belum Upload Bukti":
                return d[~d[COL_PLATE].apply(lambda p: bool(get_vendor_payment_info(p)["proof_url"]))]
            if payment_filter == "Sudah Upload Bukti":
                return d[d[COL_PLATE].apply(lambda p: bool(get_vendor_payment_info(p)["proof_url"]))]
            return d

        # ---------- Pecahan kategori ----------
        fb_df_approved = approved_df[approved_df[COL_TYPE] == CAT_FB]
        cb_df_approved = approved_df[approved_df[COL_TYPE] == CAT_CARBOOT]
        ot_df_approved = approved_df[~approved_df[COL_TYPE].isin([CAT_CARBOOT, CAT_FB])]

        # ---------- Fungsi render satu kategori ----------
        def render_payment_section(title, icon, section_df, key_prefix):
            st.markdown(f"### {icon} {title}")

            section_df = apply_proof_filter(section_df)

            if section_df.empty:
                st.info(f"Tiada vendor {title} untuk dipaparkan.")
                st.markdown("")
                return

            n_paid = int(section_df["Paid"].sum())
            n_unpaid = len(section_df) - n_paid
            st.caption(
                f"**{len(section_df)}** vendor — ✅ {n_paid} bayar &nbsp;|&nbsp; ⏳ {n_unpaid} belum bayar"
            )

            new_paid_status = {}

            with st.form(f"payment_form_{key_prefix}"):
                for _, row in section_df.iterrows():
                    plate = row[COL_PLATE]
                    info = get_vendor_payment_info(plate)

                    proof_url   = info["proof_url"]
                    folder_url  = info["folder_url"]
                    parking_lot = info["parking_lot"]
                    fnb_lot     = info["fnb_lot"]

                    v_t = str(row.get(COL_TYPE, "")).strip()
                    v_total = get_vendor_total(v_t, row.get(COL_ADDON, ""))

                    cols = st.columns([3, 2, 1, 1])

                    # --- Kolum 0: nama + plate ---
                    with cols[0]:
                        status_icon = "✅" if proof_url else "⬜"
                        sub = str(row.get(COL_CAT, "")).strip()
                        sub_str = f" / {sub}" if sub else ""
                        st.markdown(
                            f"{status_icon} **{plate}** — {row[COL_NAME]}  \n"
                            f"<span style='color:#78716c;font-size:0.85rem'>"
                            f"{row[COL_TYPE]}{sub_str}</span>",
                            unsafe_allow_html=True,
                        )

                    # --- Kolum 1: bukti + lot ---
                    with cols[1]:
                        if proof_url:
                            st.markdown(f"[📄 Bukti]({proof_url})")
                            if folder_url:
                                st.markdown(f"[📁 Folder]({folder_url})")
                        else:
                            st.caption("_Belum upload_")

                        if parking_lot:
                            st.caption(f"🅿️ Parking: **{parking_lot}**")
                        if fnb_lot:
                            st.caption(f"🍽️ F&B Lot: **{fnb_lot}**")

                    # --- Kolum 2: total ---
                    with cols[2]:
                        st.markdown(f"**{format_rm(v_total)}**")

                    # --- Kolum 3: checkbox ---
                    with cols[3]:
                        new_val = st.checkbox(
                            "Sudah Bayar",
                            value=bool(row["Paid"]),
                            key=f"paid_{key_prefix}_{plate}",
                        )
                        new_paid_status[plate] = new_val

                    st.markdown(
                        "<hr style='margin:0.75rem 0;border:none;border-top:1px solid #f0e6d6;'>",
                        unsafe_allow_html=True,
                    )

                save_clicked = st.form_submit_button(
                    f"💾 Simpan Status Bayaran — {title}",
                    type="primary",
                    use_container_width=True,
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
                                f"{'Tanda' if is_paid else 'Buang tanda'} bayaran ({title})",
                            )

                    if changed > 0:
                        safe_update(conn, df)
                        st.toast(f"✅ {changed} rekod {title} dikemaskini", icon="💾")
                    else:
                        st.toast("Tiada perubahan", icon="ℹ️")
                    st.rerun()

            st.markdown("")

        # ---------- Render 3 section ----------
        render_payment_section("F&B", "🍽️", fb_df_approved, "fb")
        st.divider()

        render_payment_section("Car Boot Sales", "🚗", cb_df_approved, "cb")
        st.divider()

        render_payment_section("Others (Arts & Crafts / Toys)", "🎨", ot_df_approved, "ot")

    st.divider()


# ============================================================
# SECTION 5 — SEMUA VENDOR
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

    st.markdown("**Status**")
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

    # ============================================================
    # BINA CSV KHAS UNTUK DOWNLOAD
    # - Buang kolum tak perlu
    # - Tambah Parking Lot & F&B Lot dari Sheet Payments
    # ============================================================
    drop_exact = {
        "Media Sosial Perniagaan (Jika Ada)",
        "Senarai Produk yang Dijual\nListkan:\n1. baju\n2. seluar",
        "Notes",
    }
    drop_contains = [
        "Media Sosial Perniagaan",
        "Senarai Produk yang Dijual\nListkan",
    ]

    def _should_drop(col_name):
        if col_name in drop_exact:
            return True
        for pat in drop_contains:
            if pat in str(col_name):
                return True
        if str(col_name).strip() == "Notes":
            return True
        return False

    csv_df = filtered_all.copy()

    # Tambah Parking Lot & F&B Lot ikut plate
    csv_df["Parking Lot"] = csv_df[COL_PLATE].apply(
        lambda p: get_vendor_payment_info(p)["parking_lot"]
    )
    csv_df["F&B Lot"] = csv_df[COL_PLATE].apply(
        lambda p: get_vendor_payment_info(p)["fnb_lot"]
    )

    # Buang kolum tak perlu
    csv_df = csv_df[[c for c in csv_df.columns if not _should_drop(c)]]

    # Format phone supaya cantik dalam CSV
    if COL_PHONE in csv_df.columns:
        csv_df[COL_PHONE] = csv_df[COL_PHONE].apply(format_phone_display)

    csv_all = csv_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "📥 Muat Turun CSV (Semua Vendor)",
        data=csv_all,
        file_name=f"vendors_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )
