import streamlit as st
import pandas as pd
import re
from urllib.parse import quote
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from style import apply_style
from components import page_header, load_sheet_safe, upload_payment_proof

st.set_page_config(page_title="Upload Bukti Bayaran", layout="wide")
apply_style()
page_header()

st.title("📤 Upload Bukti Bayaran")
st.caption("Bukti bayaran akan disimpan automatik ke Google Drive mengikut kategori anda.")

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

FB_CATEGORIES = [
    "Local Food", "Dessert", "Coffee/Air", "Grill and BBQ",
    "Deep-Fry", "Italian/Western Food", "Japanese Food", "Chinese Food",
]

ADMIN_WA_NUMBER = "601157727459"


# ============================================================
# HELPER — WhatsApp
# ============================================================
def whatsapp_button(label, message):
    wa_url = f"https://wa.me/{ADMIN_WA_NUMBER}?text={quote(message)}"
    st.markdown(f"""
    <a href="{wa_url}" target="_blank" style="
        display: block;
        background-color: #25D366;
        color: #ffffff;
        text-align: center;
        padding: 0.85rem 1.5rem;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        font-size: 1rem;
        margin-top: 0.75rem;
    ">{label}</a>
    """, unsafe_allow_html=True)


# ============================================================
# HELPER — NOTIS PEMBAYARAN
# ============================================================
def payment_notice():
    st.markdown("""
    <div style="
        background-color: #fef2f2;
        border: 2px solid #fca5a5;
        border-radius: 12px;
        padding: 1.5rem 1.75rem;
        margin-bottom: 1.5rem;
    ">
        <div style="
            font-size: 1rem;
            font-weight: 700;
            color: #991b1b;
            margin-bottom: 0.85rem;
            line-height: 1.4;
        ">❗️ NOTIS PEMBAYARAN TAPAK VENDOR PFM MEGA CARBOOT SALE ❗️</div>

        <div style="
            color: #44403c;
            font-size: 0.9rem;
            line-height: 1.6;
            margin-bottom: 1rem;
        ">
            Sila buat bayaran tapak mengikut kategori yang dipilih.
            Untuk Carboot tak disediakan lampu dan elektrik.
        </div>

        <div style="
            background-color: #ffffff;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
        ">
            <div style="
                font-size: 0.8rem;
                color: #78716c;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                font-weight: 600;
                margin-bottom: 0.6rem;
            ">Maklumat Pembayaran</div>

            <div style="
                display: grid;
                gap: 0.4rem;
                font-size: 0.9rem;
                color: #292524;
            ">
                <div>
                    <span style="color: #78716c; display: inline-block; min-width: 110px;">🏦 Bank</span>
                    <b>MAYBANK</b>
                </div>
                <div>
                    <span style="color: #78716c; display: inline-block; min-width: 110px;">👤 Nama Akaun</span>
                    <b>PRINTHERO MERCHANDISE SDN. BHD.</b>
                </div>
                <div>
                    <span style="color: #78716c; display: inline-block; min-width: 110px;">🔢 No. Akaun</span>
                    <b style="font-size: 1rem; letter-spacing: 1px;">557054621057</b>
                </div>
                <div>
                    <span style="color: #78716c; display: inline-block; min-width: 110px;">📝 Remark</span>
                    <b>PFMCBS (4 digit terakhir No. Telefon)</b>
                </div>
                <div>
                    <span style="color: #78716c; display: inline-block; min-width: 110px;">📋 Contoh</span>
                    <b>PFMCBS1234</b>
                </div>
            </div>
        </div>

        <div style="
            color: #44403c;
            font-size: 0.9rem;
            line-height: 1.6;
        ">
            Sila upload resit pembayaran di bawah ini dan pilih jenis lot untuk pengesahan.<br>
            <b>Terima Kasih</b>
        </div>
    </div>
    """, unsafe_allow_html=True)


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
    try:
        if vendor_type == "F&B":
            return float(st.secrets["event"]["deposit_fb"])
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


def get_addon_items(addon_str):
    if addon_str is None or pd.isna(addon_str):
        return []
    try:
        items = re.findall(
            r"([^,()]+?)\s*\(Fee:\s*RM\s*([0-9.]+)\)",
            str(addon_str)
        )
        return [(name.strip(), float(price)) for name, price in items]
    except Exception:
        return []


def format_rm(amount):
    try:
        return f"RM {float(amount):,.2f}"
    except (ValueError, TypeError):
        return "RM 0.00"


# ============================================================
# LOAD VENDORS
# ============================================================
conn = st.connection("gsheets", type=GSheetsConnection)
df = load_sheet_safe(conn, "Vendors", ttl=0)
if df is None:
    st.stop()

if "Paid" not in df.columns:
    df["Paid"] = False
df["Paid"] = df["Paid"].fillna(False).astype(bool)


# ============================================================
# FORM
# ============================================================
with st.form("payment_upload", clear_on_submit=False):
    plate_input = st.text_input(
        "No. Pendaftaran Kenderaan / Plate Number",
        placeholder="Contoh: NNA1806",
        help="Masukkan no. plate yang sama seperti semasa pendaftaran.",
    ).strip().upper()

    uploaded = st.file_uploader(
        "Pilih gambar bukti bayaran",
        type=["jpg", "jpeg", "png", "pdf"],
        help="Format dibenarkan: JPG, PNG, PDF. Saiz maksimum 10MB.",
    )

    st.markdown("---")
    submitted = st.form_submit_button(
        "Hantar Bukti Bayaran", type="primary", use_container_width=True
    )


# ============================================================
# PROSES
# ============================================================
if submitted:
    if not plate_input:
        st.error("❌ Sila masukkan No. Plate.")
        st.stop()

    if not uploaded:
        st.error("❌ Sila pilih fail bukti bayaran.")
        st.stop()

    MAX_SIZE_MB = 10
    file_size_mb = uploaded.size / (1024 * 1024)
    if file_size_mb > MAX_SIZE_MB:
        st.error(f"❌ Saiz fail terlalu besar ({file_size_mb:.1f} MB). Maksimum {MAX_SIZE_MB} MB.")
        st.stop()

    normalized_input = plate_input.replace(" ", "").upper()
    matched = df[
        df[COL_PLATE].astype(str).str.upper().str.replace(" ", "")
        == normalized_input
    ]

    if matched.empty:
        st.error(f"❌ No. Plate **{plate_input}** tidak dijumpai dalam sistem.")
        st.info("Sila pastikan No. Plate betul, atau daftar terlebih dahulu.")
        whatsapp_button(
            "💬 Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — Saya nak tanya pasal pendaftaran (Plate: {plate_input})"
        )
        st.stop()

    vendor = matched.iloc[0]
    vendor_name = str(vendor.get(COL_NAME, ""))
    status = str(vendor.get("Status", "")).strip().title()
    vendor_type = str(vendor.get(COL_TYPE, "Car Boot Sales")).strip()
    fb_category = str(vendor.get(COL_CAT, "") or "").strip()

    # ---- Semak status ----
    if status == "Pending":
        st.warning(
            f"⚠️ Permohonan anda masih **Menunggu Semakan**. "
            "Bukti bayaran hanya boleh dihantar selepas permohonan diluluskan."
        )
        whatsapp_button(
            "💬 Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — Permohonan saya masih pending (Plate: {plate_input})"
        )
        st.stop()

    if status == "Rejected":
        st.error(
            "❌ Permohonan anda **Tidak Berjaya**. "
            "Sila hubungi admin untuk maklumat lanjut."
        )
        whatsapp_button(
            "💬 Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — Nak tanya pasal permohonan yang ditolak (Plate: {plate_input})"
        )
        st.stop()

    if status == "Cancelled":
        st.error(
            "🚫 Slot anda telah **Dibatalkan** kerana bayaran tidak diterima "
            "sebelum tarikh akhir. Hubungi admin jika ini satu kesilapan."
        )
        whatsapp_button(
            "💬 Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — Slot saya telah dibatalkan (Plate: {plate_input})"
        )
        st.stop()

    if status != "Approved":
        st.error(f"⚠️ Status tidak dikenali: **{status}**. Sila hubungi admin.")
        whatsapp_button(
            "💬 Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — Status tidak dikenali (Plate: {plate_input})"
        )
        st.stop()

    st.success(f"✅ Vendor dijumpai: **{vendor_name}** ({vendor_type})")

    # === NOTIS PEMBAYARAN ===
    payment_notice()

    # ============================================================
    # KIRA TOTAL HARGA
    # ============================================================
    cat_price = get_category_price(vendor_type)
    deposit_amount = get_deposit(vendor_type)
    addon_str_raw = str(vendor.get(COL_ADDON, "") or "")
    addon_price = get_addon_price(addon_str_raw)
    addon_items = get_addon_items(addon_str_raw)
    total_price = cat_price + deposit_amount + addon_price

    if total_price > 0:
        breakdown_html = f'<div>📦 {vendor_type}: <b>{format_rm(cat_price)}</b></div>'
        if deposit_amount > 0:
            breakdown_html += f'<div>🔒 Deposit (Refundable): <b>{format_rm(deposit_amount)}</b></div>'
        if addon_price > 0:
            breakdown_html += f'<div>➕ Add On: <b>{format_rm(addon_price)}</b></div>'

        st.markdown(f"""
        <div style="
            background-color: #fef9ec;
            border: 2px solid #f0e6d6;
            border-radius: 12px;
            padding: 1.5rem 1.75rem;
            margin: 1rem 0 0.75rem 0;
        ">
            <div style="
                font-size: 0.8rem; color: #78716c;
                text-transform: uppercase; letter-spacing: 0.5px;
                margin-bottom: 0.5rem;
            ">💰 Jumlah Perlu Dibayar</div>
            <div style="
                font-size: 2.25rem; font-weight: 700;
                color: #78350f; margin-bottom: 0.75rem;
                line-height: 1;
            ">{format_rm(total_price)}</div>
            <div style="
                font-size: 0.85rem; color: #57534e;
                border-top: 1px dashed #e8dcc7;
                padding-top: 0.75rem;
                display: grid; gap: 0.35rem;
            ">
                {breakdown_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if addon_items:
            with st.expander("📋 Detail Add On"):
                for name, price in addon_items:
                    st.markdown(f"- {name}: **{format_rm(price)}**")

        if deposit_amount > 0:
            st.info(
                f"💡 **Sila buat bayaran sebanyak {format_rm(total_price)}** "
                f"({format_rm(cat_price + addon_price)} bayaran + "
                f"{format_rm(deposit_amount)} deposit). "
                f"**Deposit {format_rm(deposit_amount)} akan dipulangkan selepas event.**"
            )
        else:
            st.info(
                f"💡 **Sila buat bayaran sebanyak {format_rm(total_price)}** "
                "sebelum upload bukti bayaran di bawah."
            )

        whatsapp_button(
            "💬 Ada Pertanyaan? Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — Saya nak tanya pasal bayaran (Plate: {plate_input}, Kategori: {vendor_type})"
        )
    else:
        st.warning(
            "⚠️ Total harga tidak dapat dikira secara automatik. "
            "Sila hubungi admin untuk jumlah bayaran."
        )
        whatsapp_button(
            "💬 Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — Nak tanya pasal jumlah bayaran (Plate: {plate_input})"
        )

    # ---- Semak jika sudah upload sebelum ini ----
    existing_payments = load_sheet_safe(conn, "Payments", ttl=0)
    if existing_payments is None or existing_payments.empty:
        existing_payments = pd.DataFrame(
            columns=["Timestamp", "Plate Number", PROOF_COL, "FolderUrl"]
        )

    for col in ["Timestamp", "Plate Number", PROOF_COL, "FolderUrl"]:
        if col not in existing_payments.columns:
            existing_payments[col] = ""

    already_uploaded = existing_payments[
        existing_payments["Plate Number"].astype(str).str.upper().str.replace(" ", "")
        == normalized_input
    ]

    if not already_uploaded.empty:
        st.warning(
            f"⚠️ Anda sudah pernah upload bukti bayaran sebelum ini "
            f"({len(already_uploaded)} rekod). Upload baru akan **tambah** rekod lama."
        )

    # ---- Upload ke Google Drive ----
    with st.spinner("Menghantar ke Google Drive..."):
        try:
            parent_folder_id = st.secrets["event"]["payment_proof_folder_id"]
        except (KeyError, Exception):
            st.error("❌ Konfigurasi folder Drive tidak dijumpai. Sila hubungi admin.")
            st.stop()

        file_id, view_url, folder_url = upload_payment_proof(
            file_bytes=uploaded.getvalue(),
            plate=plate_input,
            vendor_type=vendor_type,
            fb_category=fb_category,
            parent_folder_id=parent_folder_id,
            mime_type=uploaded.type or "image/jpeg",
        )

    if not view_url:
        st.error("❌ Gagal upload ke Google Drive. Sila cuba lagi atau hubungi admin.")
        whatsapp_button(
            "💬 Lapor Masalah ke Admin",
            f"Hi! PFM Car Boot Sale — Upload bukti bayaran saya gagal (Plate: {plate_input})"
        )
        st.stop()

    # ---- Simpan rekod ke sheet Payments ----
    new_row = pd.DataFrame([{
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Plate Number": plate_input,
        PROOF_COL: view_url,
        "FolderUrl": folder_url,
    }])
    updated_payments = pd.concat([existing_payments, new_row], ignore_index=True)

    try:
        conn.update(worksheet="Payments", data=updated_payments)
        st.success("💾 Rekod pembayaran disimpan dalam sistem.")
    except Exception as e:
        st.warning(
            "⚠️ Fail berjaya diupload ke Drive, tapi rekod tidak dapat disimpan "
            f"dalam sistem. Sila maklumkan admin. (Error: {e})"
        )

    # ---- Paparkan hasil ----
    st.markdown("---")
    st.markdown("### ✅ Bukti Bayaran Berjaya Dihantar")
    st.markdown(f"**Vendor:** {vendor_name}  \n**No. Plate:** `{plate_input}`")
    if total_price > 0:
        st.markdown(f"**Jumlah:** {format_rm(total_price)}")
    st.markdown(f"**Fail:** [Lihat Bukti]({view_url})")
    if folder_url:
        st.markdown(f"**Folder vendor:** [Buka Folder]({folder_url})")

    st.info(
        "📌 **Seterusnya:** Admin akan semak bukti bayaran anda dan tanda "
        "'Sudah Bayar' dalam sistem. Sila sertai WhatsApp Group untuk update terkini."
    )

    whatsapp_button(
        "💬 Ada Pertanyaan? Tanya Admin via WhatsApp",
        f"Hi! PFM Car Boot Sale — Bukti bayaran saya telah dihantar (Plate: {plate_input})"
    )

    if uploaded.type and uploaded.type.startswith("image/"):
        with st.expander("Lihat gambar yang diupload"):
            st.image(uploaded, use_container_width=True)

    st.balloons()
