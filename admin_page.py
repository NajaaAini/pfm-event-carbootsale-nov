import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime
from style import apply_style
from components import page_header, load_sheet_safe, log_action

st.set_page_config(page_title="Admin Panel", layout="wide", initial_sidebar_state="expanded")
apply_style()

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    :root {
        --brand: #78350f;
        --brand-soft: #f2ebe0;
        --border: #e5e5e5;
        --text: #1c1917;
        --muted: #78716c;
        --bg-card: #ffffff;
    }

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px;
    }

    [data-testid="stMetric"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem 1.25rem;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: var(--muted) !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 600 !important;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 600;
        color: var(--text);
        margin: 0 0 0.25rem 0;
    }
    .section-sub {
        font-size: 0.85rem;
        color: var(--muted);
        margin: 0 0 1.25rem 0;
    }

    .product-box {
        background: #fafaf9;
        border-left: 3px solid #78350f;
        border-radius: 6px;
        padding: 0.6rem 0.85rem;
        margin: 0.5rem 0 0.6rem 0;
        font-size: 0.85rem;
        color: #44403c;
        white-space: pre-wrap;
        line-height: 1.45;
    }

    .remark-box {
        background: #fef3c7;
        border-left: 3px solid #92400e;
        border-radius: 6px;
        padding: 0.6rem 0.85rem;
        margin: 0.5rem 0 0.6rem 0;
        font-size: 0.85rem;
        color: #44403c;
        white-space: pre-wrap;
        line-height: 1.45;
    }

    .stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        border: 1px solid var(--border) !important;
    }
    .stButton > button[kind="primary"] {
        background: var(--brand) !important;
        color: white !important;
        border: none !important;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: hidden;
    }

    hr {
        margin: 1.25rem 0 !important;
        border-color: var(--border) !important;
    }

    [data-testid="stSidebar"] {
        background: #fafaf9;
        border-right: 1px solid var(--border);
    }
</style>
""", unsafe_allow_html=True)


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
FT_LIMIT = st.secrets["event"]["total_ft"]
FB_CATEGORY_LIMIT = st.secrets["event"]["fb_per_category"]
OTHERS_LIMIT = st.secrets["event"]["total_others"]
EVENT_DATE = date.fromisoformat(st.secrets["event"]["event_date"])
PAYMENT_DEADLINE_DAYS = 2

FB_CATEGORIES = [
    "Local Food", "Dessert", "Coffee/Air", "Grill and BBQ",
    "Deep-Fry", "Italian/Western Food", "Japanese Food", "Chinese Food",
]

COL_NAME = "Nama Perniagaan Syarikat"
COL_PHONE = "Nombor Telefon/Phone Number"
COL_TYPE = "Kategori Produk/Product Category"
COL_CAT = "F&B CATEGORY"
COL_PLATE = "Plate Number"
COL_ADDON = "ADD ON"
COL_PRODUCTS = "Senarai Produk yang Dijual"
COL_REMARK = "Remark"

PROOF_COL = "Upload Bukti Bayaran"

VALID_STATUSES = ["Pending", "Approved", "Rejected", "Cancelled"]

CAT_CARBOOT = "Car Boot Sales"
CAT_FB = "F&B"
CAT_FT = "Food Truck"
CAT_ARTS = "Arts/Crafts & Others"


# ============================================================
# HELPER
# ============================================================
def normalize_type(raw):
    if raw is None or pd.isna(raw):
        return ""
    s = str(raw).strip()
    if s.lower() in ("", "nan", "none", "nat", "null"):
        return ""
    if s.lower() in ("arts & crafts / toys", "arts & crafts", "arts/crafts"):
        return "Arts/Crafts & Others"
    if s.lower() in ("food truck", "foodtruck", "ft"):
        return "Food Truck"
    return s


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
    s = str(raw).strip().lstrip("'")
    if s.endswith(".0"):
        s = s[:-2]
    return s.strip()


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


def clean_cat_str(raw):
    if raw is None or pd.isna(raw):
        return ""
    s = str(raw).strip()
    if s.lower() in ("nan", "none", "nat", "null"):
        return ""
    return s


def clean_products_str(raw):
    if raw is None or pd.isna(raw):
        return ""
    s = str(raw).strip()
    if s.lower() in ("nan", "none", "nat", "null"):
        return ""
    return s


def clean_text(raw):
    if raw is None or pd.isna(raw):
        return ""
    s = str(raw).strip()
    if s.lower() in ("nan", "none", "nat", "null"):
        return ""
    return s


def _get_products_col(df_):
    for c in df_.columns:
        if "Senarai Produk yang Dijual" in str(c):
            return c
    return None


def _normalize_type(v):
    if v is None or pd.isna(v):
        return ""
    return str(v).strip().lower()


def get_category_price(vendor_type):
    vt = _normalize_type(vendor_type)
    try:
        if vt == "car boot sales":
            return float(st.secrets["event"]["price_car_boot"])
        elif vt == "f&b":
            return float(st.secrets["event"]["price_fb"])
        elif vt == "food truck":
            return float(st.secrets["event"]["price_ft"])
        else:
            return float(st.secrets["event"]["price_others"])
    except Exception:
        return 0.0


def get_deposit(vendor_type):
    vt = _normalize_type(vendor_type)
    try:
        if vt == "f&b":
            return float(st.secrets["event"]["deposit_fb"])
        elif vt == "food truck":
            return float(st.secrets["event"]["deposit_ft"])
        elif vt == "arts/crafts & others":
            return float(st.secrets["event"].get("deposit_others", 100))
        return 0.0
    except Exception:
        return 0.0


def get_addon_price(addon_str):
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


def format_timestamp_display(raw):
    """Tukar timestamp dari Google Form jadi format yang senang baca."""
    if raw is None or pd.isna(raw):
        return "—"
    s = str(raw).strip()
    if s == "" or s.lower() in ("nan", "none", "nat", "null", "—", "-"):
        return "—"

    formats = [
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%d %b %Y, %I:%M %p")
        except (ValueError, TypeError):
            continue

    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        pass

    return s


def get_vendor_total(vendor_type, addon_str):
    return get_category_price(vendor_type) + get_deposit(vendor_type) + get_addon_price(addon_str)


# ============================================================
# SAMBUNGAN DATA
# ============================================================
conn = st.connection("gsheets", type=GSheetsConnection)
df = load_sheet_safe(conn, "Vendors", ttl=60)

if df is None:
    st.stop()

df[COL_TYPE] = df[COL_TYPE].apply(normalize_type)
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
        columns=[
            "Timestamp", "Plate Number", PROOF_COL, "FolderUrl",
            "Pilih parking lot", "Pilih F&B Lot",
            "Pilih Arts/Crafts & Others Lot", "Pilih Food Truck Lot",
        ]
    )

for col in [
    "Timestamp", "Plate Number", PROOF_COL, "FolderUrl",
    "Pilih parking lot", "Pilih F&B Lot",
    "Pilih Arts/Crafts & Others Lot", "Pilih Food Truck Lot",
]:
    if col not in payments_df.columns:
        payments_df[col] = ""

payments_df["_plate_norm"] = (
    payments_df["Plate Number"].astype(str).str.upper().str.replace(" ", "")
)


def _clean_payment_val(v):
    if v is None or pd.isna(v):
        return ""
    s = str(v).strip()
    if s.lower() in ("nan", "none", "nat", "null"):
        return ""
    return s


def _pick_col(df_, *candidates):
    norm = {str(c).strip().lower().replace(" ", ""): c for c in df_.columns}
    for cand in candidates:
        key = cand.strip().lower().replace(" ", "")
        if key in norm:
            return norm[key]
    return None


def get_vendor_payment_info(plate):
    normalized = str(plate).upper().replace(" ", "")
    matched = payments_df[payments_df["_plate_norm"] == normalized]

    if matched.empty:
        return {
            "proof_url": "", "folder_url": "", "timestamp": "",
            "parking_lot": "", "fnb_lot": "", "ft_lot": "", "arts_lot": "",
        }

    try:
        matched = matched.sort_values("Timestamp", ascending=False)
    except Exception:
        pass

    latest = matched.iloc[0]

    col_proof   = _pick_col(payments_df, PROOF_COL, "Upload Bukti Bayaran", "Bukti Bayaran")
    col_folder  = _pick_col(payments_df, "FolderUrl", "Folder URL")
    col_ts      = _pick_col(payments_df, "Timestamp", "Tarikh")
    col_parking = _pick_col(payments_df, "Pilih parking lot", "Parking Lot", "Parking")
    col_fnb     = _pick_col(payments_df, "Pilih F&B Lot", "F&B Lot", "FNB Lot", "F&B")
    col_ft      = _pick_col(
        payments_df,
        "Pilih Food Truck Lot",
        "Food Truck Lot",
        "Food Truck",
        "FT Lot",
    )
    col_arts    = _pick_col(
        payments_df,
        "Pilih Arts/Crafts & Others Lot",
        "Pilih Arts & Crafts / Toys Lot",
        "Arts & Crafts / Toys Lot",
        "Arts & Crafts Lot",
        "Arts Lot",
    )

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
        "ft_lot":      _get(col_ft),
        "arts_lot":    _get(col_arts),
    }


# ============================================================
# FUNGSI BANTUAN
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


def others_approved():
    mask = ~df[COL_TYPE].isin([CAT_CARBOOT, CAT_FB, CAT_FT])
    mask &= (df["Status"] == "Approved")
    return df[mask].shape[0]


def others_pending():
    mask = ~df[COL_TYPE].isin([CAT_CARBOOT, CAT_FB, CAT_FT])
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
    st.markdown(
        "<div style='padding: 0.5rem 0 1rem 0;'>"
        "<div style='font-size: 1.05rem; font-weight: 600; color: #1c1917;'>Admin Panel</div>"
        "<div style='font-size: 0.78rem; color: #78716c; margin-top: 0.15rem;'>Event Vendor Manager</div>"
        "</div>",
        unsafe_allow_html=True,
    )
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
# DIALOG
# ============================================================
@st.dialog("Sahkan Tindakan")
def confirm_approve_dialog(plate, vendor_name):
    st.write("Anda akan **meluluskan** permohonan ini:")
    st.markdown(f"**No. Plate:** `{plate}`  \n**Nama:** {vendor_name}")

    vendor_row = df[df[COL_PLATE] == plate]
    if not vendor_row.empty:
        vendor_remark = clean_text(vendor_row.iloc[0].get(COL_REMARK, ""))
        if vendor_remark:
            st.markdown("**📝 Remark Vendor:**")
            st.markdown(
                f"<div class='remark-box'>{vendor_remark}</div>",
                unsafe_allow_html=True,
            )

    existing_row = df[df[COL_PLATE] == plate]
    existing_note = ""
    if not existing_row.empty:
        existing_val = existing_row.iloc[0].get("Notes", "")
        if pd.notna(existing_val) and str(existing_val).strip():
            existing_note = str(existing_val).strip()

    admin_note = st.text_area(
        "Nota Admin (vendor akan nampak — optional)",
        value=existing_note,
        placeholder="Contoh: Sila bawa salinan resit semasa event.",
        height=120,
        key=f"approve_note_{plate}",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Luluskan", type="primary", use_container_width=True, key="dlg_approve_yes"):
            df.loc[df[COL_PLATE] == plate, "Status"] = "Approved"
            df.loc[df[COL_PLATE] == plate, "Notes"] = admin_note.strip()
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
                log_action(conn, ADMIN_NAME, "REJECT", plate,
                           f"Tolak: {vendor_name} — Sebab: {reject_reason[:100]}")
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

    type_options = ["Car Boot Sales", "F&B", "Food Truck", "Arts/Crafts & Others"]
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

    new_addon = st.text_input(
        "ADD ON",
        value=str(vendor.get(COL_ADDON, "") or ""),
        help="Contoh: Meja (Fee: RM 20), Kerusi (Fee: RM 5)",
        key="edit_addon",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Simpan", type="primary", use_container_width=True, key="edit_save"):
            idx = df[df[COL_PLATE] == plate].index[0]
            df.at[idx, COL_NAME] = new_name
            df.at[idx, COL_PHONE] = clean_phone_raw(new_phone)
            df.at[idx, COL_TYPE] = new_type
            df.at[idx, COL_CAT] = new_cat
            df.at[idx, COL_PLATE] = new_plate
            df.at[idx, COL_ADDON] = new_addon
            safe_update(conn, df)
            log_action(conn, ADMIN_NAME, "EDIT", plate, f"Nama: {new_name}, Plate: {new_plate}")
            st.toast(f"✅ {plate} telah dikemaskini", icon="✅")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True, key="edit_cancel"):
            st.rerun()


@st.dialog("Sahkan Padam")
def confirm_delete_dialog(plate, vendor_name, row_signature):
    st.warning("Anda akan **memadam** 1 baris rekod vendor ini:")
    st.markdown(f"**No. Plate:** `{plate}`  \n**Nama:** {vendor_name}")
    st.write("")
    st.info(
        "ℹ️ Kalau ada duplicate (2 baris sama plate), **hanya 1 baris ini** "
        "akan dipadam. Baris lain kekal."
    )
    st.error("⚠️ **Tindakan ini tidak boleh diundur.** Data akan dibuang dari Google Sheet.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Padam", type="primary", use_container_width=True, key="dlg_delete_yes"):
            global df
            matched_idx = None
            for i, r in df.iterrows():
                sig = tuple(str(r.get(c, "")) for c in df.columns)
                if sig == row_signature:
                    matched_idx = i
                    break

            if matched_idx is not None:
                df = df.drop(matched_idx).reset_index(drop=True)
                safe_update(conn, df)
                log_action(conn, ADMIN_NAME, "DELETE", plate,
                           f"Padam 1 baris: {vendor_name}")
                st.toast(f"🗑️ 1 baris {plate} telah dipadam", icon="🗑️")
                st.rerun()
            else:
                st.error("❌ Baris tidak dijumpai — mungkin sudah dipadam.")

    with col2:
        if st.button("Batal", use_container_width=True, key="dlg_delete_no"):
            st.rerun()


# ============================================================
# 📞 WHATSAPP GROUP
# ============================================================
try:
    wa_group = st.secrets["event"]["whatsapp_group"]
except Exception:
    wa_group = ""

if wa_group:
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #f2ebe0 0%, #faf5ec 100%);
        border: 1px solid #e8dcc7;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    ">
        <div>
            <div style="font-weight: 600; color: #292524; font-size: 0.95rem;">💬 WhatsApp Group Vendor</div>
            <div style="color: #78716c; font-size: 0.82rem; margin-top: 0.2rem;">Hantar mesej terus dalam group</div>
        </div>
        <a href="{wa_group}" target="_blank" style="
            background-color: #78350f;
            color: #ffffff;
            padding: 0.55rem 1.1rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.85rem;
            white-space: nowrap;
        ">Buka Group →</a>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# SECTION 1 — DASHBOARD
# ============================================================
if show_section("1️⃣ Dashboard"):
    st.markdown('<div class="section-title">1️⃣ Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Ringkasan slot & permohonan vendor</div>', unsafe_allow_html=True)

    cb_approved = count_approved(**{COL_TYPE: CAT_CARBOOT})
    fb_approved = count_approved(**{COL_TYPE: CAT_FB})
    ft_approved = count_approved(**{COL_TYPE: CAT_FT})
    ot_approved = others_approved()

    cb_pending = count_pending(**{COL_TYPE: CAT_CARBOOT})
    fb_pending = count_pending(**{COL_TYPE: CAT_FB})
    ft_pending = count_pending(**{COL_TYPE: CAT_FT})
    ot_pending = others_pending()

    total_approved = cb_approved + fb_approved + ft_approved + ot_approved
    total_pending = cb_pending + fb_pending + ft_pending + ot_pending
    total_limit = CAR_BOOT_LIMIT + FB_OVERALL_LIMIT + FT_LIMIT + OTHERS_LIMIT

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Car Boot", f"{cb_approved} / {CAR_BOOT_LIMIT}",
              f"⏳ {cb_pending} pending" if cb_pending else None, delta_color="off")
    c2.metric("F&B", f"{fb_approved} / {FB_OVERALL_LIMIT}",
              f"⏳ {fb_pending} pending" if fb_pending else None, delta_color="off")
    c3.metric("Food Truck", f"{ft_approved} / {FT_LIMIT}",
              f"⏳ {ft_pending} pending" if ft_pending else None, delta_color="off")
    c4.metric("Others", f"{ot_approved} / {OTHERS_LIMIT}",
              f"⏳ {ot_pending} pending" if ot_pending else None, delta_color="off")
    c5.metric("Total", f"{total_approved} / {total_limit}",
              f"⏳ {total_pending} pending" if total_pending else None, delta_color="off")

    st.markdown("")
    cb_committed = cb_approved + cb_pending
    fb_committed = fb_approved + fb_pending
    ft_committed = ft_approved + ft_pending
    ot_committed = ot_approved + ot_pending
    total_committed = total_approved + total_pending

    pc1, pc2, pc3, pc4, pc5 = st.columns(5)
    with pc1:
        st.caption("**Car Boot**")
        st.progress(min(cb_committed / CAR_BOOT_LIMIT, 1.0), text=f"{cb_committed}/{CAR_BOOT_LIMIT}")
    with pc2:
        st.caption("**F&B**")
        st.progress(min(fb_committed / FB_OVERALL_LIMIT, 1.0), text=f"{fb_committed}/{FB_OVERALL_LIMIT}")
    with pc3:
        st.caption("**Food Truck**")
        st.progress(min(ft_committed / FT_LIMIT, 1.0), text=f"{ft_committed}/{FT_LIMIT}")
    with pc4:
        st.caption("**Crafts & Others**")
        st.progress(min(ot_committed / OTHERS_LIMIT, 1.0), text=f"{ot_committed}/{OTHERS_LIMIT}")
    with pc5:
        st.caption("**Total**")
        st.progress(min(total_committed / total_limit, 1.0), text=f"{total_committed}/{total_limit}")

    st.caption(
        f"📅 Event: **{EVENT_DATE.strftime('%d %b %Y')}** &nbsp;·&nbsp; "
        f"✅ Approved &nbsp;·&nbsp; ⏳ Pending"
    )

    st.markdown("---")
    st.markdown(f"#### Pecahan Kategori F&B")
    st.caption(f"Had: **{FB_CATEGORY_LIMIT}** vendor per kategori")

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
            "Total": committed_n, "Limit": FB_CATEGORY_LIMIT, "Baki": left,
        })

    fb_df = pd.DataFrame(rows)
    st.dataframe(fb_df, hide_index=True, use_container_width=True)

    st.divider()


# ============================================================
# SECTION 2 — TARIKH AKHIR BAYARAN
# ============================================================
cutoff_date = EVENT_DATE - timedelta(days=PAYMENT_DEADLINE_DAYS)

if show_section("2️⃣ Tarikh Akhir Bayaran"):
    st.markdown('<div class="section-title">2️⃣ Tarikh Akhir Bayaran</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-sub">Vendor yang belum bayar akan dibatalkan selepas '
                f'<b>{cutoff_date.strftime("%d %b %Y")}</b></div>', unsafe_allow_html=True)

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
# SECTION 3 — PERMOHONAN MENUNGGU
# ============================================================
if show_section("3️⃣ Permohonan Menunggu"):
    st.markdown('<div class="section-title">3️⃣ Permohonan Menunggu</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Semak & luluskan permohonan vendor baru</div>', unsafe_allow_html=True)

    try:
        form_url = st.secrets["event"].get("google_form_responses_url", "")
    except Exception:
        form_url = ""

    if form_url:
        st.markdown(f"""
        <div style="
            background: #fafaf9;
            border: 1px solid #e5e5e5;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
        ">
            <div style="font-size: 0.85rem; color: #57534e;">
                📋 <b>Response Google Form</b> — buka Responses tab untuk urus response asal
            </div>
            <a href="{form_url}" target="_blank" style="
                background-color: #78350f;
                color: #ffffff;
                padding: 0.45rem 0.9rem;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 500;
                font-size: 0.82rem;
                white-space: nowrap;
            ">Buka Form →</a>
        </div>
        """, unsafe_allow_html=True)

    pending_df = df[df["Status"] == "Pending"]
    products_col = _get_products_col(df)

    if pending_df.empty:
        st.info("Tiada permohonan yang menunggu.")
    else:
        f_col1, f_col2, f_col3 = st.columns([2, 3, 1])

        with f_col1:
            type_options = ["Semua", "Car Boot Sales", "F&B", "Food Truck", "Arts/Crafts & Others"]
            type_filter = st.selectbox("Kategori", options=type_options, key="pending_type_filter")

        with f_col2:
            search_query = st.text_input(
                "Cari",
                placeholder="No. Plate / Nama / Telefon",
                key="pending_search",
            ).strip()

        with f_col3:
            st.markdown(
                "<div style='height: 1.85rem;'></div>"
                f"<div style='font-size: 0.85rem; color: #78716c; text-align: right;'>"
                f"<b>{len(pending_df)}</b> permohonan"
                f"</div>",
                unsafe_allow_html=True,
            )

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

        if filtered.empty:
            st.warning("Tiada permohonan sepadan dengan tapisan anda.")
        else:
            list_height = min(max(len(filtered) * 300, 300), 1000)

            with st.container(height=list_height, border=False):
                for idx, (_, row) in enumerate(filtered.iterrows()):
                    plate = row[COL_PLATE]
                    name = row[COL_NAME]
                    v_type = row[COL_TYPE]
                    v_cat = clean_cat_str(row.get(COL_CAT, ""))
                    phone = format_phone_display(row[COL_PHONE])

                    cat_str = f" / {v_cat}" if v_cat else ""

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

                        products_text = clean_products_str(row.get(products_col, "")) if products_col else ""
                        if products_text:
                            st.markdown(
                                f"<div style='font-size:0.8rem; font-weight:600; color:#78350f; "
                                f"text-transform:uppercase; letter-spacing:0.5px; margin:0.35rem 0 0.25rem 0;'>"
                                f"🛍️ Senarai Produk</div>"
                                f"<div class='product-box'>{products_text}</div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.caption("🛍️ _(Tiada senarai produk diisi)_")

                        remark_text = clean_text(row.get(COL_REMARK, ""))
                        if remark_text:
                            st.markdown(
                                f"<div style='font-size:0.8rem; font-weight:600; color:#92400e; "
                                f"text-transform:uppercase; letter-spacing:0.5px; margin:0.35rem 0 0.25rem 0;'>"
                                f"📝 Remark Vendor</div>"
                                f"<div class='remark-box'>{remark_text}</div>",
                                unsafe_allow_html=True,
                            )

                        v_total = get_vendor_total(v_type, row.get(COL_ADDON, ""))
                        st.caption(f"💰 Total: {format_rm(v_total)}")

                        b1, b2, b3, _ = st.columns([1, 1, 1, 3])

                        with b1:
                            if st.button("✓ Lulus", type="primary", use_container_width=True, key=f"approve_{plate}_{idx}"):
                                confirm_approve_dialog(plate, name)
                        with b2:
                            if st.button("✗ Tolak", use_container_width=True, key=f"reject_{plate}_{idx}"):
                                confirm_reject_dialog(plate, name)
                        with b3:
                            if st.button("✎ Edit", use_container_width=True, key=f"edit_{plate}_{idx}"):
                                edit_vendor_dialog(plate)

    st.divider()


# ============================================================
# SECTION 4 — REKOD BAYARAN
# ============================================================
if show_section("4️⃣ Rekod Bayaran"):
    st.markdown('<div class="section-title">4️⃣ Rekod Bayaran</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Semak bukti & tandakan status pembayaran vendor</div>', unsafe_allow_html=True)

    approved_df = df[df["Status"] == "Approved"]

    if approved_df.empty:
        st.info("Belum ada vendor yang diluluskan.")
    else:
        total_paid = int(approved_df["Paid"].sum())
        total_unpaid = len(approved_df) - total_paid

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Diluluskan", len(approved_df))
        mc2.metric("✅ Sudah Bayar", total_paid)
        mc3.metric("⬜ Belum Bayar", total_unpaid)

        st.markdown("---")

        f1, f2, f3, f4 = st.columns([1, 1, 1, 1])

        with f1:
            category_filter = st.selectbox(
                "Kategori",
                options=["Semua", "Car Boot Sales", "F&B", "Food Truck", "Arts/Crafts & Others"],
                key="pay_filter_category",
            )
        with f2:
            paid_filter = st.selectbox(
                "Status Bayar",
                options=["Semua", "✅ Sudah Bayar", "⬜ Belum Bayar"],
                key="pay_filter_paid",
            )
        with f3:
            proof_filter = st.selectbox(
                "Status Bukti",
                options=["Semua", "📄 Ada Bukti", "⬜ Tiada Bukti"],
                key="pay_filter_proof",
            )
        with f4:
            plate_search = st.text_input(
                "🔍 Cari No. Plate",
                placeholder="Contoh: PJL3465",
                key="pay_filter_plate",
            ).strip().upper()

        display_rows = []
        for _, row in approved_df.iterrows():
            plate = row[COL_PLATE]
            info = get_vendor_payment_info(plate)

            proof_url   = info["proof_url"]
            parking_lot = info["parking_lot"]
            fnb_lot     = info["fnb_lot"]
            ft_lot      = info.get("ft_lot", "")
            arts_lot    = info["arts_lot"]

            row_type = str(row[COL_TYPE]).strip()
            if row_type == CAT_CARBOOT:
                lot_val = parking_lot
            elif row_type == CAT_FB:
                lot_val = fnb_lot
            elif row_type == CAT_FT:
                lot_val = ft_lot or fnb_lot
            elif row_type == CAT_ARTS:
                lot_val = arts_lot
            else:
                lot_val = parking_lot or fnb_lot or ft_lot or arts_lot

            v_t = str(row.get(COL_TYPE, "")).strip()
            v_total = get_vendor_total(v_t, row.get(COL_ADDON, ""))
            cat = clean_cat_str(row.get(COL_CAT, ""))

            display_rows.append({
                "Plate": plate,
                "Nama": row[COL_NAME],
                "Telefon": format_phone_display(row.get(COL_PHONE, "")),
                "Kategori": v_t,
                "F&B Category": cat if cat else "—",
                "Lot": lot_val or "—",
                "Total": format_rm(v_total),
                "Timestamp": format_timestamp_display(info.get("timestamp", "")),
                "Bukti": "📄 Ada" if proof_url else "⬜ Tiada",
                "Link": proof_url if proof_url else "",
                "Bayar": bool(row["Paid"]),
            })

        table_df = pd.DataFrame(display_rows)

        if category_filter != "Semua":
            table_df = table_df[table_df["Kategori"] == category_filter]
        if paid_filter == "✅ Sudah Bayar":
            table_df = table_df[table_df["Bayar"] == True]
        elif paid_filter == "⬜ Belum Bayar":
            table_df = table_df[table_df["Bayar"] == False]
        if proof_filter == "📄 Ada Bukti":
            table_df = table_df[table_df["Bukti"] == "📄 Ada"]
        elif proof_filter == "⬜ Tiada Bukti":
            table_df = table_df[table_df["Bukti"] == "⬜ Tiada"]
        if plate_search:
            table_df = table_df[
                table_df["Plate"].astype(str).str.upper().str.replace(" ", "").str.contains(
                    plate_search.replace(" ", ""),
                    na=False,
                )
            ]

        table_df = table_df.sort_values(["Kategori", "Plate"]).reset_index(drop=True)

        if table_df.empty:
            st.info("Tiada vendor sepadan dengan filter.")
        else:
            st.caption(
                f"Menunjukkan **{len(table_df)}** daripada **{len(approved_df)}** vendor. "
                f"Tick kolum **Bayar** → klik **💾 Simpan Status Bayaran**."
            )

            row_h = 35
            header_h = 45
            table_height = min(max(len(table_df) * row_h + header_h, 250), 600)

            edited = st.data_editor(
                table_df,
                hide_index=True,
                use_container_width=True,
                height=table_height,
                disabled=["Plate", "Nama", "Telefon", "Kategori", "F&B Category",
                          "Lot", "Total", "Timestamp", "Bukti", "Link"],
                column_config={
                    "Plate": st.column_config.TextColumn("Plate", width="small"),
                    "Nama": st.column_config.TextColumn("Nama", width="medium"),
                    "Telefon": st.column_config.TextColumn("Telefon", width="small"),
                    "Kategori": st.column_config.TextColumn("Kategori", width="medium"),
                    "F&B Category": st.column_config.TextColumn("F&B Category", width="medium"),
                    "Lot": st.column_config.TextColumn("Lot", width="small"),
                    "Total": st.column_config.TextColumn("Total", width="small"),
                    "Timestamp": st.column_config.TextColumn("Timestamp", width="medium"),
                    "Bukti": st.column_config.TextColumn("Bukti", width="small"),
                    "Link": st.column_config.LinkColumn("Link", display_text="Buka 📄", width="small"),
                    "Bayar": st.column_config.CheckboxColumn("Bayar", width="small", default=False),
                },
                key=f"pay_editor_{category_filter}_{paid_filter}_{proof_filter}_{plate_search}",
            )

            st.markdown("")
            if st.button("💾 Simpan Status Bayaran", type="primary", use_container_width=False):
                with st.spinner("Menyimpan..."):
                    changed = 0
                    for _, r in edited.iterrows():
                        plate = r["Plate"]
                        new_paid = bool(r["Bayar"])
                        old_paid = bool(df.loc[df[COL_PLATE] == plate, "Paid"].iloc[0])
                        if new_paid != old_paid:
                            df.loc[df[COL_PLATE] == plate, "Paid"] = new_paid
                            changed += 1
                            log_action(
                                conn, ADMIN_NAME,
                                "PAID" if new_paid else "UNPAID",
                                plate,
                                f"{'Tanda' if new_paid else 'Buang tanda'} bayaran",
                            )

                    if changed > 0:
                        safe_update(conn, df)
                        st.toast(f"✅ {changed} rekod dikemaskini", icon="💾")
                        st.rerun()
                    else:
                        st.toast("Tiada perubahan", icon="ℹ️")

    st.divider()


# ============================================================
# SECTION 5 — SEMUA VENDOR
# ============================================================
if show_all:
    st.markdown('<div class="section-title">5️⃣ Semua Vendor</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Senarai penuh vendor + muat turun CSV</div>', unsafe_allow_html=True)

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
                display: flex; align-items: center; justify-content: center; gap: 0.5rem;
                background-color: #78350f; color: #ffffff; padding: 0.6rem 1rem;
                border-radius: 10px; text-decoration: none; font-weight: 500; font-size: 0.85rem;
            ">📋 Buka Google Form Responses</a>
            """, unsafe_allow_html=True)
    with quick_col2:
        if sheet_url:
            st.markdown(f"""
            <a href="{sheet_url}" target="_blank" style="
                display: flex; align-items: center; justify-content: center; gap: 0.5rem;
                background-color: #ffffff; color: #78350f; padding: 0.6rem 1rem;
                border-radius: 10px; text-decoration: none; font-weight: 500; font-size: 0.85rem;
                border: 1px solid #d6c4a3;
            ">📊 Buka Google Sheet</a>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")

    all_f1, all_f2, all_f3 = st.columns([2, 2, 3])

    with all_f1:
        status_options = df["Status"].dropna().unique().tolist()
        status_filter = st.multiselect(
            "Tapis mengikut status",
            options=status_options,
            default=status_options,
            key="all_status_filter",
        )
    with all_f2:
        all_category_filter = st.selectbox(
            "Kategori",
            options=["Semua", "Car Boot Sales", "F&B", "Food Truck", "Arts/Crafts & Others"],
            key="all_category_filter",
        )
    with all_f3:
        all_search = st.text_input(
            "🔍 Cari (Plate / Nama / Telefon)",
            placeholder="Contoh: PJL3465 atau Cute Club",
            key="all_search",
        ).strip()

    filtered_all = df[df["Status"].isin(status_filter)]

    if all_category_filter != "Semua":
        filtered_all = filtered_all[filtered_all[COL_TYPE] == all_category_filter]

    if all_search:
        q = all_search.lower()
        filtered_all = filtered_all[
            filtered_all[COL_PLATE].astype(str).str.lower().str.contains(q, na=False)
            | filtered_all[COL_NAME].astype(str).str.lower().str.contains(q, na=False)
            | filtered_all[COL_PHONE].astype(str).str.lower().str.contains(q, na=False)
        ]

    display_df = filtered_all.copy()
    display_df["Timestamp"] = display_df[COL_PLATE].apply(
        lambda p: format_timestamp_display(get_vendor_payment_info(p)["timestamp"]))
    display_df["Parking Lot"] = display_df[COL_PLATE].apply(
        lambda p: get_vendor_payment_info(p)["parking_lot"] or "-")
    display_df["F&B Lot"] = display_df[COL_PLATE].apply(
        lambda p: get_vendor_payment_info(p)["fnb_lot"] or "-")
    display_df["Food Truck Lot"] = display_df[COL_PLATE].apply(
        lambda p: get_vendor_payment_info(p).get("ft_lot", "") or "-")
    display_df["Arts & Crafts Lot"] = display_df[COL_PLATE].apply(
        lambda p: get_vendor_payment_info(p)["arts_lot"] or "-")

    display_df["Total Price"] = display_df.apply(
        lambda r: format_rm(get_vendor_total(r[COL_TYPE], r.get(COL_ADDON, ""))), axis=1)

    drop_exact = {
        "Media Sosial Perniagaan (Jika Ada)",
        "Notes", "TOTAL PRICE", "Jenis Model Kenderaan", "Email address",
        "Nama/Name",
    }
    drop_contains = [
        "Media Sosial Perniagaan",
        "Jenis Model Kenderaan",
        "Email address",
        "TERMA DAN SYARAT",
        "IC (",
    ]

    def _should_drop(col_name):
        cname = str(col_name).strip()
        if cname in drop_exact:
            return True
        for pat in drop_contains:
            if pat in cname:
                return True
        if cname == "Notes":
            return True
        # Buang column kosong / auto-generated oleh Google Sheet
        if cname == "":
            return True
        if cname.startswith("Unnamed:"):
            return True
        if re.fullmatch(r"Column\s*\d+", cname, flags=re.IGNORECASE):
            return True
        if cname.lower() in ("nan", "none", "nat", "null"):
            return True
        return False

    display_df = display_df[[c for c in display_df.columns if not _should_drop(c)]]

    if COL_PHONE in display_df.columns:
        display_df[COL_PHONE] = display_df[COL_PHONE].apply(format_phone_display)

    priority_cols = [COL_PLATE, COL_NAME, COL_PHONE, COL_TYPE, COL_CAT,
                     "Parking Lot", "F&B Lot", "Food Truck Lot", "Arts & Crafts Lot",
                     "Timestamp", "Total Price"]
    ordered_cols = [c for c in priority_cols if c in display_df.columns] + \
                   [c for c in display_df.columns if c not in priority_cols]
    display_df = display_df[ordered_cols]

    table_height = min(max(len(display_df) * 35 + 45, 250), 600)
    st.dataframe(display_df, hide_index=True, use_container_width=True, height=table_height)

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    st.markdown("##### 🗑️ Padam 1 Baris")
    st.caption(
        "Kalau ada duplicate plate, pilih **baris tepat** untuk dipadam — "
        "baris lain akan kekal."
    )

    display_df_reset = display_df.reset_index(drop=True)
    delete_options = ["— Pilih baris —"] + [
        f"Baris {i+1}: {display_df_reset.iloc[i][COL_PLATE]} — {display_df_reset.iloc[i][COL_NAME]}"
        for i in range(len(display_df_reset))
    ]

    act_col1, act_col2 = st.columns([3, 1])
    with act_col1:
        delete_choice = st.selectbox(
            "Pilih baris untuk dipadam",
            options=delete_options,
            key="delete_row_select",
            label_visibility="collapsed",
        )
    with act_col2:
        if st.button("🗑️ Padam", type="primary", use_container_width=True):
            if delete_choice and delete_choice != "— Pilih baris —":
                idx_pick = delete_options.index(delete_choice) - 1
                row_pick = display_df_reset.iloc[idx_pick]
                plate_pick = row_pick[COL_PLATE]
                name_pick = row_pick[COL_NAME]

                row_signature = tuple(
                    str(row_pick.get(c, "")) for c in df.columns
                )

                confirm_delete_dialog(plate_pick, name_pick, row_signature)
            else:
                st.error("Sila pilih baris.")

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    csv_all = display_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 Muat Turun CSV (Semua Vendor)",
        data=csv_all,
        file_name=f"vendors_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )
