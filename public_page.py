import streamlit as st
import pandas as pd
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

# Nama column bukti bayaran dalam Sheet
PROOF_COL = "Upload Bukti Bayaran"

VALID_STATUSES = ["Pending", "Approved", "Rejected", "Cancelled"]


# ============================================================
# HELPER — Normalize Status
# ============================================================
def normalize_status(raw):
    """Normalize status kepada format standard."""
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

# Normalize status column
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

        # Hanya check kalau status Approved & belum Paid
        if status == "Approved" and not paid:
            payments, pay_err = load_payments()
            if payments is not None and not payments.empty:
                # Pastikan column wujud
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
                        # FIX: guna PROOF_COL = "Upload Bukti Bayaran"
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

        # ---------- CANCELLED ----------
        elif status == "Cancelled":
            st.markdown("""
            <div style="
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 12px;
                padding: 1.5rem 1.75rem;
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
                    "📌 **Seterusnya:** Sila tunggu pengesahan admin dan jangan lupa untuk join group whatsapp nanti bila dah approve."
                )                    

            # ==========================================
            # CASE 2: Approved + BELUM Paid + BELUM UPLOAD
            # ==========================================
            elif not paid and not has_uploaded_proof:
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

                st.markdown("""
                <div style="
                    background-color: #fef2f2;
                    border: 1px solid #fecaca;
                    border-radius: 12px;
                    padding: 1rem 1.25rem;
                    margin-bottom: 1rem;
                ">
                    <div style="color: #991b1b; font-size: 0.9rem; font-weight: 500;">
                        ⚠️ <b>Penting:</b> Kalau bayaran tidak diterima <b>2 hari sebelum event</b>, slot anda akan dibatalkan automatik.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Butang upload — cuba page_link dulu, fallback ke link_button
                try:
                    st.page_link(
                        "upload_payment.py",
                        label="📤  Upload Bukti Bayaran",
                        use_container_width=True,
                    )
                except Exception:
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

            # Butang WhatsApp
            wa_number = "601157727459"
            wa_message = "Hi! PFM Car Boot Sale November"
            wa_url = f"https://wa.me/{wa_number}?text={wa_message.replace(' ', '%20').replace('!', '%21')}"

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
            ">💬 Hubungi Admin via WhatsApp</a>
            """, unsafe_allow_html=True)
