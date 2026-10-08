Ya, nampak masalahnya. 👍

Dalam secrets.toml awak, ini:

payment_proof_folder_id = "1rXKv_eulYO8HfV0ZnLGPQ9n_LQkyhBjy"

dah betul sebagai folder ID, tetapi sekadar letak ID dalam secrets.toml tak menyebabkan file automatik masuk ke folder tersebut.

Code Streamlit yang upload/create payment proof perlu ambil value itu dan gunakan sebagai parent folder.

Contohnya kalau guna Google Drive API:

folder_id = st.secrets["connections"]["gsheets"]["payment_proof_folder_id"]

file_metadata = {
    "name": file_name,
    "parents": [folder_id]
}

Kemudian masa upload:

file = drive_service.files().create(
    body=file_metadata,
    media_body=media,
    fields="id, name, webViewLink"
).execute()
Satu lagi perkara penting

Saya perasan struktur secrets awak ialah:

[connections.gsheets]
spreadsheet = "..."
client_x509_cert_url = "..."
payment_proof_folder_id = "..."

Jadi dalam Streamlit, aksesnya biasanya:

st.secrets["connections"]["gsheets"]["payment_proof_folder_id"]

Bukan:

st.secrets["payment_proof_folder_id"]

Kalau awak bagi saya bahagian code Streamlit yang handle upload payment proof, saya boleh modify terus supaya:

Upload payment proof → automatik masuk folder payment_proof_folder_id → simpan link dalam Google Sheet.

Tak perlu ubah struktur secrets.toml awak.

Pasted text(4).txt
Document

Ya — saya dah nampak puncanya dalam code awak. 👍

Masalahnya bukan pada upload_payment_proof() sahaja. Ada mismatch antara secrets.toml dengan code Streamlit.

Dalam code awak, bahagian upload mengambil folder ID daripada:

parent_folder_id = st.secrets["event"]["payment_proof_folder_id"]

Tetapi secrets.toml yang awak tunjuk tadi meletakkan ID itu di bawah:

[connections.gsheets]
payment_proof_folder_id = "1rXKv_eulYO8HfV0ZnLGPQ9n_LQkyhBjy"

Jadi code sepatutnya ambil daripada connections.gsheets, bukan event.

Tukar baris ini

Daripada:

parent_folder_id = st.secrets["event"]["payment_proof_folder_id"]

kepada:

parent_folder_id = st.secrets["connections"]["gsheets"]["payment_proof_folder_id"]

Jadi bahagian lengkapnya:

# ---- Upload ke Google Drive ----
with st.spinner("Menghantar ke Google Drive..."):
    try:
        parent_folder_id = st.secrets["connections"]["gsheets"]["payment_proof_folder_id"]
    except Exception:
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
Tapi ada satu lagi benda penting

Code awak memang sudah direka untuk hantar parent_folder_id ke upload_payment_proof().

Maksudnya, selepas kita betulkan path secrets, sama ada ia betul-betul masuk folder atau tidak bergantung pada code upload_payment_proof() dalam components.py.

Kalau function itu menggunakan Google Drive API dengan betul, ia sepatutnya create/upload file dengan:

"parents": [parent_folder_id]

Kalau components.py tak menggunakan parents, file akan tetap masuk ke root My Drive walaupun folder ID sudah betul.

Jadi sekarang saya cadangkan kita check components.py pula. Upload file components.py awak, dan saya boleh pinpoint terus bahagian yang perlu diubah supaya:

Payment proof → folder yang ID 1rXKv... → link folder disimpan dalam Payments sheet.

bagi full code

Boleh. Berdasarkan code yang awak upload, full code untuk page ini boleh kekalkan semua logic sedia ada dan betulkan bahagian folder ID supaya baca daripada [connections.gsheets].

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

# Admin WhatsApp
ADMIN_WA_NUMBER = "601157727459"
ADMIN_WA_DEFAULT_MSG = "Hi! PFM Car Boot Sale November"

FB_CATEGORIES = [
    "Local Food",
    "Dessert",
    "Coffee/Air",
    "Grill and BBQ",
    "Deep-Fry",
    "Italian/Western Food",
    "Japanese Food",
    "Chinese Food",
]


# ============================================================
# HELPER — WHATSAPP
# ============================================================
def whatsapp_button(label, message):
    wa_url = f"https://wa.me/{ADMIN_WA_NUMBER}?text={quote(message)}"

    st.markdown(
        f"""
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
        """,
        unsafe_allow_html=True,
    )


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
            return float(
                st.secrets["event"].get("deposit_others", 100)
            )

        return 0.0

    except Exception:
        return 0.0


def get_addon_price(addon_str):
    if addon_str is None or pd.isna(addon_str):
        return 0.0

    try:
        matches = re.findall(
            r"RM\s*([0-9]+(?:\.[0-9]+)?)",
            str(addon_str)
        )

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

        return [
            (name.strip(), float(price))
            for name, price in items
        ]

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
conn = st.connection(
    "gsheets",
    type=GSheetsConnection
)

df = load_sheet_safe(
    conn,
    "Vendors",
    ttl=0
)

if df is None:
    st.stop()


if "Paid" not in df.columns:
    df["Paid"] = False

df["Paid"] = df["Paid"].fillna(False).astype(bool)


# ============================================================
# FORM
# ============================================================
with st.form(
    "payment_upload",
    clear_on_submit=False
):

    plate_input = st.text_input(
        "No. Pendaftaran Kenderaan / Plate Number",
        placeholder="Contoh: NNA1806",
        help="Masukkan no. plate yang sama seperti semasa pendaftaran.",
    ).strip().upper()

    uploaded = st.file_uploader(
        "Pilih gambar bukti bayaran",
        type=[
            "jpg",
            "jpeg",
            "png",
            "pdf"
        ],
        help="Format dibenarkan: JPG, PNG, PDF. Saiz maksimum 10MB.",
    )

    st.markdown("---")

    submitted = st.form_submit_button(
        "Hantar Bukti Bayaran",
        type="primary",
        use_container_width=True
    )


# ============================================================
# PROSES
# ============================================================
if submitted:

    # --------------------------------------------------------
    # Validasi input asas
    # --------------------------------------------------------
    if not plate_input:
        st.error("❌ Sila masukkan No. Plate.")
        st.stop()

    if not uploaded:
        st.error("❌ Sila pilih fail bukti bayaran.")
        st.stop()


    # --------------------------------------------------------
    # Semak saiz fail
    # --------------------------------------------------------
    MAX_SIZE_MB = 10

    file_size_mb = uploaded.size / (1024 * 1024)

    if file_size_mb > MAX_SIZE_MB:
        st.error(
            f"❌ Saiz fail terlalu besar "
            f"({file_size_mb:.1f} MB). "
            f"Maksimum {MAX_SIZE_MB} MB."
        )
        st.stop()


    # --------------------------------------------------------
    # Cari vendor
    # --------------------------------------------------------
    normalized_input = (
        plate_input
        .replace(" ", "")
        .upper()
    )

    matched = df[
        df[COL_PLATE]
        .astype(str)
        .str.upper()
        .str.replace(" ", "")
        == normalized_input
    ]


    if matched.empty:

        st.error(
            f"❌ No. Plate **{plate_input}** "
            "tidak dijumpai dalam sistem."
        )

        st.info(
            "Sila pastikan No. Plate betul, "
            "atau daftar terlebih dahulu."
        )

        whatsapp_button(
            "💬 Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — "
            f"Saya nak tanya pasal pendaftaran "
            f"(Plate: {plate_input})"
        )

        st.stop()


    vendor = matched.iloc[0]

    vendor_name = str(
        vendor.get(COL_NAME, "")
    )

    status = str(
        vendor.get("Status", "")
    ).strip().title()

    vendor_type = str(
        vendor.get(
            COL_TYPE,
            "Car Boot Sales"
        )
    ).strip()

    fb_category = str(
        vendor.get(COL_CAT, "") or ""
    ).strip()


    # --------------------------------------------------------
    # Semak status
    # --------------------------------------------------------
    if status == "Pending":

        st.warning(
            "⚠️ Permohonan anda masih "
            "**Menunggu Semakan**. "
            "Bukti bayaran hanya boleh dihantar "
            "selepas permohonan diluluskan."
        )

        whatsapp_button(
            "💬 Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — "
            f"Permohonan saya masih pending "
            f"(Plate: {plate_input})"
        )

        st.stop()


    if status == "Rejected":

        st.error(
            "❌ Permohonan anda "
            "**Tidak Berjaya**. "
            "Sila hubungi admin untuk maklumat lanjut."
        )

        whatsapp_button(
            "💬 Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — "
            f"Nak tanya pasal permohonan yang ditolak "
            f"(Plate: {plate_input})"
        )

        st.stop()


    if status == "Cancelled":

        st.error(
            "🚫 Slot anda telah **Dibatalkan** "
            "kerana bayaran tidak diterima "
            "sebelum tarikh akhir. "
            "Hubungi admin jika ini satu kesilapan."
        )

        whatsapp_button(
            "💬 Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — "
            f"Slot saya telah dibatalkan "
            f"(Plate: {plate_input})"
        )

        st.stop()


    if status != "Approved":

        st.error(
            f"⚠️ Status tidak dikenali: **{status}**. "
            "Sila hubungi admin."
        )

        whatsapp_button(
            "💬 Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — "
            f"Status tidak dikenali "
            f"(Plate: {plate_input})"
        )

        st.stop()


    st.success(
        f"✅ Vendor dijumpai: "
        f"**{vendor_name}** ({vendor_type})"
    )


    # ========================================================
    # KIRA TOTAL HARGA
    # ========================================================
    cat_price = get_category_price(vendor_type)

    deposit_amount = get_deposit(vendor_type)

    addon_str_raw = str(
        vendor.get(COL_ADDON, "") or ""
    )

    addon_price = get_addon_price(
        addon_str_raw
    )

    addon_items = get_addon_items(
        addon_str_raw
    )

    total_price = (
        cat_price
        + deposit_amount
        + addon_price
    )


    # ========================================================
    # KAD HARGA
    # ========================================================
    if total_price > 0:

        breakdown_html = (
            f'<div>📦 {vendor_type}: '
            f'<b>{format_rm(cat_price)}</b></div>'
        )

        if deposit_amount > 0:

            breakdown_html += (
                f'<div>🔒 Deposit (Refundable): '
                f'<b>{format_rm(deposit_amount)}</b></div>'
            )

        if addon_price > 0:

            breakdown_html += (
                f'<div>➕ Add On: '
                f'<b>{format_rm(addon_price)}</b></div>'
            )


        st.markdown(
            f"""
            <div style="
                background-color: #fef9ec;
                border: 2px solid #f0e6d6;
                border-radius: 12px;
                padding: 1.5rem 1.75rem;
                margin: 1rem 0 0.75rem 0;
            ">

                <div style="
                    font-size: 0.8rem;
                    color: #78716c;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 0.5rem;
                ">
                    💰 Jumlah Perlu Dibayar
                </div>

                <div style="
                    font-size: 2.25rem;
                    font-weight: 700;
                    color: #78350f;
                    margin-bottom: 0.75rem;
                    line-height: 1;
                ">
                    {format_rm(total_price)}
                </div>

                <div style="
                    font-size: 0.85rem;
                    color: #57534e;
                    border-top: 1px dashed #e8dcc7;
                    padding-top: 0.75rem;
                    display: grid;
                    gap: 0.35rem;
                ">
                    {breakdown_html}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


        # ----------------------------------------------------
        # Detail ADD ON
        # ----------------------------------------------------
        if addon_items:

            with st.expander("📋 Detail Add On"):

                for name, price in addon_items:

                    st.markdown(
                        f"- {name}: "
                        f"**{format_rm(price)}**"
                    )


        # ----------------------------------------------------
        # Info bayaran
        # ----------------------------------------------------
        if deposit_amount > 0:

            st.info(
                f"💡 **Sila buat bayaran sebanyak "
                f"{format_rm(total_price)}** "
                f"({format_rm(cat_price + addon_price)} "
                f"bayaran + "
                f"{format_rm(deposit_amount)} deposit). "
                f"**Deposit {format_rm(deposit_amount)} "
                f"akan dipulangkan selepas event.**"
            )

        else:

            st.info(
                f"💡 **Sila buat bayaran sebanyak "
                f"{format_rm(total_price)}** "
                "sebelum upload bukti bayaran di bawah."
            )


        # ----------------------------------------------------
        # WhatsApp
        # ----------------------------------------------------
        whatsapp_button(
            "💬 Ada Pertanyaan? Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — "
            f"Saya nak tanya pasal bayaran "
            f"(Plate: {plate_input}, "
            f"Kategori: {vendor_type})"
        )

    else:

        st.warning(
            "⚠️ Total harga tidak dapat dikira "
            "secara automatik. "
            "Sila hubungi admin untuk jumlah bayaran."
        )

        whatsapp_button(
            "💬 Tanya Admin via WhatsApp",
            f"Hi! PFM Car Boot Sale — "
            f"Nak tanya pasal jumlah bayaran "
            f"(Plate: {plate_input})"
        )


    # ========================================================
    # SEMAK JIKA SUDAH UPLOAD
    # ========================================================
    existing_payments = load_sheet_safe(
        conn,
        "Payments",
        ttl=0
    )


    if (
        existing_payments is None
        or existing_payments.empty
    ):

        existing_payments = pd.DataFrame(
            columns=[
                "Timestamp",
                "Plate Number",
                PROOF_COL,
                "FolderUrl"
            ]
        )


    for col in [
        "Timestamp",
        "Plate Number",
        PROOF_COL,
        "FolderUrl"
    ]:

        if col not in existing_payments.columns:
            existing_payments[col] = ""


    already_uploaded = existing_payments[
        existing_payments["Plate Number"]
        .astype(str)
        .str.upper()
        .str.replace(" ", "")
        == normalized_input
    ]


    if not already_uploaded.empty:

        st.warning(
            f"⚠️ Anda sudah pernah upload "
            f"bukti bayaran sebelum ini "
            f"({len(already_uploaded)} rekod). "
            "Upload baru akan **tambah** rekod lama."
        )


    # ========================================================
    # UPLOAD KE GOOGLE DRIVE
    # ========================================================
    with st.spinner(
        "Menghantar ke Google Drive..."
    ):

        try:

            # IMPORTANT:
            # Folder ID sekarang diambil daripada:
            #
            # [connections.gsheets]
            # payment_proof_folder_id = "..."
            #
            parent_folder_id = (
                st.secrets["connections"]
                ["gsheets"]
                ["payment_proof_folder_id"]
            )

        except KeyError:

            st.error(
                "❌ Konfigurasi "
                "`payment_proof_folder_id` "
                "tidak dijumpai dalam secrets.toml."
            )

            st.code(
                """
[connections.gsheets]

payment_proof_folder_id = "YOUR_FOLDER_ID"
                """
            )

            st.stop()

        except Exception as e:

            st.error(
                f"❌ Gagal membaca konfigurasi folder: {e}"
            )

            st.stop()


        # ----------------------------------------------------
        # Upload
        # ----------------------------------------------------
        try:

            file_id, view_url, folder_url = (
                upload_payment_proof(
                    file_bytes=uploaded.getvalue(),
                    plate=plate_input,
                    vendor_type=vendor_type,
                    fb_category=fb_category,
                    parent_folder_id=parent_folder_id,
                    mime_type=uploaded.type
                    or "image/jpeg",
                )
            )

        except Exception as e:

            st.error(
                f"❌ Gagal upload ke Google Drive: {e}"
            )

            st.stop()


    # ========================================================
    # CHECK RESULT
    # ========================================================
    if not view_url:

        st.error(
            "❌ Gagal upload ke Google Drive. "
            "Sila cuba lagi atau hubungi admin."
        )

        whatsapp_button(
            "💬 Lapor Masalah ke Admin",
            f"Hi! PFM Car Boot Sale — "
            f"Upload bukti bayaran saya gagal "
            f"(Plate: {plate_input})"
        )

        st.stop()


    # ========================================================
    # SIMPAN REKOD KE GOOGLE SHEET
    # ========================================================
    new_row = pd.DataFrame(
        [{
            "Timestamp": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "Plate Number": plate_input,
            PROOF_COL: view_url,
            "FolderUrl": folder_url,
        }]
    )


    updated_payments = pd.concat(
        [
            existing_payments,
            new_row
        ],
        ignore_index=True
    )


    try:

        conn.update(
            worksheet="Payments",
            data=updated_payments
        )

        st.success(
            "💾 Rekod pembayaran disimpan dalam sistem."
        )

    except Exception as e:

        st.warning(
            "⚠️ Fail berjaya diupload ke Drive, "
            "tapi rekod tidak dapat disimpan "
            f"dalam sistem. Sila maklumkan admin. "
            f"(Error: {e})"
        )


    # ========================================================
    # PAPARKAN HASIL
    # ========================================================
    st.markdown("---")

    st.markdown(
        "### ✅ Bukti Bayaran Berjaya Dihantar"
    )

    st.markdown(
        f"**Vendor:** {vendor_name}  \n"
        f"**No. Plate:** `{plate_input}`"
    )


    if total_price > 0:

        st.markdown(
            f"**Jumlah:** {format_rm(total_price)}"
        )


    st.markdown(
        f"**Fail:** [Lihat Bukti]({view_url})"
    )


    if folder_url:

        st.markdown(
            f"**Folder vendor:** "
            f"[Buka Folder]({folder_url})"
        )


    st.info(
        "📌 **Seterusnya:** Admin akan semak "
        "bukti bayaran anda dan tanda "
        "'Sudah Bayar' dalam sistem. "
        "Sila sertai WhatsApp Group untuk "
        "update terkini."
    )


    # ========================================================
    # WHATSAPP — SELEPAS BERJAYA
    # ========================================================
    whatsapp_button(
        "💬 Ada Pertanyaan? Tanya Admin via WhatsApp",
        f"Hi! PFM Car Boot Sale — "
        f"Bukti bayaran saya telah dihantar "
        f"(Plate: {plate_input})"
    )


    # ========================================================
    # PREVIEW IMAGE
    # ========================================================
    if (
        uploaded.type
        and uploaded.type.startswith("image/")
    ):

        with st.expander(
            "Lihat gambar yang diupload"
        ):

            st.image(
                uploaded,
                use_container_width=True
            )


    st.balloons()

Tapi penting: code di atas membetulkan page awak sahaja. Dalam code asal memang function upload_payment_proof() dipanggil dengan parent_folder_id sebagai parameter.

Jadi kalau selepas perubahan ini file masih masuk ke My Drive/root dan bukan folder 1rXKv..., masalah seterusnya hampir pasti berada dalam components.py → function upload_payment_proof().

Kalau awak upload/paste components.py, saya boleh bagi full code components.py yang siap dengan Google Drive folder creation/upload, supaya terus masuk folder yang awak tetapkan.

Try ChatGPT Work in the desktop app
ChatGPT Work helps you move real work forward by turning one-off tasks into reusable workflows, polished outputs, and live artifacts. Included in your plan.
Download the app

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

============================================================
KONFIGURASI
============================================================

COL_NAME = "Nama/Name"
COL_PHONE = "Nombor Telefon/Phone Number"
COL_TYPE = "Kategori Produk/Product Category"
COL_CAT = "F&B CATEGORY"
COL_PLATE = "Plate Number"
COL_ADDON = "ADD ON"

PROOF_COL = "Upload Bukti Bayaran"

Admin WhatsApp

ADMIN_WA_NUMBER = "601157727459"
ADMIN_WA_DEFAULT_MSG = "Hi! PFM Car Boot Sale November"

FB_CATEGORIES = [
"Local Food", "Dessert", "Coffee/Air", "Grill and BBQ",
"Deep-Fry", "Italian/Western Food", "Japanese Food", "Chinese Food",
]

============================================================
HELPER — WHATSAPP
============================================================

def whatsapp_button(label, message):
wa_url = f"https://wa.me/{ADMIN_WA_NUMBER}?text={quote(message)}"
st.markdown(f"""
<a href="{wa_url}" target="_blank" style=" display: block; background-color: #25D366; color: #ffffff; text-align: center; padding: 0.85rem 1.5rem; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 1rem; margin-top: 0.75rem; ">{label}</a>
""", unsafe_allow_html=True)

============================================================
HELPER — KIRA HARGA
============================================================

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
matches = re.findall(r"RM\s*([0-9]+(?:.[0-9]+)?)", str(addon_str))
return sum(float(m) for m in matches)
except Exception:
return 0.0

def get_addon_items(addon_str):
if addon_str is None or pd.isna(addon_str):
return []
try:
items = re.findall(
r"([^,()]+?)\s*(Fee:\sRM\s([0-9.]+))",
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

============================================================
LOAD VENDORS
============================================================

conn = st.connection("gsheets", type=GSheetsConnection)
df = load_sheet_safe(conn, "Vendors", ttl=0)
if df is None:
st.stop()

if "Paid" not in df.columns:
df["Paid"] = False
df["Paid"] = df["Paid"].fillna(False).astype(bool)

============================================================
FORM
============================================================

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
============================================================
PROSES
============================================================

if submitted:
# ---- Validasi input asas ----
if not plate_input:
st.error("❌ Sila masukkan No. Plate.")
st.stop()

if not uploaded:
    st.error("❌ Sila pilih fail bukti bayaran.")
    st.stop()

# ---- Semak saiz fail (max 10MB) ----
MAX_SIZE_MB = 10
file_size_mb = uploaded.size / (1024 * 1024)
if file_size_mb > MAX_SIZE_MB:
    st.error(f"❌ Saiz fail terlalu besar ({file_size_mb:.1f} MB). Maksimum {MAX_SIZE_MB} MB.")
    st.stop()

# ---- Cari vendor ----
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

# ============================================================
# KIRA TOTAL HARGA
# ============================================================
cat_price = get_category_price(vendor_type)
deposit_amount = get_deposit(vendor_type)
addon_str_raw = str(vendor.get(COL_ADDON, "") or "")
addon_price = get_addon_price(addon_str_raw)
addon_items = get_addon_items(addon_str_raw)
total_price = cat_price + deposit_amount + addon_price

# === Kad harga ===
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

    # Detail ADD ON
    if addon_items:
        with st.expander("📋 Detail Add On"):
            for name, price in addon_items:
                st.markdown(f"- {name}: **{format_rm(price)}**")

    # Info bayaran
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

    # === BUTANG WHATSAPP ===
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

# === BUTANG WHATSAPP — selepas berjaya ===
whatsapp_button(
    "💬 Ada Pertanyaan? Tanya Admin via WhatsApp",
    f"Hi! PFM Car Boot Sale — Bukti bayaran saya telah dihantar (Plate: {plate_input})"
)

if uploaded.type and uploaded.type.startswith("image/"):
    with st.expander("Lihat gambar yang diupload"):
        st.image(uploaded, use_container_width=True)

st.balloons()
Close
