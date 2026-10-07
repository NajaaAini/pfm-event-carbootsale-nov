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
# TITLE
# ============================================================
st.markdown("""
<div style="
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
">
    <div style="
        width: 44px;
        height: 44px;
        background-color: #f2ebe0;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
    ">🔍</div>
    <h1 style="
        margin: 0;
        color: #292524;
        font-weight: 600;
        font-size: 1.85rem;
        border: none;
        padding: 0;
    ">Semak Kelayakan</h1>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<p style="
    color: #78716c;
    font-size: 0.95rem;
    margin-bottom: 2rem;
">Masukkan No. Pendaftaran Kenderaan/Plate Number anda untuk semak status permohonan.</p>
""", unsafe_allow_html=True)

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
        st.warning("""
        ⏳ **Sistem sedang sibuk.**

        Terlalu banyak permintaan. Sila tunggu **1-2 minit** dan cuba lagi.
        """)
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
        st.markdown(f"""
        <div style="
            background-color: #fef3c7;
            border: 1px solid #fde68a;
            border-radius: 12px;
            padding: 1.5rem 1.75rem;
            margin-top: 1rem;
        ">
            <div style="
                font-size: 1.05rem;
                font-weight: 600;
                color: #78350f;
                margin-bottom: 0.5rem;
            ">❌ Tiada permohonan dijumpai</div>
            <div style="
                color: #78350f;
                font-size: 0.95rem;
                margin-bottom: 1.25rem;
            "><b>{query}</b> tidak ada dalam sistem. Sila daftar terlebih dahulu atau hubungi admin.</div>
            <a href="https://forms.gle/bheUdQTvKRTCns4eA" target="_blank" style="
                display: block;
                background-color: #78350f;
                color: #ffffff;
                text-align: center;
                padding: 0.85rem 1.5rem;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                font-size: 1rem;
            ">📝 Daftar Sekarang</a>
        </div>
        """, unsafe_allow_html=True)

    else:
        row = result.iloc[0]
        status = str(row["Status"]).strip()
        paid = bool(row["Paid"]) if pd.notna(row["Paid"]) else False
        plate_norm = str(row[COL_PLATE]).upper().replace(" ", "")

        st.divider()

        # ====================================================
        # INFO CARD
        # ====================================================
        fb_row = ""
        if pd.notna(row.get(COL_CAT)) and str(row[COL_CAT]).strip():
            fb_row = (
                f'<div style="color:#44403c;">'
                f'<span style="color:#78716c;">F&B Category:</span> '
                f'<b style="color:#292524;">{row[COL_CAT]}</b>'
                f'</div>'
            )

        info_card_html = (
            f'<div style="background-color:#ffffff;border:1px solid #e8dcc7;'
            f'border-radius:12px;padding:1.5rem 1.75rem;margin-bottom:1.5rem;">'
            f'<div style="font-size:0.8rem;color:#78716c;text-transform:uppercase;'
            f'letter-spacing:0.5px;margin-bottom:0.5rem;">Maklumat Permohonan</div>'
            f'<div style="font-size:1.3rem;font-weight:600;color:#292524;'
            f'margin-bottom:0.75rem;">{row[COL_PLATE]}</div>'
            f'<div style="display:grid;gap:0.5rem;">'
            f'<div style="color:#44403c;"><span style="color:#78716c;">Nama:</span> '
            f'<b style="color:#292524;">{row[COL_NAME]}</b></div>'
            f'<div style="color:#44403c;"><span style="color:#78716c;">Kategori:</span> '
            f'<b style="color:#292524;">{row[COL_TYPE]}</b></div>'
            f'{fb_row}'
            f'</div>'
            f'</div>'
        )

        st.markdown(info_card_html, unsafe_allow_html=True)

        # ====================================================
        # CHECK: BUKTI BAYARAN DAH UPLOAD?
        # ====================================================
        has_uploaded_proof = False
        proof_upload_time = ""
        proof_url = ""
        folder_url = ""

        if status == "Approved" and not paid:
            payments, pay_err = load_payments()
            if payments is not None and not payments.empty:
                if "Plate Number" in payments.columns:
                    matched_pay = payments[
                        payments["Plate Number"].astype(str).str.upper().str.replace(" ", "")
                        == plate_norm
                    ]
                    if not matched_pay.empty:
                        has_uploaded_proof = True
                        try:
                            matched_pay = matched_pay.sort_values("Timestamp", ascending=False)
                        except Exception:
                            pass
                        latest = matched_pay.iloc[0]
                        proof_upload_time = str(latest.get("Timestamp", "") or "")
                        proof_url = str(latest.get(PROOF_COL, "") or "")
                        folder_url = str(latest.get("FolderUrl", "") or "")

        # ====================================================
        # STATUS KAD
        # ====================================================

        # ---------- PENDING ----------
        if status == "Pending":
            st.markdown("""
            <div style="
                background-color: #fffbeb;
                border: 1px solid #fde68a;
                border-radius: 12px;
                padding: 1.5rem 1.75rem;
                margin-bottom: 1rem;
            ">
                <div style="display: flex;align-items: center;gap: 0.75rem;margin-bottom: 0.75rem;">
                    <div style="
                        width: 36px;height: 36px;background-color: #f59e0b;
                        color: #ffffff;border-radius: 50%;
                        display: flex;align-items: center;justify-content: center;
                        font-size: 1.1rem;font-weight: 700;
                    ">⏳</div>
                    <div style="font-size: 1.15rem;font-weight: 700;color: #78350f;">
                        Permohonan Sedang Disemak
                    </div>
                </div>
                <div style="color: #78350f;font-size: 0.95rem;">
                    Permohonan anda telah diterima dan sedang dalam proses semakan admin. Sila semak semula dalam <b>1-2 hari</b>.
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.info("📌 **Belum perlu buat bayaran.** Bayaran hanya diperlukan selepas permohonan anda diluluskan.")

        # ---------- REJECTED ----------
        elif status == "Rejected":
            st.markdown("""
            <div style="
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 12px;
                padding: 1.5rem 1.75rem;
                margin-bottom: 1rem;
            ">
                <div style="display: flex;align-items: center;gap: 0.75rem;margin-bottom: 0.75rem;">
                    <div style="
                        width: 36px;height: 36px;background-color: #dc2626;
                        color: #ffffff;border-radius: 50%;
                        display: flex;align-items: center;justify-content: center;
                        font-size: 1.1rem;font-weight: 700;
                    ">✕</div>
                    <div style="font-size: 1.15rem;font-weight: 700;color: #991b1b;">
                        Permohonan Tidak Berjaya
                    </div>
                </div>
                <div style="color: #991b1b;font-size: 0.95rem;">
                    Maaf, permohonan anda tidak dipilih untuk event ini. Hubungi admin untuk maklumat lanjut.
                </div>
            </div>
            """, unsafe_allow_html=True)

            reject_reason = ""
            if pd.notna(row.get("Notes")) and str(row.get("Notes")).strip():
                reject_reason = str(row.get("Notes")).strip()

            if reject_reason:
                safe_reason = (
                    reject_reason
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                st.markdown(f"""
                <div style="
                    background-color: #ffffff;
                    border: 1px solid #fecaca;
                    border-left: 4px solid #dc2626;
                    border-radius: 8px;
                    padding: 1.1rem 1.35rem;
                    margin-bottom: 1rem;
                ">
                    <div style="
                        font-size: 0.78rem;
                        color: #78716c;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        font-weight: 600;
                        margin-bottom: 0.5rem;
                    ">📋 Sebab Penolakan</div>
                    <div style="
                        color: #292524;
                        font-size: 0.95rem;
                        line-height: 1.6;
                    ">{safe_reason}</div>
                </div>
                """, unsafe_allow_html=True)

        # ---------- CANCELLED ----------
        elif status == "Cancelled":
            st.markdown("""
            <div style="
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 12px;
                padding: 1.5rem 1.75rem;
                margin-bottom: 1rem;
            ">
                <div style="display: flex;align-items: center;gap: 0.75rem;margin-bottom: 0.75rem;">
                    <div style="
                        width: 36px;height: 36px;background-color: #dc2626;
                        color: #ffffff;border-radius: 50%;
                        display: flex;align-items: center;justify-content: center;
                        font-size: 1.1rem;font-weight: 700;
                    ">🚫</div>
                    <div style="font-size: 1.15rem;font-weight: 700;color: #991b1b;">
                        Slot Dibatalkan
                    </div>
                </div>
                <div style="color: #991b1b;font-size: 0.95rem;">
                    Slot anda telah dibatalkan kerana bayaran tidak diterima sebelum tarikh akhir. Hubungi admin jika ada masalah.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ---------- APPROVED ----------
        elif status == "Approved":

            # ==========================================
            # CASE 1: Approved + BELUM Paid + DAH UPLOAD BUKTI
            # ==========================================
            if not paid and has_uploaded_proof:
                st.markdown(f"""
                <div style="
                    background-color: #eff6ff;
                    border: 1px solid #bfdbfe;
                    border-radius: 12px;
                    padding: 1.5rem 1.75rem;
                    margin-bottom: 1rem;
                ">
                    <div style="display: flex;align-items: center;gap: 0.75rem;margin-bottom: 0.75rem;">
                        <div style="
                            width: 36px;height: 36px;background-color: #2563eb;
                            color: #ffffff;border-radius: 50%;
                            display: flex;align-items: center;justify-content: center;
                            font-size: 1.1rem;font-weight: 700;
                        ">📤</div>
                        <div style="font-size: 1.15rem;font-weight: 700;color: #1e40af;">
                            Bukti Bayaran Telah Dihantar
                        </div>
                    </div>
                    <div style="color: #1e40af;font-size: 0.95rem;">
                        Terima kasih! Bukti bayaran anda telah diterima
                        {'pada <b>' + proof_upload_time + '</b>' if proof_upload_time else ''}.
                        Admin akan semak dan sahkan slot anda tidak lama lagi.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.info(
                    "📌 **Seterusnya:** Sila tunggu pengesahan admin dan jangan lupa untuk join group whatsapp."
                )

                if proof_url or folder_url:
                    with st.expander("📎 Lihat bukti yang dihantar"):
                        if proof_url:
                            st.markdown(f"[📄 Fail Bukti Bayaran]({proof_url})")
                        if folder_url:
                            st.markdown(f"[📁 Folder Bukti]({folder_url})")

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
                        margin-bottom: 1.5rem;
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

                # === KAD STATUS APPROVED ===
                st.markdown("""
                <div style="
                    background-color: #fffbeb;
                    border: 1px solid #fde68a;
                    border-radius: 12px;
                    padding: 1.5rem 1.75rem;
                    margin-bottom: 1.5rem;
                ">
                    <div style="display: flex;align-items: center;gap: 0.75rem;margin-bottom: 0.75rem;">
                        <div style="
                            width: 36px;height: 36px;background-color: #78350f;
                            color: #ffffff;border-radius: 50%;
                            display: flex;align-items: center;justify-content: center;
                            font-size: 1.1rem;font-weight: 700;
                        ">✓</div>
                        <div style="font-size: 1.15rem;font-weight: 700;color: #78350f;">
                            Permohonan Diluluskan
                        </div>
                    </div>
                    <div style="color: #78350f;font-size: 0.95rem;">
                        Tahniah! Permohonan anda telah diluluskan. Sila buat bayaran dan upload bukti untuk konfirmasi slot anda.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # === KAD MAKLUMAT PEMBAYARAN ===
                st.markdown("""
                <div style="
                    background-color: #ffffff;
                    border: 1px solid #e8dcc7;
                    border-radius: 12px;
                    padding: 1.5rem 1.75rem;
                    margin-bottom: 1.5rem;
                ">
                    <div style="
                        font-size: 0.8rem;
                        color: #78716c;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        font-weight: 600;
                        margin-bottom: 0.75rem;
                    ">💳 Maklumat Pembayaran</div>

                    <div style="
                        display: grid;
                        gap: 0.5rem;
                        font-size: 0.9rem;
                        color: #292524;
                    ">
                        <div>
                            <span style="color: #78716c; display: inline-block; min-width: 130px;">🏦 Bank</span>
                            <b>MAYBANK</b>
                        </div>
                        <div>
                            <span style="color: #78716c; display: inline-block; min-width: 130px;">👤 Nama Akaun</span>
                            <b>PRINTHERO MERCHANDISE SDN. BHD.</b>
                        </div>
                        <div>
                            <span style="color: #78716c; display: inline-block; min-width: 130px;">🔢 No. Akaun</span>
                            <b style="letter-spacing: 1px;">557054621057</b>
                        </div>
                        <div>
                            <span style="color: #78716c; display: inline-block; min-width: 130px;">📝 Remark</span>
                            <b>PFMCBS (4 digit terakhir No. Telefon)</b>
                        </div>
                        <div>
                            <span style="color: #78716c; display: inline-block; min-width: 130px;">📋 Contoh</span>
                            <b>PFMCBS1234</b>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # === NOTA PENTING ===
                st.markdown("""
                <div style="
                    background-color: #fef2f2;
                    border: 1px solid #fecaca;
                    border-radius: 12px;
                    padding: 1rem 1.25rem;
                    margin-bottom: 1.5rem;
                ">
                    <div style="color: #991b1b; font-size: 0.9rem; font-weight: 500;">
                        ⚠️ <b>Penting:</b> Kalau bayaran tidak diterima <b>2 hari sebelum event</b>, slot anda akan dibatalkan automatik.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # === BUTANG LINK GOOGLE FORM ===
                try:
                    st.link_button(
                        "📤  Upload Bukti Bayaran",
                        st.secrets["event"]["payment_form_url"],
                        use_container_width=True,
                        type="primary",
                    )
                except AttributeError:
                    st.markdown(
                        f"""
                        <a href="{st.secrets['event']['payment_form_url']}" target="_blank" style="
                            display: block;
                            background-color: #78350f;
                            color: #ffffff;
                            text-align: center;
                            padding: 0.85rem 1.5rem;
                            border-radius: 8px;
                            text-decoration: none;
                            font-weight: 600;
                            font-size: 1rem;
                            margin-top: 0.5rem;
                        ">📤 Upload Bukti Bayaran</a>
                        """,
                        unsafe_allow_html=True,
                    )

            # ==========================================
            # CASE 3: Approved + DAH Paid
            # ==========================================
            else:
                st.markdown("""
                <div style="
                    background-color: #f0fdf4;
                    border: 1px solid #86efac;
                    border-radius: 12px;
                    padding: 1.5rem 1.75rem;
                    margin-bottom: 1rem;
                ">
                    <div style="display: flex;align-items: center;gap: 0.75rem;margin-bottom: 0.75rem;">
                        <div style="
                            width: 36px;height: 36px;background-color: #16a34a;
                            color: #ffffff;border-radius: 50%;
                            display: flex;align-items: center;justify-content: center;
                            font-size: 1.1rem;font-weight: 700;
                        ">✓</div>
                        <div style="font-size: 1.15rem;font-weight: 700;color: #14532d;">
                            Permohonan Disahkan
                        </div>
                    </div>
                    <div style="color: #166534;font-size: 0.95rem;">
                        Tahniah! Anda telah berjaya mendaftar dan membuat pembayaran. Sertai kumpulan WhatsApp vendor untuk maklumat lanjut.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                <div style="
                    font-size: 1rem;
                    font-weight: 600;
                    color: #292524;
                    margin-top: 1.5rem;
                    margin-bottom: 0.25rem;
                ">Sertai WhatsApp Group Vendor</div>
                <div style="
                    color: #78716c;
                    font-size: 0.9rem;
                    margin-bottom: 1rem;
                ">Dapatkan maklumat terkini tentang event, susun atur booth, dan update penting.</div>
                """, unsafe_allow_html=True)

                try:
                    st.link_button(
                        "💬  Join WhatsApp Group",
                        st.secrets["event"]["whatsapp_group"],
                        use_container_width=True,
                        type="primary",
                    )
                except AttributeError:
                    st.markdown(
                        f"""
                        <a href="{st.secrets['event']['whatsapp_group']}" target="_blank" style="
                            display: block;
                            background-color: #78350f;
                            color: #ffffff;
                            text-align: center;
                            padding: 0.85rem 1.5rem;
                            border-radius: 8px;
                            text-decoration: none;
                            font-weight: 600;
                            font-size: 1rem;
                        ">Join WhatsApp Group</a>
                        """,
                        unsafe_allow_html=True,
                    )

                st.balloons()

        # ---------- UNKNOWN ----------
        else:
            st.warning(
                f"⚠️ Status permohonan tidak dikenali: **{status}**. "
                "Sila hubungi admin untuk maklumat lanjut."
            )
