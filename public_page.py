import streamlit as st
import pandas as pd
import re
import time

from streamlit_gsheets import GSheetsConnection
from style import apply_style
from components import page_header, load_sheet_safe


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="Semak Kelayakan", layout="wide")
apply_style()
page_header()


# ============================================================
# KONFIGURASI
# ============================================================
COL_NAME = "Nama Perniagaan Syarikat"
COL_PHONE = "Nombor Telefon/Phone Number"
COL_TYPE = "Kategori Produk/Product Category"
COL_CAT = "F&B CATEGORY"
COL_PLATE = "Plate Number"
COL_ADDON = "ADD ON"
COL_REMARK = "Remark"

PROOF_COL = "Upload Bukti Bayaran dan Pemilihan Lot"

VALID_STATUSES = ["Pending", "Approved", "Rejected", "Cancelled"]


# ============================================================
# HELPERS
# ============================================================
def normalize_status(raw):
    if raw is None or pd.isna(raw):
        return "Pending"
    if str(raw).strip() == "":
        return "Pending"
    s = str(raw).strip().title()
    aliases = {
        "Menunggu": "Pending", "Waiting": "Pending", "New": "Pending",
        "Approve": "Approved", "Reject": "Rejected",
        "Cancel": "Cancelled", "Canceled": "Cancelled",
    }
    s = aliases.get(s, s)
    return s if s in VALID_STATUSES else "Pending"


def get_category_price(vendor_type):
    try:
        if vendor_type == "Car Boot Sales":
            return float(st.secrets["event"]["price_car_boot"])
        elif vendor_type == "F&B":
            return float(st.secrets["event"]["price_fb"])
        elif vendor_type == "Food Truck":
            return float(st.secrets["event"]["price_ft"])
        else:
            return float(st.secrets["event"]["price_others"])
    except Exception:
        return 0.0


def get_deposit(vendor_type):
    try:
        if vendor_type == "F&B":
            return float(st.secrets["event"]["deposit_fb"])
        elif vendor_type == "Food Truck":
            return float(st.secrets["event"]["deposit_ft"])
        elif vendor_type == "Arts/Crafts & Others":
            return float(st.secrets["event"].get("deposit_others", 100))
        return 0.0
    except Exception:
        return 0.0


def get_addon_price(addon_str):
    if addon_str is None or pd.isna(addon_str):
        return 0.0
    try:
        matches = re.findall(r"RM\s*([0-9]+(?:\.[0-9]+)?)", str(addon_str))
        return sum(float(m) for m in matches)
    except Exception:
        return 0.0


def format_rm(amount):
    try:
        return f"RM {float(amount):,.2f}"
    except (ValueError, TypeError):
        return "RM 0.00"


def clean_text_field(raw):
    """Return clean string or '' if empty/NaN/null."""
    if raw is None or pd.isna(raw):
        return ""
    s = str(raw).strip()
    if s.lower() in ("", "nan", "none", "nat", "null"):
        return ""
    return s


def find_products_column(df_):
    """Auto-detect the products column name (tolerates whitespace/newlines)."""
    for c in df_.columns:
        if "Senarai Produk yang Dijual" in str(c):
            return c
    return None


def get_vendor_payment_info(payments_df, plate_norm):
    if payments_df is None or payments_df.empty:
        return {}
    if "Plate Number" not in payments_df.columns:
        return {}

    matched = payments_df[
        payments_df["Plate Number"].astype(str).str.upper().str.replace(" ", "") == plate_norm
    ]
    if matched.empty:
        return {}

    try:
        matched = matched.sort_values("Timestamp", ascending=False)
    except Exception:
        pass

    latest = matched.iloc[0]

    def _clean(v):
        s = str(v or "").strip()
        if s.lower() in ("nan", "none", "nat", "null"):
            return ""
        return s

    return {
        "proof_url": _clean(latest.get(PROOF_COL, "")),
        "folder_url": _clean(latest.get("FolderUrl", "")),
        "timestamp": _clean(latest.get("Timestamp", "")),
        "pilih_jenis": _clean(latest.get("Pilih Jenis", "")),
        "parking_lot": _clean(latest.get("Pilih parking lot", "")),
        "fnb_lot": _clean(latest.get("Pilih F&B Lot", "")),
        "ft_lot": _clean(latest.get("Pilih Food Truck Lot", "") or latest.get("Pilih F&B Lot", "")),
        "arts_lot": _clean(
            latest.get("Pilih Arts/Crafts & Others Lot", "")
            or latest.get("Pilih Arts & Crafts / Toys Lot", "")
        ),
    }


def render_products_box(products_text):
    """Papar senarai produk dalam box berwarna."""
    st.markdown(
        "<div style='background:#faf5ec; border-left:4px solid #78350f; "
        "border-radius:8px; padding:0.75rem 1rem; margin:0.5rem 0;'>"
        "<div style='font-size:0.72rem; color:#78350f; letter-spacing:0.04em; "
        "font-weight:700; text-transform:uppercase; margin-bottom:0.35rem;'>"
        "🛍️ Senarai Produk Anda</div>"
        f"<div style='font-size:0.85rem; color:#44403c; white-space:pre-wrap; "
        f"line-height:1.5;'>{products_text}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# POPUP — TA'AHNIAH (Approved + Paid)
# ============================================================
@st.dialog("🎉 Tahniah!", width="large")
def show_success_dialog(row, plate, status, paid, slot_items):
    """Popup tahniah untuk vendor yang dah paid."""

    # ---- Header congratulation ----
    st.markdown(
        "<div style='text-align:center; padding:0.5rem 0 1rem 0;'>"
        "<div style='font-size:3rem; line-height:1;'>🎉</div>"
        "<div style='font-size:1.4rem; font-weight:700; color:#14532d; "
        "margin-top:0.5rem;'>Pendaftaran Berjaya Disahkan!</div>"
        "<div style='font-size:0.85rem; color:#78716c; margin-top:0.35rem;'>"
        "Terima kasih kerana menyertai event kami.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ---- Info vendor (plate, nama, kategori) ----
    cat_str = ""
    if pd.notna(row.get(COL_CAT)) and str(row.get(COL_CAT)).strip():
        cat_str = f" · {row[COL_CAT]}"

    st.markdown(
        f"<div style='background:#f0fdf4; border:1px solid #bbf7d0; "
        f"border-radius:10px; padding:0.8rem 1rem; margin:0.5rem 0;'>"
        f"<div style='font-size:1rem; font-weight:700; color:#14532d;'>"
        f"🚗 {plate} — {row[COL_NAME]}</div>"
        f"<div style='font-size:0.82rem; color:#166534; margin-top:0.2rem;'>"
        f"{row[COL_TYPE]}{cat_str}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ---- Slot info ----
    if slot_items:
        st.markdown(
            "<div style='font-size:0.72rem; color:#78716c; letter-spacing:0.04em; "
            "font-weight:600; text-transform:uppercase; margin-top:0.75rem; "
            "margin-bottom:0.35rem;'>📍 Maklumat Slot Anda</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(2)
        for i, (label, val) in enumerate(slot_items):
            with cols[i % 2]:
                st.markdown(
                    f"<div style='background:#f7f3ee; border-radius:8px; "
                    f"padding:0.55rem 0.75rem; margin-bottom:0.4rem; font-size:0.85rem;'>"
                    f"<b>{label}:</b> {val}</div>",
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)

    # ---- Reminder WhatsApp ----
    st.info(
        "📌 **Jangan lupa join WhatsApp Group Vendor** — "
        "untuk update terkini tentang event, susun atur booth, "
        "parking lot, dan pengumuman penting."
    )

    # ---- Button Join WhatsApp (besar) ----
    st.link_button(
        "💬 Join WhatsApp Group Vendor",
        st.secrets["event"]["whatsapp_group"],
        width="stretch",
        type="primary",
    )

    # ---- Button tutup ----
    if st.button("Tutup", width="stretch"):
        st.rerun()


# ============================================================
# POPUP — MAKLUMAT PEMBAYARAN (Approved + Belum Bayar)
# ============================================================
@st.dialog("💳 Maklumat Pembayaran", width="large")
def show_payment_dialog(row, plate, vendor_type, cat_price, deposit_amount, addon_price, total_price, admin_note=""):
    """Popup maklumat bayaran untuk vendor yang dah lulus tapi belum bayar."""

    # ---- Header: Total besar ----
    st.markdown(
        f"<div style='text-align:center; padding:0.5rem 0 0.75rem 0;'>"
        f"<div style='font-size:0.72rem; color:#9a3412; letter-spacing:0.04em; "
        f"font-weight:700; text-transform:uppercase;'>💰 Jumlah Perlu Dibayar</div>"
        f"<div style='font-size:2.2rem; font-weight:800; color:#7c2d12; "
        f"line-height:1.1; margin-top:0.35rem;'>{format_rm(total_price)}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ---- Info vendor ringkas ----
    st.markdown(
        f"<div style='font-size:0.85rem; color:#57534e; text-align:center; "
        f"margin-bottom:0.75rem;'>🚗 <b>{plate}</b> — {row[COL_NAME]}</div>",
        unsafe_allow_html=True,
    )

    # ---- Breakdown kategori ----
    breakdown_lines = [
        f"<div style='display:flex; justify-content:space-between; padding:0.35rem 0; "
        f"font-size:0.88rem; border-bottom:1px solid #f5f5f4;'>"
        f"<span style='color:#57534e;'>📦 {vendor_type}</span>"
        f"<span style='color:#1c1917; font-weight:600;'>{format_rm(cat_price)}</span>"
        f"</div>"
    ]
    if deposit_amount > 0:
        breakdown_lines.append(
            f"<div style='display:flex; justify-content:space-between; padding:0.35rem 0; "
            f"font-size:0.88rem; border-bottom:1px solid #f5f5f4;'>"
            f"<span style='color:#57534e;'>🔒 Deposit (Refundable)</span>"
            f"<span style='color:#1c1917; font-weight:600;'>{format_rm(deposit_amount)}</span>"
            f"</div>"
        )
    if addon_price > 0:
        breakdown_lines.append(
            f"<div style='display:flex; justify-content:space-between; padding:0.35rem 0; "
            f"font-size:0.88rem; border-bottom:1px solid #f5f5f4;'>"
            f"<span style='color:#57534e;'>➕ Add On</span>"
            f"<span style='color:#1c1917; font-weight:600;'>{format_rm(addon_price)}</span>"
            f"</div>"
        )

    st.markdown(
        f"<div style='background:#fafaf9; border-radius:8px; padding:0.6rem 0.9rem; "
        f"margin:0.5rem 0;'>{''.join(breakdown_lines)}</div>",
        unsafe_allow_html=True,
    )

    # ---- Nota dari Admin ----
    if admin_note:
        st.markdown(
            "<div style='font-size:0.72rem; color:#78716c; letter-spacing:0.04em; "
            "font-weight:700; text-transform:uppercase; margin-top:0.75rem; "
            "margin-bottom:0.35rem;'>📝 Nota dari Admin</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='background:#eff6ff; border-left:4px solid #2563eb; "
            f"border-radius:8px; padding:0.85rem 1rem; font-size:0.88rem; "
            f"color:#44403c; white-space:pre-wrap; line-height:1.6;'>"
            f"{admin_note}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    # ---- Maklumat Bank ----
    st.markdown(
        "<div style='font-size:0.72rem; color:#78716c; letter-spacing:0.04em; "
        "font-weight:700; text-transform:uppercase; margin-bottom:0.35rem;'>"
        "🏦 Maklumat Bank</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='background:#eff6ff; border:1px solid #bfdbfe; "
        "border-radius:8px; padding:0.75rem 1rem; font-size:0.88rem; line-height:1.7;'>"
        "<b>Bank:</b> MAYBANK<br>"
        "<b>Nama Akaun:</b> PRINTHERO MERCHANDISE SDN. BHD.<br>"
        "<b>No. Akaun:</b> <code style='background:#fff; padding:0.15rem 0.4rem; "
        "border-radius:4px; font-size:0.95rem;'>557054621057</code><br>"
        "<b>Remark:</b> <code style='background:#fff; padding:0.15rem 0.4rem; "
        "border-radius:4px;'>PFMCBS</code> + 4 digit akhir No. Telefon<br>"
        "<span style='color:#78716c; font-size:0.8rem;'>Contoh: "
        "<code style='background:#fff; padding:0.1rem 0.3rem; border-radius:4px;'>"
        "PFMCBS1234</code></span>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    # ---- Nota penting ----
    st.warning("📄 Sila upload bukti bayaran dalam **format PDF sahaja**.")

    # ---- Button Upload (besar, primary) ----
    st.link_button(
        "📤 Upload Bukti Bayaran dan Pemilihan Slot",
        st.secrets["event"]["payment_form_url"],
        width="stretch",
        type="primary",
    )

    # ---- Button tutup ----
    if st.button("Tutup", width="stretch"):
        st.rerun()


# ============================================================
# POPUP — REJECT (Rejected)
# ============================================================
@st.dialog("✕ Permohonan Tidak Berjaya", width="large")
def show_reject_dialog(row, plate, reject_reason):
    """Popup untuk vendor yang direject — sama gaya dengan tahniah."""

    # ---- Header ----
    st.markdown(
        "<div style='text-align:center; padding:0.5rem 0 1rem 0;'>"
        "<div style='font-size:1.3rem; font-weight:700; color:#991b1b; "
        "margin-top:0.5rem;'>Permohonan Tidak Berjaya</div>"
        "<div style='font-size:0.85rem; color:#78716c; margin-top:0.35rem;'>"
        "Maaf, permohonan anda tidak dapat diterima untuk event ini.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ---- Info vendor ----
    cat_str = ""
    if pd.notna(row.get(COL_CAT)) and str(row.get(COL_CAT)).strip():
        cat_str = f" · {row[COL_CAT]}"

    st.markdown(
        f"<div style='background:#fef2f2; border:1px solid #fecaca; "
        f"border-radius:10px; padding:0.8rem 1rem; margin:0.5rem 0;'>"
        f"<div style='font-size:1rem; font-weight:700; color:#991b1b;'>"
        f"🚗 {plate} — {row[COL_NAME]}</div>"
        f"<div style='font-size:0.82rem; color:#7f1d1d; margin-top:0.2rem;'>"
        f"{row[COL_TYPE]}{cat_str}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ---- Ayat admin ----
    if reject_reason:
        st.markdown(
            "<div style='font-size:0.72rem; color:#78716c; letter-spacing:0.04em; "
            "font-weight:600; text-transform:uppercase; margin-top:0.75rem; "
            "margin-bottom:0.35rem;'>📋 Mesej dari Admin</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='background:#fff7ed; border-left:4px solid #dc2626; "
            f"border-radius:8px; padding:0.85rem 1rem; font-size:0.88rem; "
            f"color:#44403c; white-space:pre-wrap; line-height:1.6;'>"
            f"{reject_reason}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info(
            "Hubungi admin untuk maklumat lanjut tentang sebab "
            "permohonan anda tidak diterima."
        )

    st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)

    # ---- Button tutup ----
    if st.button("Tutup", width="stretch"):
        st.rerun()


# ============================================================
# TITLE
# ============================================================
st.title("🔍 Semak Kelayakan")
st.caption("Masukkan No. Pendaftaran Kenderaan/Plate Number anda untuk semak status.")


# ============================================================
# LOAD VENDORS
# ============================================================
@st.cache_data(ttl=300, show_spinner="Memuatkan data...")
def load_vendors():
    conn = st.connection("gsheets", type=GSheetsConnection)
    last_err = None
    for attempt in range(3):
        try:
            return conn.read(worksheet="Vendors", ttl=300), None
        except Exception as e:
            last_err = str(e)
            if attempt < 2:
                time.sleep(2)
    return None, last_err


@st.cache_data(ttl=300, show_spinner=False)
def load_payments():
    conn = st.connection("gsheets", type=GSheetsConnection)
    last_err = None
    for attempt in range(3):
        try:
            return conn.read(worksheet="Payments", ttl=300), None
        except Exception as e:
            last_err = str(e)
            if attempt < 2:
                time.sleep(2)
    return None, last_err


# ============================================================
# GET VENDORS DATA
# ============================================================
df, err = load_vendors()

if df is None:
    error_msg = (err or "").lower()
    if "429" in error_msg or "quota" in error_msg:
        st.warning("⏳ **Sistem sedang sibuk.** Sila tunggu 1-2 minit dan cuba lagi.")
    elif any(k in error_msg for k in ("timeout", "connection", "timed out")):
        st.warning("🌐 **Masalah sambungan.** Sila cuba lagi sebentar.")
    else:
        st.error("⚠️ Sistem tidak dapat memuatkan data.")
        with st.expander("Butiran teknikal"):
            st.code(err)

    if st.button("🔄 Cuba Lagi"):
        st.cache_data.clear()
        st.rerun()
    st.stop()


# ============================================================
# NORMALIZE STATUS
# ============================================================
if "Status" not in df.columns:
    df["Status"] = "Pending"
else:
    df["Status"] = df["Status"].apply(normalize_status)


# ============================================================
# WHATSAPP ADMIN
# ============================================================
WA_ADMIN = "601157727459"
WA_TEXT = "Hi! Pertanyaan tentang vendor carbootsale PFM : ."


def _encode_wa(text):
    return (
        text.replace(" ", "%20")
        .replace("\n", "%0A")
        .replace(",", "%2C")
        .replace("?", "%3F")
        .replace("&", "%26")
    )


WA_URL = f"https://wa.me/{WA_ADMIN}?text={_encode_wa(WA_TEXT)}"


# ============================================================
# SEARCH FORM
# ============================================================
with st.form("search"):
    query = st.text_input(
        "No. Pendaftaran Kenderaan/Plate Number",
        placeholder="Contoh: NNA1806",
    ).strip().upper()

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col2:
        submitted = st.form_submit_button("Semak Status", type="primary", width="stretch")
    with col3:
        st.link_button("💬 WhatsApp Admin", WA_URL, width="stretch", key="wa_admin_btn")


# ============================================================
# RESULT
# ============================================================
if submitted and query:

    result = df[
        df[COL_PLATE].astype(str).str.upper().str.replace(" ", "") == query.replace(" ", "")
    ]

    # --------------------------------------------------------
    # NO RESULT
    # --------------------------------------------------------
    if result.empty:
        st.divider()
        with st.container(border=True):
            st.error("❌ **Tiada permohonan dijumpai**")
            st.markdown(f"**{query}** tidak ada dalam sistem. Sila daftar atau hubungi admin.")
            st.link_button(
                "📝 Daftar Sekarang",
                "https://forms.gle/bheUdQTvKRTCns4eA",
                width="stretch",
                type="primary",
            )

    # --------------------------------------------------------
    # FOUND
    # --------------------------------------------------------
    else:
        row = result.iloc[0]
        status = str(row["Status"]).strip()
        paid = bool(row["Paid"]) if "Paid" in row and pd.notna(row["Paid"]) else False
        plate_norm = str(row[COL_PLATE]).upper().replace(" ", "")

        # ====================================================
        # INFO CARD (compact — inline style)
        # ====================================================
        cat_str = ""
        if pd.notna(row.get(COL_CAT)) and str(row.get(COL_CAT)).strip():
            cat_str = f" · {row[COL_CAT]}"

        st.markdown(
            f"<div style='background:#fafaf9; border:1px solid #e5e5e5; border-radius:10px; "
            f"padding:0.6rem 0.9rem; margin:0.5rem 0;'>"
            f"<div style='font-size:1rem; font-weight:700; color:#292524;'>"
            f"🚗 {row[COL_PLATE]} — {row[COL_NAME]}</div>"
            f"<div style='font-size:0.8rem; color:#57534e; margin-top:0.15rem;'>"
            f"{row[COL_TYPE]}{cat_str}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # ====================================================
        # AMBIL INFO PAYMENT
        # ====================================================
        payments_df, pay_err = load_payments()
        if payments_df is None:
            payments_df = pd.DataFrame()

        payment_info = get_vendor_payment_info(payments_df, plate_norm)

        has_uploaded_proof = bool(payment_info.get("proof_url"))
        proof_upload_time = payment_info.get("timestamp", "")
        parking_lot = payment_info.get("parking_lot", "")
        fnb_lot = payment_info.get("fnb_lot", "")
        ft_lot = payment_info.get("ft_lot", "")
        arts_lot = payment_info.get("arts_lot", "")

        # ====================================================
        # SENARAI PRODUK (auto-detect column)
        # ====================================================
        products_col_name = find_products_column(df)
        products_text = ""
        if products_col_name:
            products_text = clean_text_field(row.get(products_col_name, ""))

        # ====================================================
        # ADMIN NOTE + VENDOR REMARK (compact helper)
        # ====================================================
        def _render_notes(row, COL_REMARK):
            admin_note = ""
            if pd.notna(row.get("Notes")) and str(row.get("Notes")).strip():
                admin_note = str(row.get("Notes")).strip()

            vendor_remark = ""
            if pd.notna(row.get(COL_REMARK)) and str(row.get(COL_REMARK)).strip():
                vendor_remark = str(row.get(COL_REMARK)).strip()

            if admin_note:
                st.info(f"📝 **Nota Admin:** {admin_note}")
            if vendor_remark:
                st.caption(f"📋 **Remark anda:** {vendor_remark}")

        # ====================================================
        # STATUS BLOCK
        # ====================================================

        # ---- PENDING ----
        if status == "Pending":
            with st.container(border=True):
                st.warning("⏳ **Permohonan Sedang Disemak**")
                st.caption("Sila semak semula dalam **1-2 hari**.")
            st.caption("📌 Belum perlu bayar. Bayaran hanya selepas diluluskan.")

        # ---- REJECTED ----
        elif status == "Rejected":
            reject_reason = str(row.get("Notes", "") or "").strip()
            if reject_reason.lower() in ("nan", "none", "null"):
                reject_reason = ""

            # ---- POPUP REJECT (sekali sahaja per sesi) ----
            reject_dialog_key = f"reject_shown_{plate_norm}"
            if not st.session_state.get(reject_dialog_key, False):
                st.session_state[reject_dialog_key] = True
                show_reject_dialog(row, plate_norm, reject_reason)

            # ---- Kad status (di belakang popup) ----
            st.markdown(
                "<div style='background:#fef2f2; border:2px solid #fecaca; "
                "border-radius:10px; padding:1rem 1.25rem; margin:0.5rem 0;'>"
                "<div style='font-size:1rem; font-weight:700; color:#991b1b; "
                "margin-bottom:0.25rem;'>✕ Permohonan Tidak Berjaya</div>"
                "<div style='font-size:0.85rem; color:#7f1d1d;'>"
                "Maaf, permohonan anda tidak dapat diterima untuk event ini.</div>"
                "</div>",
                unsafe_allow_html=True,
            )

            # ---- Ayat admin (kalau ada) ----
            if reject_reason:
                st.markdown(
                    "<div style='font-size:0.72rem; color:#78716c; letter-spacing:0.04em; "
                    "font-weight:600; text-transform:uppercase; margin-top:0.75rem; "
                    "margin-bottom:0.35rem;'>📋 Mesej dari Admin</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='background:#fff7ed; border-left:4px solid #dc2626; "
                    f"border-radius:8px; padding:0.85rem 1rem; font-size:0.88rem; "
                    f"color:#44403c; white-space:pre-wrap; line-height:1.6;'>"
                    f"{reject_reason}</div>",
                    unsafe_allow_html=True,
                )

        # ---- CANCELLED ----
        elif status == "Cancelled":
            cancel_reason = str(row.get("Notes", "") or "").strip()
            if cancel_reason.lower() in ("nan", "none", "null"):
                cancel_reason = ""

            with st.container(border=True):
                st.error("🚫 **Slot Dibatalkan**")
                if not cancel_reason:
                    st.caption("Hubungi admin untuk maklumat lanjut.")

            # ---- Ayat dari admin (kalau ada) ----
            if cancel_reason:
                st.markdown(
                    "<div style='font-size:0.72rem; color:#78716c; letter-spacing:0.04em; "
                    "font-weight:600; text-transform:uppercase; margin-top:0.75rem; "
                    "margin-bottom:0.35rem;'>📋 Mesej dari Admin</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='background:#fef2f2; border-left:4px solid #dc2626; "
                    f"border-radius:8px; padding:0.85rem 1rem; font-size:0.88rem; "
                    f"color:#44403c; white-space:pre-wrap; line-height:1.6;'>"
                    f"{cancel_reason}</div>",
                    unsafe_allow_html=True,
                )

        # ---- APPROVED ----
        elif status == "Approved":

            # ========== CASE 1: BELUM PAID + DAH UPLOAD ==========
            if not paid and has_uploaded_proof:
                with st.container(border=True):
                    st.info("📤 **Bukti Bayaran Telah Dihantar**")
                    if proof_upload_time:
                        st.caption(f"Diterima pada **{proof_upload_time}**. Admin akan semak.")
                    else:
                        st.caption("Admin akan semak dan sahkan tidak lama lagi.")

                _render_notes(row, COL_REMARK)

                if products_text:
                    render_products_box(products_text)

            # ========== CASE 2: BELUM PAID + BELUM UPLOAD ==========
            elif not paid and not has_uploaded_proof:

                vendor_type = str(row.get(COL_TYPE, "")).strip()
                cat_price = get_category_price(vendor_type)
                deposit_amount = get_deposit(vendor_type)
                addon_str_raw = str(row.get(COL_ADDON, "") or "")
                addon_price = get_addon_price(addon_str_raw)
                total_price = cat_price + deposit_amount + addon_price

                # ---- Ambil nota admin untuk popup ----
                admin_note_for_popup = ""
                if pd.notna(row.get("Notes")) and str(row.get("Notes")).strip():
                    admin_note_for_popup = str(row.get("Notes")).strip()

                # ---- POPUP BAYARAN (sekali sahaja per sesi) ----
                payment_dialog_key = f"payment_shown_{plate_norm}"
                if not st.session_state.get(payment_dialog_key, False) and total_price > 0:
                    st.session_state[payment_dialog_key] = True
                    show_payment_dialog(
                        row, plate_norm, vendor_type,
                        cat_price, deposit_amount, addon_price, total_price,
                        admin_note=admin_note_for_popup,
                    )

                # ---- KAD HARGA (compact) ----
                if total_price > 0:
                    breakdown = f"📦 {vendor_type}: {format_rm(cat_price)}"
                    if deposit_amount > 0:
                        breakdown += f" · 🔒 Deposit: {format_rm(deposit_amount)}"
                    if addon_price > 0:
                        breakdown += f" · ➕ Add On: {format_rm(addon_price)}"

                    st.markdown(
                        f"<div style='background:#fff7ed; border:1px solid #fed7aa; "
                        f"border-radius:10px; padding:0.7rem 1rem; margin:0.5rem 0;'>"
                        f"<div style='font-size:0.72rem; color:#9a3412; letter-spacing:0.04em; "
                        f"font-weight:600; text-transform:uppercase;'>💰 Jumlah Perlu Dibayar</div>"
                        f"<div style='font-size:1.7rem; font-weight:800; color:#7c2d12; "
                        f"line-height:1.1; margin:0.15rem 0;'>{format_rm(total_price)}</div>"
                        f"<div style='font-size:0.78rem; color:#9a3412;'>{breakdown}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                # ---- MAKLUMAT BANK (2 columns, compact) ----
                with st.container(border=True):
                    st.caption("💳 MAKLUMAT PEMBAYARAN")
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        st.markdown("🏦 **Bank:** MAYBANK")
                        st.markdown("👤 **Nama:** PRINTHERO MERCHANDISE SDN. BHD.")
                    with bc2:
                        st.markdown("🔢 **No. Akaun:** `557054621057`")
                        st.markdown("📝 **Remark:** `PFMCBS` + 4 digit phone")

                st.caption(
                    "⚠️ Sila upload bukti bayaran dalam **format PDF sahaja**. "
                    "Kegagalan bayaran boleh sebabkan slot dibatalkan."
                )

                _render_notes(row, COL_REMARK)

                if products_text:
                    render_products_box(products_text)
                    st.caption(
                        "⚠️ Kalau ada perubahan senarai produk, sila maklumkan admin "
                        "semasa upload bukti bayaran."
                    )

                # ---- BUTANG UPLOAD (SATU SAHAJA) ----
                st.link_button(
                    "📤 Upload Bukti Bayaran dan Pemilihan Slot",
                    st.secrets["event"]["payment_form_url"],
                    width="stretch",
                    type="primary",
                )

            # ========== CASE 3: DAH PAID ==========
            else:
                # ---- Bina slot_items (untuk popup & display) ----
                slot_items = []
                if parking_lot:
                    slot_items.append(("🅿️ Parking Lot", parking_lot))
                if fnb_lot:
                    slot_items.append(("🍴 F&B Lot", fnb_lot))
                if ft_lot and ft_lot != fnb_lot:
                    slot_items.append(("🚚 Food Truck Lot", ft_lot))
                if arts_lot:
                    slot_items.append(("🎨 Arts/Crafts Lot", arts_lot))

                # ---- POPUP (sekali sahaja per sesi) ----
                dialog_key = f"success_shown_{plate_norm}"
                if not st.session_state.get(dialog_key, False):
                    st.session_state[dialog_key] = True
                    show_success_dialog(row, plate_norm, status, paid, slot_items)

                # ---- Content di belakang popup ----
                with st.container(border=True):
                    st.success("✓ **Permohonan Disahkan**")
                    st.caption("Slot anda telah dikonfirmasi.")

                _render_notes(row, COL_REMARK)

                # ---- SLOT INFO (grid 2 columns) ----
                if slot_items:
                    with st.container(border=True):
                        st.caption("📍 MAKLUMAT SLOT ANDA")
                        cols = st.columns(2)
                        for i, (label, val) in enumerate(slot_items):
                            with cols[i % 2]:
                                st.markdown(
                                    f"<div style='background:#f7f3ee; border-radius:8px; "
                                    f"padding:0.5rem 0.75rem; margin-bottom:0.4rem; font-size:0.85rem;'>"
                                    f"<b>{label}:</b> {val}</div>",
                                    unsafe_allow_html=True,
                                )

                # ---- SENARAI PRODUK (rujukan vendor) ----
                if products_text:
                    render_products_box(products_text)
                else:
                    st.caption("🛍️ _(Tiada senarai produk didaftarkan)_")

                # ---- EVENT INFO (compact) ----
                st.markdown(
                    "<div style='background:#f0fdf4; border:1px solid #bbf7d0; "
                    "border-radius:10px; padding:0.7rem 1rem; margin:0.5rem 0;'>"
                    "<div style='font-size:1rem; font-weight:700; color:#14532d;'>"
                    "📅 Jumpa anda pada 6-8 November 2026!</div>"
                    "<div style='font-size:0.8rem; color:#166534; margin-top:0.25rem;'>"
                    "Join WhatsApp Group untuk update terkini (susun atur, parking, dll)."
                    "</div></div>",
                    unsafe_allow_html=True,
                )

                # ---- BUTANG WHATSAPP (SATU SAHAJA) ----
                st.link_button(
                    "💬 Join WhatsApp Group Vendor",
                    st.secrets["event"]["whatsapp_group"],
                    width="stretch",
                    type="primary",
                )

                st.balloons()

        # ---- UNKNOWN ----
        else:
            st.warning(f"⚠️ Status tidak dikenali: **{status}**. Hubungi admin.")
