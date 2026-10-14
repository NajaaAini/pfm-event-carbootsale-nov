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
# PROFESSIONAL CSS
# ============================================================
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        -webkit-font-smoothing: antialiased;
    }

    :root {
        --brand-900: #431407;
        --brand-800: #78350f;
        --brand-700: #92400e;
        --brand-100: #fef3c7;
        --brand-50: #fffbeb;
        --neutral-900: #0c0a09;
        --neutral-700: #292524;
        --neutral-500: #78716c;
        --neutral-300: #d6d3d1;
        --neutral-200: #e7e5e4;
        --neutral-100: #f5f5f4;
        --neutral-50: #fafaf9;
        --success: #16a34a;
        --success-bg: #f0fdf4;
        --warning: #d97706;
        --warning-bg: #fffbeb;
        --danger: #dc2626;
        --danger-bg: #fef2f2;
        --info: #2563eb;
        --info-bg: #eff6ff;
        --radius: 12px;
        --radius-sm: 8px;
        --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
        --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.06), 0 2px 4px -1px rgba(0,0,0,0.04);
        --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -2px rgba(0,0,0,0.04);
    }

    .block-container {
        padding-top: 1.75rem !important;
        padding-bottom: 3rem !important;
        max-width: 1440px;
    }

    .section-header {
        display: flex;
        align-items: center;
        gap: 0.85rem;
        margin: 0 0 1.75rem 0;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--neutral-200);
    }
    .section-badge {
        width: 42px;
        height: 42px;
        border-radius: 10px;
        background: linear-gradient(135deg, var(--brand-800) 0%, var(--brand-700) 100%);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 1.1rem;
        flex-shrink: 0;
        box-shadow: 0 2px 4px rgba(120, 53, 15, 0.2);
    }
    .section-header-text {
        flex: 1;
        min-width: 0;
    }
    .section-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--neutral-900);
        margin: 0;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }
    .section-sub {
        font-size: 0.85rem;
        color: var(--neutral-500);
        margin: 0.15rem 0 0 0;
        line-height: 1.4;
    }
    .section-count {
        background: var(--neutral-100);
        color: var(--neutral-700);
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 700;
        white-space: nowrap;
    }

    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid var(--neutral-200);
        border-radius: var(--radius);
        padding: 1.1rem 1.25rem;
        box-shadow: var(--shadow-sm);
        transition: box-shadow 0.15s ease, transform 0.15s ease;
        border-top: 3px solid var(--brand-800);
    }
    [data-testid="stMetric"]:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-1px);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.7rem !important;
        color: var(--neutral-500) !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 700 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.7rem !important;
        font-weight: 800 !important;
        color: var(--neutral-900) !important;
        letter-spacing: -0.02em;
    }

    .stButton > button,
    .stDownloadButton > button,
    .stLinkButton > a {
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 1rem !important;
        border: 1px solid var(--neutral-300) !important;
        transition: all 0.15s ease !important;
        letter-spacing: 0.01em;
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stLinkButton > a:hover {
        transform: translateY(-1px);
        box-shadow: var(--shadow-md) !important;
        border-color: var(--neutral-500) !important;
    }
    .stButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"],
    .stLinkButton > a[kind="primary"] {
        background: var(--brand-800) !important;
        color: #ffffff !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--brand-900) !important;
        box-shadow: 0 4px 12px rgba(120, 53, 15, 0.25) !important;
    }

    .product-box {
        background: var(--neutral-50);
        border-left: 3px solid var(--brand-800);
        border-radius: var(--radius-sm);
        padding: 0.7rem 0.9rem;
        margin: 0.5rem 0 0.6rem 0;
        font-size: 0.85rem;
        color: var(--neutral-700);
        white-space: pre-wrap;
        line-height: 1.55;
    }
    .remark-box {
        background: var(--warning-bg);
        border-left: 3px solid var(--warning);
        border-radius: var(--radius-sm);
        padding: 0.7rem 0.9rem;
        margin: 0.5rem 0 0.6rem 0;
        font-size: 0.85rem;
        color: var(--neutral-700);
        white-space: pre-wrap;
        line-height: 1.55;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--neutral-200);
        border-radius: var(--radius);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
    }
    [data-testid="stDataFrame"] [role="columnheader"] {
        background: var(--neutral-50) !important;
        font-weight: 700 !important;
        font-size: 0.72rem !important;
        color: var(--neutral-700) !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    hr {
        margin: 2rem 0 !important;
        border-color: var(--neutral-200) !important;
    }

    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--neutral-200);
    }
    [data-testid="stSidebar"] .stRadio > label {
        font-size: 0.7rem !important;
        color: var(--neutral-500) !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
    }
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
        padding: 0.65rem 0.8rem;
        border-radius: var(--radius-sm);
        transition: all 0.15s ease;
        font-weight: 500;
        font-size: 0.9rem;
    }
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover {
        background: var(--neutral-50);
    }
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-checked="true"] {
        background: var(--brand-50);
        color: var(--brand-800);
        font-weight: 700;
    }

    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stMultiSelect > div > div > div,
    .stTextArea > div > div > textarea {
        border-radius: var(--radius-sm) !important;
        border-color: var(--neutral-300) !important;
        font-size: 0.88rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus-within,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--brand-800) !important;
        box-shadow: 0 0 0 3px rgba(120, 53, 15, 0.1) !important;
    }

    [data-testid="stAlert"] {
        border-radius: var(--radius-sm);
        border: none;
        font-size: 0.88rem;
    }

    .stProgress > div > div > div > div {
        background: var(--brand-800);
    }

    [data-testid="stDialog"] > div {
        border-radius: var(--radius);
        box-shadow: var(--shadow-lg);
    }

    .badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .badge-success { background: var(--success-bg); color: var(--success); }
    .badge-warning { background: var(--warning-bg); color: var(--warning); }
    .badge-danger  { background: var(--danger-bg);  color: var(--danger); }
    .badge-info    { background: var(--info-bg);    color: var(--info); }
    .badge-neutral { background: var(--neutral-100); color: var(--neutral-700); }

    .sub-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin: 1.5rem 0 1rem 0;
    }
    .sub-header-line {
        flex: 1;
        height: 1px;
        background: var(--neutral-200);
    }
    .sub-header-text {
        font-size: 0.9rem;
        font-weight: 700;
        color: var(--neutral-700);
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .empty-state {
        text-align: center;
        padding: 2.5rem 1rem;
        color: var(--neutral-500);
    }
    .empty-state-icon {
        font-size: 2.5rem;
        margin-bottom: 0.75rem;
        opacity: 0.6;
    }
    .empty-state-text {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPERS — SECTION HEADER
# ============================================================
def section_header(num, title, subtitle, count=None):
    count_html = f"<div class='section-count'>{count}</div>" if count is not None else ""
    st.markdown(
        f"<div class='section-header'>"
        f"<div class='section-badge'>{num}</div>"
        f"<div class='section-header-text'>"
        f"<div class='section-title'>{title}</div>"
        f"<div class='section-sub'>{subtitle}</div>"
        f"</div>"
        f"{count_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def sub_header(text):
    st.markdown(
        f"<div class='sub-header'>"
        f"<span class='sub-header-text'>{text}</span>"
        f"<div class='sub-header-line'></div>"
        f"</div>",
        unsafe_allow_html=True,
    )


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

COL_NAME = COL_PHONE = COL_TYPE = COL_CAT = None
COL_PLATE = COL_ADDON = COL_PRODUCTS = COL_REMARK = None
PROOF_COL = None

VALID_STATUSES = ["Pending", "Approved", "Rejected", "Cancelled"]
CAT_CARBOOT = "Car Boot Sales"
CAT_FB = "F&B"
CAT_FT = "Food Truck"
CAT_ARTS = "Arts/Crafts & Others"


# ============================================================
# REJECT TEMPLATES
# ============================================================
REJECT_TEMPLATES = {
    "Deadline bayaran lepas": (
        "Maaf, tempahan slot anda telah dibatalkan kerana bayaran tidak "
        "diterima sebelum tarikh akhir yang ditetapkan. Slot anda kini "
        "telah dibuka semula kepada vendor lain. Terima kasih atas "
        "minat anda. Semoga kita dapat bekerjasama pada event akan datang. 🙏"
    ),
    "Slot kategori penuh": (
        "Maaf, slot untuk kategori anda telah penuh. Kami tidak dapat "
        "menerima permohonan anda untuk event kali ini. Terima kasih "
        "atas minat anda. 🙏"
    ),
    "Maklumat tidak lengkap": (
        "Maaf, permohonan anda tidak dapat diproses kerana maklumat yang "
        "diberikan tidak lengkap. Sila hubungi admin untuk maklumat lanjut. 🙏"
    ),
    "Custom (taip sendiri)": "",
}


# ============================================================
# CANCEL TEMPLATES (untuk vendor yang dah bayar)
# ============================================================
CANCEL_TEMPLATES = {
    "Vendor cancel sendiri": (
        "Permohonan anda telah dibatalkan atas permintaan anda sendiri. "
        "Slot anda telah dilepaskan. Terima kasih kerana berminat. 🙏"
    ),
    "Vendor tak dapat hadir": (
        "Slot anda telah dibatalkan kerana ketidakupayaan untuk hadir ke event. "
        "Terima kasih atas maklum balas anda. 🙏"
    ),
    "Custom (taip sendiri)": "",
}


# ============================================================
# HELPER — CALLBACK TEMPLATE DROPDOWN
# ============================================================
def _on_reject_tpl_change(plate):
    tpl = st.session_state.get(f"reject_tpl_{plate}", "")
    if tpl and tpl != "Custom (taip sendiri)":
        st.session_state[f"reject_note_{plate}"] = REJECT_TEMPLATES.get(tpl, "")


def _on_cancel_tpl_change(plate):
    tpl = st.session_state.get(f"cancel_tpl_{plate}", "")
    if tpl and tpl != "Custom (taip sendiri)":
        st.session_state[f"cancel_note_{plate}"] = CANCEL_TEMPLATES.get(tpl, "")


# ============================================================
# COLUMN RESOLVER
# ============================================================
def _norm_key(s):
    if s is None:
        return ""
    s = str(s).replace("\ufeff", "").replace("\u00a0", " ")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def resolve_column(df_, exact_candidates, keywords=None, required=True, label=None):
    norm_map = {_norm_key(c): c for c in df_.columns}

    for cand in exact_candidates:
        k = _norm_key(cand)
        if k in norm_map:
            return norm_map[k]

    if keywords:
        kw = [_norm_key(k) for k in keywords]
        for col in df_.columns:
            n = _norm_key(col)
            if all(k in n for k in kw):
                return col

    if required:
        st.error(f"❌ Kolum tidak dijumpai: **{label or exact_candidates[0]}**")
        st.write("**Kolum sebenar dalam sheet (repr):**")
        st.write([repr(c) for c in df_.columns])
        st.info("Kemaskini `admin_page.py` untuk sepadan dengan nama di atas.")
        st.stop()
    return None


# ============================================================
# HELPERS
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


def _get_remark_col(df_):
    for c in df_.columns:
        cname = str(c).strip().lower()
        if cname in ("remark", "remarks"):
            return c
    for c in df_.columns:
        if "remark" in str(c).strip().lower():
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
    if raw is None or pd.isna(raw):
        return "—"
    s = str(raw).strip()
    if s == "" or s.lower() in ("nan", "none", "nat", "null", "—", "-"):
        return "—"

    formats = [
        "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M",
        "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d",
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


def _df_to_str(df_):
    out = df_.copy()
    for c in out.columns:
        out[c] = out[c].astype(str)
    return out


# ============================================================
# SAMBUNGAN DATA
# ============================================================
conn = st.connection("gsheets", type=GSheetsConnection)

df = load_sheet_safe(conn, "Vendors", ttl=0)

if df is None:
    st.stop()

COL_NAME     = resolve_column(df, ["Nama Perniagaan Syarikat", "Nama Perniagaan", "Business Name"],
                              keywords=["nama", "perniagaan"])
COL_PHONE    = resolve_column(df, ["Nombor Telefon/Phone Number", "Nombor Telefon", "Phone Number", "Telefon"],
                              keywords=["telefon"])
COL_TYPE     = resolve_column(df, ["Kategori Produk/Product Category", "Kategori Produk", "Product Category"],
                              keywords=["kategori"])
COL_CAT      = resolve_column(df, ["F&B CATEGORY", "FNB CATEGORY", "F&B Category"],
                              keywords=["category"], required=False)
COL_PLATE    = resolve_column(df, ["Plate Number", "No. Plate", "No Plate", "Nombor Plat"],
                              keywords=["plate"])
COL_ADDON    = resolve_column(df, ["ADD ON", "Add On", "Addon"],
                              keywords=["addon"], required=False)
COL_PRODUCTS = resolve_column(df, ["Senarai Produk yang Dijual", "Senarai Produk"],
                              keywords=["senarai", "produk"], required=False)
COL_REMARK   = resolve_column(df, ["Remark", "Remarks", "Catatan"],
                              keywords=["remark"], required=False)
PROOF_COL    = resolve_column(df, ["Upload Bukti Bayaran", "Bukti Bayaran"],
                              keywords=["bukti"], required=False) or "Upload Bukti Bayaran"

if COL_CAT is None:
    COL_CAT = "F&B CATEGORY"
    df[COL_CAT] = ""
if COL_ADDON is None:
    COL_ADDON = "ADD ON"
    df[COL_ADDON] = ""
if COL_PRODUCTS is None:
    COL_PRODUCTS = "Senarai Produk yang Dijual"
    df[COL_PRODUCTS] = ""
if COL_REMARK is None:
    COL_REMARK = "Remark"
    df[COL_REMARK] = ""

df[COL_TYPE] = df[COL_TYPE].apply(normalize_type)

_paid_col   = resolve_column(df, ["Paid", "PAID", "Bayar"], keywords=["paid"], required=False)
_status_col = resolve_column(df, ["Status", "STATUS"], keywords=["status"], required=False)

df["Paid"] = df[_paid_col].fillna(False).astype(bool) if _paid_col else False
df["Status"] = df[_status_col].apply(normalize_status) if _status_col else "Pending"

if COL_PHONE in df.columns:
    df[COL_PHONE] = df[COL_PHONE].apply(clean_phone_raw)

if "Notes" not in df.columns:
    df["Notes"] = ""
df["Notes"] = df["Notes"].astype("object").fillna("").astype(str)

# ============================================================
# LOAD PAYMENTS
# ============================================================
payments_df = load_sheet_safe(conn, "Payments", ttl=0)
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
    col_ft      = _pick_col(payments_df, "Pilih Food Truck Lot", "Food Truck Lot", "Food Truck", "FT Lot")
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


def safe_update(conn, df, sheet_name="Vendors"):
    try:
        fresh = load_sheet_safe(conn, sheet_name, ttl=0)
    except Exception:
        fresh = None

    if fresh is not None and len(fresh) > 0:
        if len(df) < len(fresh):
            st.error(
                f"⚠️ **Safety block**: Data yang nak diupdate ada **{len(df)}** baris, "
                f"tapi sheet sekarang ada **{len(fresh)}** baris. "
                f"Kemungkinan ada data baru dari sumber lain (form / admin lain). "
                f"Sila refresh page (tekan R) dan cuba lagi."
            )
            st.stop()

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
        "<div style='padding: 0.5rem 0 1.25rem 0;'>"
        "<div style='font-size: 1.15rem; font-weight: 800; color: #0c0a09; "
        "letter-spacing: -0.02em;'>Admin Panel</div>"
        "<div style='font-size: 0.72rem; color: #a8a29e; margin-top: 0.15rem; "
        "letter-spacing: 0.05em; text-transform: uppercase; font-weight: 600;'>"
        "Event Vendor Manager</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    section = st.radio(
        "NAVIGASI",
        options=[
            "🏠 Semua Section",
            "1️⃣ Dashboard",
            "2️⃣ Permohonan Menunggu",
            "3️⃣ Rekod Bayaran (Baru)",
            "4️⃣ Bayaran Pending",
            "5️⃣ Vendor Diluluskan",
            "6️⃣ Semua Vendor",
            "7️⃣ ⚙️ Tindakan Admin",
        ],
        label_visibility="visible",
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
            st.markdown(f"<div class='remark-box'>{vendor_remark}</div>", unsafe_allow_html=True)

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
        if st.button("Ya, Luluskan", type="primary", width="stretch", key="dlg_approve_yes"):
            df.loc[df[COL_PLATE] == plate, "Status"] = "Approved"
            df.loc[df[COL_PLATE] == plate, "Notes"] = admin_note.strip()
            safe_update(conn, df, sheet_name="Vendors")
            log_action(conn, ADMIN_NAME, "APPROVE", plate, f"Lulus: {vendor_name}")
            st.toast(f"✅ {plate} telah diluluskan", icon="✅")
            st.rerun()
    with col2:
        if st.button("Batal", width="stretch", key="dlg_approve_no"):
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
        if st.button("Ya, Tolak", type="primary", width="stretch", key="dlg_reject_yes"):
            if not reject_reason.strip():
                st.warning("⚠️ Sila masukkan sebab penolakan.")
            else:
                df.loc[df[COL_PLATE] == plate, "Status"] = "Rejected"
                df.loc[df[COL_PLATE] == plate, "Notes"] = reject_reason.strip()
                safe_update(conn, df, sheet_name="Vendors")
                log_action(conn, ADMIN_NAME, "REJECT", plate,
                           f"Tolak: {vendor_name} — Sebab: {reject_reason[:100]}")
                st.toast(f"❌ {plate} telah ditolak", icon="❌")
                st.rerun()
    with col2:
        if st.button("Batal", width="stretch", key="dlg_reject_no"):
            st.rerun()


@st.dialog("💰 Sahkan Bayaran", width="large")
def confirm_verify_payment_dialog(plate, vendor_name):
    st.markdown(
        "<div style='text-align:center; padding:0.5rem 0 1rem 0;'>"
        "<div style='font-size:3rem; line-height:1;'>💰</div>"
        "<div style='font-size:1.3rem; font-weight:700; color:#78350f; "
        "margin-top:0.5rem;'>Sahkan Bayaran Vendor?</div>"
        "<div style='font-size:0.85rem; color:#78716c; margin-top:0.35rem;'>"
        "Vendor akan ditandakan sebagai <b>Approved + Paid</b>.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div style='background:#fffbeb; border:1px solid #fde68a; "
        f"border-radius:10px; padding:0.8rem 1rem; margin:0.5rem 0;'>"
        f"<div style='font-size:1rem; font-weight:700; color:#78350f;'>"
        f"🚗 {plate} — {vendor_name}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    info = get_vendor_payment_info(plate)
    proof_url = info.get("proof_url", "")
    ts_display = format_timestamp_display(info.get("timestamp", ""))

    if proof_url:
        st.markdown("**📄 Bukti Bayaran:**")
        st.markdown(f"[🔗 Buka Bukti Bayaran]({proof_url})")
        if ts_display and ts_display != "—":
            st.caption(f"⏰ Dihantar: {ts_display}")

    vendor_row = df[df[COL_PLATE] == plate]
    if not vendor_row.empty:
        cur_status = vendor_row.iloc[0]["Status"]
        cur_paid = vendor_row.iloc[0]["Paid"]
        st.caption(f"Status semasa: **{cur_status}** · Paid: **{cur_paid}**")

    lot_parts = []
    if info.get("parking_lot"):
        lot_parts.append(f"Parking: {info['parking_lot']}")
    if info.get("fnb_lot"):
        lot_parts.append(f"F&B: {info['fnb_lot']}")
    if info.get("ft_lot"):
        lot_parts.append(f"Food Truck: {info['ft_lot']}")
    if info.get("arts_lot"):
        lot_parts.append(f"Arts/Crafts: {info['arts_lot']}")
    if lot_parts:
        st.caption("📍 Lot dipilih: " + " · ".join(lot_parts))

    st.markdown("")
    st.info("Selepas disahkan, vendor akan masuk ke **Section 5 — Vendor Diluluskan**.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Ya, Sahkan", type="primary", width="stretch",
                     key=f"dlg_verify_yes_{plate}"):
            df.loc[df[COL_PLATE] == plate, "Paid"] = True
            df.loc[df[COL_PLATE] == plate, "Status"] = "Approved"
            safe_update(conn, df, sheet_name="Vendors")
            log_action(conn, ADMIN_NAME, "VERIFY_PAYMENT", plate,
                       f"Sahkan bayaran: {vendor_name}")
            st.toast(f"💰 {plate} bayaran disahkan", icon="💰")
            st.rerun()
    with col2:
        if st.button("Batal", width="stretch", key=f"dlg_verify_no_{plate}"):
            st.rerun()


@st.dialog("🚫 Reject Vendor", width="large")
def reject_unpaid_dialog(plate, vendor_name, vendor_type):
    st.markdown(
        "<div style='text-align:center; padding:0.5rem 0 1rem 0;'>"
        "<div style='font-size:3rem; line-height:1;'>🚫</div>"
        "<div style='font-size:1.3rem; font-weight:700; color:#991b1b; "
        "margin-top:0.5rem;'>Reject Vendor Ini?</div>"
        "<div style='font-size:0.85rem; color:#78716c; margin-top:0.35rem;'>"
        "Ayat di bawah akan dipaparkan kepada vendor.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div style='background:#fef2f2; border:1px solid #fecaca; "
        f"border-radius:10px; padding:0.8rem 1rem; margin:0.5rem 0;'>"
        f"<div style='font-size:1rem; font-weight:700; color:#991b1b;'>"
        f"🚗 {plate} — {vendor_name}</div>"
        f"<div style='font-size:0.82rem; color:#7f1d1d; margin-top:0.2rem;'>"
        f"Kategori: {vendor_type}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("")

    # Pre-fill Notes lama
    existing_note = ""
    vendor_row = df[df[COL_PLATE] == plate]
    if not vendor_row.empty:
        val = vendor_row.iloc[0].get("Notes", "")
        if pd.notna(val) and str(val).strip() and str(val).strip().lower() not in ("nan", "none", "null"):
            existing_note = str(val).strip()

    note_key = f"reject_note_{plate}"
    if note_key not in st.session_state:
        st.session_state[note_key] = existing_note

    tpl_key = f"reject_tpl_{plate}"
    if tpl_key not in st.session_state:
        st.session_state[tpl_key] = "Custom (taip sendiri)"

    st.selectbox(
        "Pilih template ayat:",
        options=list(REJECT_TEMPLATES.keys()),
        key=tpl_key,
        on_change=_on_reject_tpl_change,
        args=(plate,),
    )

    reject_note = st.text_area(
        "Ayat untuk vendor (boleh edit):",
        key=note_key,
        height=160,
        help="Ayat ini akan dipaparkan di page Semak Kelayakan.",
    )

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚫 Ya, Reject", type="primary", width="stretch",
                     key=f"dlg_reject_unpaid_yes_{plate}"):
            if not reject_note.strip():
                st.warning("⚠️ Sila masukkan ayat untuk vendor.")
            else:
                df.loc[df[COL_PLATE] == plate, "Status"] = "Rejected"
                df.loc[df[COL_PLATE] == plate, "Notes"] = reject_note.strip()
                safe_update(conn, df, sheet_name="Vendors")
                log_action(conn, ADMIN_NAME, "REJECT_UNPAID", plate,
                           f"Tolak (belum bayar): {vendor_name}")
                st.session_state.pop(note_key, None)
                st.session_state.pop(tpl_key, None)
                st.toast(f"🚫 {plate} telah direject", icon="🚫")
                st.rerun()
    with col2:
        if st.button("Batal", width="stretch", key=f"dlg_reject_unpaid_no_{plate}"):
            st.session_state.pop(note_key, None)
            st.session_state.pop(tpl_key, None)
            st.rerun()


@st.dialog("🚫 Cancel Vendor (Dah Bayar)", width="large")
def cancel_paid_dialog(plate, vendor_name, vendor_type):
    st.markdown(
        "<div style='text-align:center; padding:0.5rem 0 1rem 0;'>"
        "<div style='font-size:3rem; line-height:1;'>🚫</div>"
        "<div style='font-size:1.3rem; font-weight:700; color:#991b1b; "
        "margin-top:0.5rem;'>Cancel Vendor Ini?</div>"
        "<div style='font-size:0.85rem; color:#78716c; margin-top:0.35rem;'>"
        "Vendor ini <b>dah bayar</b>. Status akan ditukar ke <b>Cancelled</b>."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div style='background:#fef2f2; border:1px solid #fecaca; "
        f"border-radius:10px; padding:0.8rem 1rem; margin:0.5rem 0;'>"
        f"<div style='font-size:1rem; font-weight:700; color:#991b1b;'>"
        f"🚗 {plate} — {vendor_name}</div>"
        f"<div style='font-size:0.82rem; color:#7f1d1d; margin-top:0.2rem;'>"
        f"Kategori: {vendor_type}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    info = get_vendor_payment_info(plate)
    ts_display = format_timestamp_display(info.get("timestamp", ""))
    proof_url = info.get("proof_url", "")

    if proof_url:
        st.caption(f"💰 Bukti bayaran: [Buka 📄]({proof_url}) · {ts_display}")

    st.markdown("---")

    # Pre-fill Notes lama
    existing_note = ""
    vendor_row = df[df[COL_PLATE] == plate]
    if not vendor_row.empty:
        val = vendor_row.iloc[0].get("Notes", "")
        if pd.notna(val) and str(val).strip() and str(val).strip().lower() not in ("nan", "none", "null"):
            existing_note = str(val).strip()

    note_key = f"cancel_note_{plate}"
    if note_key not in st.session_state:
        st.session_state[note_key] = existing_note

    tpl_key = f"cancel_tpl_{plate}"
    if tpl_key not in st.session_state:
        st.session_state[tpl_key] = "Custom (taip sendiri)"

    st.selectbox(
        "Pilih template ayat untuk vendor:",
        options=list(CANCEL_TEMPLATES.keys()),
        key=tpl_key,
        on_change=_on_cancel_tpl_change,
        args=(plate,),
    )

    cancel_note = st.text_area(
        "Ayat untuk vendor (boleh edit):",
        key=note_key,
        height=140,
        help="Ayat ini akan dipaparkan di page Semak Kelayakan.",
    )

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚫 Ya, Cancel", type="primary", width="stretch",
                     key=f"dlg_cancel_paid_yes_{plate}"):
            if not cancel_note.strip():
                st.warning("⚠️ Sila masukkan ayat untuk vendor.")
            else:
                df.loc[df[COL_PLATE] == plate, "Status"] = "Cancelled"
                df.loc[df[COL_PLATE] == plate, "Notes"] = cancel_note.strip()
                safe_update(conn, df, sheet_name="Vendors")
                log_action(
                    conn, ADMIN_NAME, "CANCEL_PAID", plate,
                    f"Cancel (dah bayar): {vendor_name}"
                )
                st.session_state.pop(note_key, None)
                st.session_state.pop(tpl_key, None)
                st.toast(f"🚫 {plate} telah dicancel", icon="🚫")
                st.rerun()
    with col2:
        if st.button("Batal", width="stretch", key=f"dlg_cancel_paid_no_{plate}"):
            st.session_state.pop(note_key, None)
            st.session_state.pop(tpl_key, None)
            st.rerun()


@st.dialog("Sahkan Penolakan")
def confirm_cancel_all_dialog(count):
    st.warning(f"Anda akan **reject {count}** vendor yang belum bayar.")
    st.caption("Status akan ditukar ke **Rejected** dengan ayat default di bawah.")
    st.write("Tindakan ini tidak boleh diundur.")

    default_reason = (
        "Maaf, tempahan slot anda telah dibatalkan kerana bayaran tidak "
        "diterima sebelum tarikh akhir yang ditetapkan. Slot anda kini "
        "telah dibuka semula kepada vendor lain. Terima kasih atas "
        "minat anda. 🙏"
    )

    bulk_reason = st.text_area(
        "Ayat untuk vendor (boleh edit):",
        value=default_reason,
        height=140,
        key="bulk_cancel_reason",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Reject Semua", type="primary", width="stretch", key="dlg_cancel_yes"):
            if not bulk_reason.strip():
                st.warning("⚠️ Sila masukkan ayat untuk vendor.")
            else:
                mask = (df["Status"] == "Approved") & (~df["Paid"])
                df.loc[mask, "Status"] = "Rejected"
                df.loc[mask, "Notes"] = bulk_reason.strip()
                safe_update(conn, df, sheet_name="Vendors")
                log_action(conn, ADMIN_NAME, "REJECT_ALL_UNPAID", "-",
                           f"{count} vendor belum bayar ditolak")
                st.toast(f"✅ {count} vendor telah ditolak", icon="✅")
                st.rerun()
    with col2:
        if st.button("Batal", width="stretch", key="dlg_cancel_no"):
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
        if st.button("Simpan", type="primary", width="stretch", key="edit_save"):
            idx = df[df[COL_PLATE] == plate].index[0]
            df.at[idx, COL_NAME] = new_name
            df.at[idx, COL_PHONE] = clean_phone_raw(new_phone)
            df.at[idx, COL_TYPE] = new_type
            df.at[idx, COL_CAT] = new_cat
            df.at[idx, COL_PLATE] = new_plate
            df.at[idx, COL_ADDON] = new_addon
            safe_update(conn, df, sheet_name="Vendors")
            log_action(conn, ADMIN_NAME, "EDIT", plate, f"Nama: {new_name}, Plate: {new_plate}")
            st.toast(f"✅ {plate} telah dikemaskini", icon="✅")
            st.rerun()
    with col2:
        if st.button("Batal", width="stretch", key="edit_cancel"):
            st.rerun()


@st.dialog("Sahkan Padam")
def confirm_delete_dialog(plate, vendor_name, row_signature):
    st.warning("Anda akan **memadam** 1 baris rekod vendor ini:")
    st.markdown(f"**No. Plate:** `{plate}`  \n**Nama:** {vendor_name}")
    st.write("")
    st.error("⚠️ **Tindakan ini tidak boleh diundur.** Data akan dibuang dari Google Sheet.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Padam", type="primary", width="stretch", key="dlg_delete_yes"):
            global df
            matched_idx = None
            for i, r in df.iterrows():
                sig = tuple(str(r.get(c, "")) for c in df.columns)
                if sig == row_signature:
                    matched_idx = i
                    break

            if matched_idx is not None:
                df = df.drop(matched_idx).reset_index(drop=True)
                safe_update(conn, df, sheet_name="Vendors")
                log_action(conn, ADMIN_NAME, "DELETE", plate, f"Padam Vendor: {vendor_name}")
                st.toast(f"🗑️ 1 baris {plate} telah dipadam", icon="🗑️")
                st.rerun()
            else:
                st.error("❌ Baris tidak dijumpai — mungkin sudah dipadam.")

    with col2:
        if st.button("Batal", width="stretch", key="dlg_delete_no"):
            st.rerun()


# ============================================================
# WHATSAPP GROUP BANNER
# ============================================================
try:
    wa_group = st.secrets["event"]["whatsapp_group"]
except Exception:
    wa_group = ""

if wa_group:
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border: 1px solid #fde68a;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    ">
        <div>
            <div style="font-weight: 700; color: #0c0a09; font-size: 0.95rem; letter-spacing: -0.01em;">
                💬 WhatsApp Group Vendor
            </div>
            <div style="color: #78350f; font-size: 0.82rem; margin-top: 0.25rem;">
                Hantar mesej terus dalam group
            </div>
        </div>
        <a href="{wa_group}" target="_blank" style="
            background-color: #78350f;
            color: #ffffff;
            padding: 0.55rem 1.15rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.85rem;
            white-space: nowrap;
        ">Buka Group →</a>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# SECTION 1 — DASHBOARD
# ============================================================
if show_section("1️⃣ Dashboard"):
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

    section_header("1", "Dashboard", "Ringkasan slot & permohonan vendor", f"{total_approved} / {total_limit}")

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

    st.caption(f"📅 Event: **{EVENT_DATE.strftime('%d %b %Y')}** &nbsp;·&nbsp; ✅ Approved &nbsp;·&nbsp; ⏳ Pending")

    st.markdown("---")
    sub_header("Pecahan Kategori F&B")
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
    st.dataframe(_df_to_str(fb_df), hide_index=True, width="stretch")

    st.divider()


# ============================================================
# SECTION 2 — PERMOHONAN MENUNGGU
# ============================================================
if show_section("2️⃣ Permohonan Menunggu"):
    pending_df = df[df["Status"] == "Pending"]
    section_header("2", "Permohonan Menunggu", "Semak & luluskan permohonan vendor baru", len(pending_df))

    try:
        form_url = st.secrets["event"].get("google_form_responses_url", "")
    except Exception:
        form_url = ""

    if form_url:
        st.markdown(f"""
        <div style="
            background: #fafaf9;
            border: 1px solid #e7e5e4;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            margin-bottom: 1.25rem;
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
                padding: 0.5rem 1rem;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                font-size: 0.82rem;
                white-space: nowrap;
            ">Buka Form →</a>
        </div>
        """, unsafe_allow_html=True)

    products_col = _get_products_col(df)
    remark_col = _get_remark_col(df)

    if pending_df.empty:
        st.markdown(
            "<div class='empty-state'>"
            "<div class='empty-state-icon'>📭</div>"
            "<div class='empty-state-text'>Tiada permohonan yang menunggu.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
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
                f"<b>{len(pending_df)}</b> permohonan</div>",
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
            list_height = min(max(len(filtered) * 340, 340), 1200)

            with st.container(height=list_height, border=False):
                for idx, (_, row) in enumerate(filtered.iterrows()):
                    plate = row[COL_PLATE]
                    name = row[COL_NAME]
                    v_type = row[COL_TYPE]
                    v_cat = clean_cat_str(row.get(COL_CAT, ""))
                    phone = format_phone_display(row[COL_PHONE])

                    with st.container(border=True):
                        st.markdown(
                            f"<div style='font-size: 1.05rem; font-weight: 700; color: #0c0a09; "
                            f"margin-bottom: 0.35rem; letter-spacing: -0.01em;'>"
                            f"📋 {plate} — {name}</div>"
                            f"<div style='font-size: 0.85rem; color: #57534e; margin-bottom: 0.2rem;'>"
                            f"<span class='badge badge-info'>{v_type}</span>"
                            f"{' <span class=\"badge badge-neutral\">' + v_cat + '</span>' if v_cat else ''}"
                            f"</div>"
                            f"<div style='font-size: 0.85rem; color: #78716c; margin-bottom: 0.5rem;'>"
                            f"📞 {phone}</div>",
                            unsafe_allow_html=True,
                        )

                        products_text = clean_products_str(row.get(products_col, "")) if products_col else ""
                        if products_text:
                            st.markdown(
                                f"<div style='font-size:0.72rem; font-weight:700; color:#78350f; "
                                f"text-transform:uppercase; letter-spacing:0.06em; margin:0.5rem 0 0.35rem 0;'>"
                                f"🛍️ Senarai Produk</div>"
                                f"<div class='product-box'>{products_text}</div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.caption("🛍️ _(Tiada senarai produk diisi)_")

                        v_total = get_vendor_total(v_type, row.get(COL_ADDON, ""))
                        st.caption(f"💰 Total: {format_rm(v_total)}")

                        remark_text = clean_text(row.get(remark_col, "")) if remark_col else ""
                        st.markdown(
                            f"<div style='font-size:0.72rem; font-weight:700; color:#92400e; "
                            f"text-transform:uppercase; letter-spacing:0.06em; margin:0.5rem 0 0.35rem 0;'>"
                            f"📝 Remark Vendor</div>",
                            unsafe_allow_html=True,
                        )
                        if remark_text:
                            st.markdown(f"<div class='remark-box'>{remark_text}</div>", unsafe_allow_html=True)
                        else:
                            st.caption("_(Tiada remark dari vendor)_")

                        b1, b2, b3, _ = st.columns([1, 1, 1, 3])

                        with b1:
                            if st.button("✓ Lulus", type="primary", width="stretch", key=f"approve_{plate}_{idx}"):
                                confirm_approve_dialog(plate, name)
                        with b2:
                            if st.button("✗ Tolak", width="stretch", key=f"reject_{plate}_{idx}"):
                                confirm_reject_dialog(plate, name)
                        with b3:
                            if st.button("✎ Edit", width="stretch", key=f"edit_{plate}_{idx}"):
                                edit_vendor_dialog(plate)

    st.divider()
    
