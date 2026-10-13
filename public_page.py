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


def render_stepper(status, paid, has_uploaded_proof):
    """Compact visual progress stepper — no buttons."""
    steps = [
        ("Daftar", True),
        ("Diluluskan", status in ("Approved", "Rejected", "Cancelled")),
        ("Upload", has_uploaded_proof),
        ("Disahkan", paid),
    ]
    cols = st.columns(4)
    for i, (label, done) in enumerate(steps):
        with cols[i]:
            icon = "✅" if done else "⚪"
            color = "#16a34a" if done else "#a8a29e"
            st.markdown(
                f"<div style='text-align:center; padding:0.1rem 0;'>"
                f"<span style='font-size:1.1rem;'>{icon}</span> "
                f"<span style='font-size:0.72rem; color:{color}; font-weight:600;'>{label}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )


def render_action_banner(status, paid, has_uploaded_proof):
    """Compact banner — no buttons (dah ada di bawah)."""
    if status == "Approved" and not paid and not has_uploaded_proof:
        st.markdown(
            "<div style='background:#fef2f2; border-left:4px solid #dc2626; "
            "padding:0.6rem 0.9rem; border-radius:8px; margin:0.5rem 0; "
            "font-size:0.82rem; color:#7f1d1d;'>"
            "<b>⚠️ TINDAKAN DIPERLUKAN</b> — Scroll ke bawah untuk "
            "jumlah bayaran & butang upload. "
            "⏰ Sebelum <b>Isnin (12/10/2026) 11:00 pagi</b>."
            "</div>",
            unsafe_allow_html=True,
        )
    elif status == "Approved" and not paid and has_uploaded_proof:
        st.markdown(
            "<div style='background:#eff6ff; border-left:4px solid #2563eb; "
            "padding:0.6rem 0.9rem; border-radius:8px; margin:0.5rem 0; "
            "font-size:0.82rem; color:#1e3a8a;'>"
            "<b>📤 BUKTI DITERIMA</b> — Admin sedang semak. Scroll ke bawah untuk info lanjut."
            "</div>",
            unsafe_allow_html=True,
        )
    elif status == "Approved" and paid:
        st.markdown(
            "<div style='background:#f0fdf4; border-left:4px solid #16a34a; "
            "padding:0.6rem 0.9rem; border-radius:8px; margin:0.5rem 0; "
            "font-size:0.82rem; color:#14532d;'>"
            "<b>✅ SLOT DISAHKAN</b> — Scroll ke bawah: maklumat slot & "
            "butang Join WhatsApp Group."
            "</div>",
            unsafe_allow_html=True,
        )


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
        # STEPPER + BANNER (compact, no buttons)
        # ====================================================
        render_stepper(status, paid, has_uploaded_proof)
        render_action_banner(status, paid, has_uploaded_proof)

        st.markdown("<div style='height:0.25rem;'></div>", unsafe_allow_html=True)

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
            with st.container(border=True):
                st.error("✕ **Permohonan Tidak Berjaya**")
                st.caption("Hubungi admin untuk maklumat lanjut.")

            reject_reason = str(row.get("Notes", "") or "").strip()
            if reject_reason:
                st.error(f"📋 **Sebab:** {reject_reason}")

        # ---- CANCELLED ----
        elif status == "Cancelled":
            with st.container(border=True):
                st.error("🚫 **Slot Dibatalkan**")
                st.caption("Bayaran tidak diterima sebelum tarikh akhir.")

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

            # ========== CASE 2: BELUM PAID + BELUM UPLOAD ==========
            elif not paid and not has_uploaded_proof:

                vendor_type = str(row.get(COL_TYPE, "")).strip()
                cat_price = get_category_price(vendor_type)
                deposit_amount = get_deposit(vendor_type)
                addon_str_raw = str(row.get(COL_ADDON, "") or "")
                addon_price = get_addon_price(addon_str_raw)
                total_price = cat_price + deposit_amount + addon_price

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

                # ---- DEADLINE (compact) ----
                st.error(
                    "📢 **Deadline:** Full payment sebelum **Isnin (12/10/2026) 11:00 pagi**. "
                    "Selepas itu slot akan **dibatalkan**."
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

                # ---- BUTANG UPLOAD (SATU SAHAJA) ----
                st.link_button(
                    "📤 Upload Bukti Bayaran dan Pemilihan Slot",
                    st.secrets["event"]["payment_form_url"],
                    width="stretch",
                    type="primary",
                )

            # ========== CASE 3: DAH PAID ==========
            else:
                with st.container(border=True):
                    st.success("✓ **Permohonan Disahkan**")
                    st.caption("Slot anda telah dikonfirmasi.")

                _render_notes(row, COL_REMARK)

                # ---- SLOT INFO (grid 2 columns) ----
                slot_items = []
                if parking_lot:
                    slot_items.append(("🅿️ Parking Lot", parking_lot))
                if fnb_lot:
                    slot_items.append(("🍴 F&B Lot", fnb_lot))
                if ft_lot and ft_lot != fnb_lot:
                    slot_items.append(("🚚 Food Truck Lot", ft_lot))
                if arts_lot:
                    slot_items.append(("🎨 Arts/Crafts Lot", arts_lot))

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
