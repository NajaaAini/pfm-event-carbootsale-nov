import streamlit as st
import base64
import io
import re
import pandas as pd
from pathlib import Path
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# ============================================================
# HEADER
# ============================================================
def _image_base64(image_path):
    path = Path(image_path)
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def page_header(title="", subtitle="", image_path="assets/headerpfm.jpeg"):
    """Straight banner image only — no title, no subtitle."""
    img_b64 = _image_base64(image_path)

    if img_b64:
        st.markdown(f"""
        <div style="
            overflow: hidden;
            margin-bottom: 2rem;
            height: 320px;
            background-image: url('data:image/jpeg;base64,{img_b64}');
            background-size: cover;
            background-position: center;
            margin-left: -1rem;
            margin-right: -1rem;
            margin-top: -1rem;
        "></div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #a8a29e 0%, #78716c 100%);
            height: 320px;
            margin-bottom: 2rem;
            margin-left: -1rem;
            margin-right: -1rem;
            margin-top: -1rem;
        "></div>
        """, unsafe_allow_html=True)


# ============================================================
# GOOGLE SHEETS
# ============================================================
def load_sheet_safe(conn, worksheet, ttl=600):
    """
    Safely read from Google Sheets with friendly error messages.
    Returns DataFrame or None on error.
    """
    try:
        return conn.read(worksheet=worksheet, ttl=ttl)

    except Exception as e:
        error_msg = str(e).lower()

        # Quota error (429)
        if "429" in error_msg or "quota" in error_msg or "rate_limit" in error_msg:
            st.warning("""
            ⏳ **Sistem sedang sibuk.**

            Terlalu banyak permintaan dalam masa singkat. Sila tunggu **1-2 minit** dan cuba lagi.
            """)
            if st.button("🔄 Cuba Lagi"):
                st.cache_data.clear()
                st.rerun()
            return None

        # Auth / permission error
        elif "permission" in error_msg or "forbidden" in error_msg or "403" in error_msg:
            st.error("""
            🔒 **Akses ditolak.**

            Sistem tidak dapat membaca data. Sila hubungi admin untuk semak kebenaran.
            """)
            return None

        # Network / connection error
        elif "connection" in error_msg or "timeout" in error_msg or "network" in error_msg:
            st.warning("""
            🌐 **Masalah sambungan.**

            Tidak dapat sambung ke pelayan. Sila semak internet anda dan cuba lagi.
            """)
            if st.button("🔄 Cuba Lagi"):
                st.cache_data.clear()
                st.rerun()
            return None

        # Generic error
        else:
            st.error("""
            ⚠️ **Ada masalah teknikal.**

            Sistem tidak dapat memuatkan data. Sila cuba lagi atau hubungi admin.
            """)
            with st.expander("Lihat butiran teknikal"):
                st.code(str(e))
            return None


def log_action(conn, admin_name, action, plate, details=""):
    """
    Log admin actions to Log sheet.
    Auto-create if Log sheet doesn't exist yet.
    """
    try:
        logs = conn.read(worksheet="Log", ttl=0)
        if logs is None or logs.empty:
            logs = pd.DataFrame(columns=["Timestamp", "Admin", "Action", "Plate", "Details"])
    except Exception:
        logs = pd.DataFrame(columns=["Timestamp", "Admin", "Action", "Plate", "Details"])

    new_log = pd.DataFrame([{
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Admin": admin_name,
        "Action": action,
        "Plate": plate,
        "Details": details,
    }])

    updated = pd.concat([logs, new_log], ignore_index=True)

    try:
        conn.update(worksheet="Log", data=updated)
    except Exception:
        pass


def convert_df_to_csv(df):
    """Convert DataFrame to CSV bytes for download."""
    return df.to_csv(index=False).encode("utf-8")


# ============================================================
# GOOGLE DRIVE — UPLOAD BUKTI BAYARAN
# ============================================================
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_MIME = "application/vnd.google-apps.folder"


def _get_drive_service():
    """Build Drive client guna service account yang sama dengan gsheets."""
    info = dict(st.secrets["connections"]["gsheets"])
    creds_dict = info.get("credentials") or info
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=DRIVE_SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _sanitize(name: str) -> str:
    """Buang karakter yang Google Drive tak benarkan dalam nama folder/fail."""
    name = re.sub(r'[\\/:*?"<>|]', "-", str(name)).strip()
    return name or "UNKNOWN"


def _get_or_create_folder(service, parent_id: str, folder_name: str) -> str:
    """Cari folder by name dalam parent. Kalau tak ada, create baru. Return folder_id."""
    folder_name = _sanitize(folder_name)
    query = (
        f"'{parent_id}' in parents "
        f"and name = '{folder_name}' "
        f"and mimeType = '{FOLDER_MIME}' "
        f"and trashed = false"
    )
    res = service.files().list(q=query, fields="files(id)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]

    meta = {"name": folder_name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
    return service.files().create(body=meta, fields="id").execute()["id"]


def upload_payment_proof(
    file_bytes: bytes,
    plate: str,
    vendor_type: str,
    fb_category: str = "",
    parent_folder_id: str = "",
    mime_type: str = "image/jpeg",
):
    """
    Upload bukti bayaran ikut struktur:
        Car Boot Sales/<PLATE>_<timestamp>.jpg
        F&B/<Kategori>/<PLATE>_<timestamp>.jpg
        Others/<PLATE>_<timestamp>.jpg

    Return (file_id, view_url, folder_url) atau (None, None, None) kalau fail.
    """
    try:
        service = _get_drive_service()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Tentukan extension
        ext = "jpg"
        if mime_type:
            ext = mime_type.split("/")[-1].lower()
            if ext in ("jpeg", "jpg"):
                ext = "jpg"

        safe_plate = _sanitize(plate).upper().replace(" ", "")
        filename = f"{safe_plate}_{timestamp}.{ext}"

        # Tentukan folder target
        if vendor_type == "F&B":
            fb_root = _get_or_create_folder(service, parent_folder_id, "F&B")
            target_folder = _get_or_create_folder(
                service, fb_root, fb_category or "Uncategorized"
            )
        elif vendor_type == "Car Boot Sales":
            target_folder = _get_or_create_folder(
                service, parent_folder_id, "Car Boot Sales"
            )
        else:
            # Others (Arts & Crafts / Toys, dan lain-lain)
            target_folder = _get_or_create_folder(
                service, parent_folder_id, "Others"
            )

        # Upload fail
        file_metadata = {"name": filename, "parents": [target_folder]}
        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes), mimetype=mime_type, resumable=False
        )
        file = service.files().create(
            body=file_metadata, media_body=media, fields="id, webViewLink"
        ).execute()

        # Make viewable by anyone with link
        try:
            service.permissions().create(
                fileId=file["id"],
                body={"role": "reader", "type": "anyone"},
            ).execute()
        except Exception:
            pass

        folder_url = f"https://drive.google.com/drive/folders/{target_folder}"
        return file["id"], file["webViewLink"], folder_url

    except Exception as e:
        st.error(f"Gagal upload ke Google Drive: {e}")
        return None, None, None