import streamlit as st
import pandas as pd
import re
from streamlit_gsheets import GSheetsConnection
from style import apply_style
from components import page_header, load_sheet_safe

apply_style()
page_header()

# ============================================================
# KONFIGURASI
# ============================================================
COL_NAME = "Nama/Name"
COL_PHONE = "Nombor Telefon/Phone Number"
COL_TYPE = "Kategori Produk/Product Category"
COL_CAT = "F&B CATEGORY"
COL_PLATE = "Plate Number"
COL_ADDON = "ADD ON"

PROOF_COL = "Upload Bukti Bayaran"

VALID_STATUSES = ["Pending", "Approved", "Rejected", "Cancelled"]


# ============================================================
# HELPER — Normalize Status
# ============================================================
def normalize_status(raw):
    if raw is None or pd.isna(raw) or str(raw).strip() == "":
        return "Pending"
    s = str(raw).strip().title()
    aliases = {
        "Menunggu": "Pending",
        "Waiting": "Pending",
        "New": "Pending",
        "Approve": "Approved",
        "Reject": "Rejected",
        "Cancel": "Cancelled",
        "Canceled": "Cancelled",
    }
    s = aliases.get(s, s)
    return s if s in VALID_STATUSES else "Pending"


# ============================================================
# HELPER — KIRA HARGA
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
    """Deposit refundable — F&B + Arts & Crafts / Toys."""
    try:
        if vendor_type == "F&B":
            return float(st.secrets["event"]["deposit_fb"])
        elif vendor_type == "Arts & Crafts / Toys":
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


# ============================================================
# HELPER — AMBIL INFO PAYMENT (lot, jenis, dll)
# ============================================================
def get_vendor_payment_info(payments_df, plate_norm):
    """Ambil info terkini dari Sheet Payments."""
    if payments_df is None or payments_df.empty:
        return {}

    if "Plate Number" not in payments_df.columns:
        return {}

    matched = payments_df[
        payments_df["Plate Number"].astype(str).str.upper().str.replace(" ", "")
        == plate_norm
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
        return "" if s.lower() in ("nan", "none", "nat", "null") else s

    return {
        "proof_url": _clean(latest.get(PROOF_COL, "")),
        "folder_url": _clean(latest.get("FolderUrl", "")),
        "timestamp": _clean(latest.get("Timestamp", "")),
        "pilih_jenis": _clean(latest.get("Pilih Jenis", "")),
        "parking_lot": _clean(latest.get("Pilih parking lot", "")),
        "fnb_lot": _clean(latest.get("Pilih F&B Lot", "")),
    }


# ============================================================
# TITLE
# ============================================================
st.title("🔍 Semak Kelayakan")
st.caption("Masukkan No. Pendaftaran Kenderaan/Plate Number anda untuk semak status permohonan.")

# ============================================================
# LOAD DATA
# ============================================================
@st.cache_data(ttl=60, show_spinner="Memuatkan data...")
def load_vendors():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        return conn.read(worksheet="Vendors", ttl=60), None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=60, show_spinner=False)
def load_payments():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        return conn.read(worksheet="Payments", ttl=60), None
    except Exception as e:
        return None, str(e)


df, err = load_vendors()

if df is None:
    error_msg = (err or "").lower()
    if "429" in error_msg or "quota" in error_msg:
        st.warning("⏳ **Sistem sedang sibuk.** Terlalu banyak permintaan. Sila tunggu **1-2 minit** dan cuba lagi.")
        if st.button("🔄 Cuba Lagi"):
            st.cache_data.clear()
            st.rerun()
    else:
        st.error("⚠️ Sistem tidak dapat memuatkan data. Sila cuba lagi.")
        with st.expander("Butiran teknikal"):
            st.code(err)
    st.stop()

df["Status"] = df["Status"].apply(normalize_status)

# ============================================================
# SEARCH FORM
# ============================================================
with st.form("search"):
    query = st.text_input(
        "No. Pendaftaran Kenderaan/Plate Number",
        placeholder="Contoh: NNA1806"
    ).strip().upper()

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        submitted = st.form_submit_button("Semak Status", type="primary", use_container_width=True)

# ============================================================
# RESULT
# ============================================================
if submitted and query:
    result = df[
        df[COL_PLATE].astype(str).str.upper().str.replace(" ", "")
        == query.replace(" ", "")
    ]

    if result.empty:
        st.divider()
        with st.container(border=True):
            st.error(f"❌ **Tiada permohonan dijumpai**")
            st.markdown(f"**{query}** tidak ada dalam sistem. Sila daftar terlebih dahulu atau hubungi admin.")
            st.link_button(
                "📝 Daftar Sekarang",
                "https://forms.gle/bheUdQTvKRTCns4eA",
                use_container_width=True,
                type="primary",
            )

    else:
        row = result.iloc[0]
        status = str(row["Status"]).strip()
        paid = bool(row["Paid"]) if pd.notna(row["Paid"]) else False
        plate_norm = str(row[COL_PLATE]).upper().replace(" ", "")

        st.divider()

        # ====================================================
        # INFO CARD
        # ====================================================
        with st.container(border=True):
            st.caption("MAKLUMAT PERMOHONAN")
            st.subheader(str(row[COL_PLATE]))
            st.markdown(f"**Nama:** {row[COL_NAME]}")
            st.markdown(f"**Kategori:** {row[COL_TYPE]}")
            if pd.notna(row.get(COL_CAT)) and str(row[COL_CAT]).strip():
                st.markdown(f"**F&B Category:** {row[COL_CAT]}")

        # ====================================================
        # AMBIL INFO PAYMENT (dari Sheet Payments)
        # ====================================================
        payments_df, _ = load_payments()
        payment_info = get_vendor_payment_info(payments_df, plate_norm)

        has_uploaded_proof = bool(payment_info.get("proof_url"))
        proof_upload_time = payment_info.get("timestamp", "")
        parking_lot = payment_info.get("parking_lot", "")
        fnb_lot = payment_info.get("fnb_lot", "")

        # ====================================================
        # STATUS KAD
        # ====================================================

        # ---------- PENDING ----------
        if status == "Pending":
            with st.container(border=True):
                st.warning("⏳ **Permohonan Sedang Disemak**")
                st.markdown("Permohonan anda telah diterima dan sedang dalam proses semakan admin. Sila semak semula dalam **1-2 hari**.")

            st.info("📌 **Belum perlu buat bayaran.** Bayaran hanya diperlukan selepas permohonan anda diluluskan.")

        # ---------- REJECTED ----------
        elif status == "Rejected":
            with st.container(border=True):
                st.error("✕ **Permohonan Tidak Berjaya**")
                st.markdown("Maaf, permohonan anda tidak dipilih untuk event ini. Hubungi admin untuk maklumat lanjut.")

            reject_reason = ""
            if pd.notna(row.get("Notes")) and str(row.get("Notes")).strip():
                reject_reason = str(row.get("Notes")).strip()

            if reject_reason:
                with st.container(border=True):
                    st.caption("📋 SEBAB PENOLAKAN")
                    st.markdown(reject_reason)

        # ---------- CANCELLED ----------
        elif status == "Cancelled":
            with st.container(border=True):
                st.error("🚫 **Slot Dibatalkan**")
                st.markdown("Slot anda telah dibatalkan kerana bayaran tidak diterima sebelum tarikh akhir. Hubungi admin jika ada masalah.")

        # ---------- APPROVED ----------
        elif status == "Approved":

            # ==========================================
            # CASE 1: Approved + BELUM Paid + DAH UPLOAD BUKTI
            # ==========================================
            if not paid and has_uploaded_proof:
                with st.container(border=True):
                    st.info("📤 **Bukti Bayaran Telah Dihantar**")
                    if proof_upload_time:
                        st.markdown(f"Terima kasih! Bukti bayaran anda telah diterima pada **{proof_upload_time}**. Admin akan semak dan sahkan slot anda tidak lama lagi.")
                    else:
                        st.markdown("Terima kasih! Bukti bayaran anda telah diterima. Admin akan semak dan sahkan slot anda tidak lama lagi.")

                st.info("📌 **Seterusnya:** Sila tunggu pengesahan admin.")

            # ==========================================
            # CASE 2: Approved + BELUM Paid + BELUM UPLOAD
            # ==========================================
            elif not paid and not has_uploaded_proof:
                # === KAD HARGA ===
                vendor_type = str(row.get(COL_TYPE, "")).strip()
                cat_price = get_category_price(vendor_type)
                deposit_amount = get_deposit(vendor_type)
                addon_str_raw = str(row.get(COL_ADDON, "") or "")
                addon_price = get_addon_price(addon_str_raw)
                total_price = cat_price + deposit_amount + addon_price

                if total_price > 0:
                    with st.container(border=True):
                        st.caption("💰 JUMLAH PERLU DIBAYAR")
                        st.markdown(f"# {format_rm(total_price)}")
                        st.divider()
                        st.markdown(f"📦 **{vendor_type}**: {format_rm(cat_price)}")
                        if deposit_amount > 0:
                            st.markdown(f"🔒 **Deposit (Refundable)**: {format_rm(deposit_amount)}")
                        if addon_price > 0:
                            st.markdown(f"➕ **Add On**: {format_rm(addon_price)}")

                # === KAD STATUS APPROVED ===
                with st.container(border=True):
                    st.success("✓ **Permohonan Diluluskan**")
                    st.markdown("Tahniah! Permohonan anda telah diluluskan. Sila buat bayaran dan upload bukti untuk konfirmasi slot anda.")

                # === KAD MAKLUMAT PEMBAYARAN ===
                with st.container(border=True):
                    st.caption("💳 MAKLUMAT PEMBAYARAN")
                    st.markdown("🏦 <b>Bank:</b> MAYBANK", unsafe_allow_html=True)
                    st.markdown("👤 <b>Nama Akaun:</b> PRINTHERO MERCHANDISE SDN. BHD.", unsafe_allow_html=True)
                    st.markdown("🔢 <b>No. Akaun:</b> 557054621057", unsafe_allow_html=True)
                    st.markdown("📝 <b>Remark:</b> PFMCBS (4 digit terakhir No. Telefon)", unsafe_allow_html=True)
                    st.markdown("📋 <b>Contoh:</b> PFMCBS1234", unsafe_allow_html=True)

                # === NOTA PENTING ===
                st.warning("⚠️ **Penting:** Kalau bayaran tidak diterima **2 hari sebelum event**, slot anda akan dibatalkan automatik.")

                # === BUTANG LINK GOOGLE FORM ===
                st.link_button(
                    "📤  Upload Bukti Bayaran",
                    st.secrets["event"]["payment_form_url"],
                    use_container_width=True,
                    type="primary",
                )

            # ==========================================
            # CASE 3: Approved + DAH Paid
            # ==========================================
            else:
                with st.container(border=True):
                    st.success("✓ **Permohonan Disahkan**")
                    st.markdown("Tahniah! Anda telah berjaya mendaftar dan membuat pembayaran. Berikut adalah maklumat slot anda:")

                # === KAD DETAIL SLOT (PILIHAN LOT) ===
                if parking_lot or fnb_lot:
                    with st.container(border=True):
                        st.caption("📍 MAKLUMAT SLOT ANDA")
                        if parking_lot:
                            st.markdown(f"<b>Parking Lot:</b> {parking_lot}", unsafe_allow_html=True)
                        if fnb_lot:
                            st.markdown(f"<b>F&B Lot:</b> {fnb_lot}", unsafe_allow_html=True)

                st.markdown("**Sertai WhatsApp Group Vendor**")
                st.caption("Dapatkan maklumat terkini tentang event, susun atur booth, dan update penting.")

                st.link_button(
                    "💬  Join WhatsApp Group",
                    st.secrets["event"]["whatsapp_group"],
                    use_container_width=True,
                    type="primary",
                )

                st.balloons()

        # ---------- UNKNOWN ----------
        else:
            st.warning(f"⚠️ Status permohonan tidak dikenali: **{status}**. Sila hubungi admin untuk maklumat lanjut.")
