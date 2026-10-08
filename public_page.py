import streamlit as st
import pandas as pd
import re

from streamlit_gsheets import GSheetsConnection
from style import apply_style
from components import page_header, load_sheet_safe


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Semak Kelayakan",
    layout="wide"
)

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

PROOF_COL = "Upload Bukti Bayaran dan Pemilihan Lot"

VALID_STATUSES = [
    "Pending",
    "Approved",
    "Rejected",
    "Cancelled"
]


# ============================================================
# HELPER — NORMALIZE STATUS
# ============================================================
def normalize_status(raw):

    if raw is None or pd.isna(raw):
        return "Pending"

    if str(raw).strip() == "":
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
            return float(
                st.secrets["event"]["price_car_boot"]
            )

        elif vendor_type == "F&B":
            return float(
                st.secrets["event"]["price_fb"]
            )

        else:
            return float(
                st.secrets["event"]["price_others"]
            )

    except Exception:
        return 0.0


# ============================================================
# HELPER — DEPOSIT
# ============================================================
def get_deposit(vendor_type):
    """
    Deposit refundable:
    - F&B
    - Arts/Crafts & Others
    """

    try:

        if vendor_type == "F&B":

            return float(
                st.secrets["event"]["deposit_fb"]
            )

        elif vendor_type == "Arts/Crafts & Others":

            return float(
                st.secrets["event"].get(
                    "deposit_others",
                    100
                )
            )

        return 0.0

    except Exception:
        return 0.0


# ============================================================
# HELPER — ADD ON PRICE
# ============================================================
def get_addon_price(addon_str):

    if addon_str is None or pd.isna(addon_str):
        return 0.0

    try:

        matches = re.findall(
            r"RM\s*([0-9]+(?:\.[0-9]+)?)",
            str(addon_str)
        )

        return sum(
            float(m)
            for m in matches
        )

    except Exception:
        return 0.0


# ============================================================
# HELPER — FORMAT RM
# ============================================================
def format_rm(amount):

    try:
        return f"RM {float(amount):,.2f}"

    except (ValueError, TypeError):
        return "RM 0.00"


# ============================================================
# HELPER — AMBIL INFO PAYMENT
# ============================================================
def get_vendor_payment_info(
    payments_df,
    plate_norm
):

    """
    Ambil info terkini dari Sheet Payments.
    """

    if payments_df is None:
        return {}

    if payments_df.empty:
        return {}

    if "Plate Number" not in payments_df.columns:
        return {}

    matched = payments_df[
        payments_df["Plate Number"]
        .astype(str)
        .str.upper()
        .str.replace(" ", "")
        == plate_norm
    ]

    if matched.empty:
        return {}

    try:

        matched = matched.sort_values(
            "Timestamp",
            ascending=False
        )

    except Exception:
        pass

    latest = matched.iloc[0]

    def _clean(v):

        s = str(v or "").strip()

        if s.lower() in (
            "nan",
            "none",
            "nat",
            "null"
        ):
            return ""

        return s

    return {
        "proof_url": _clean(
            latest.get(PROOF_COL, "")
        ),

        "folder_url": _clean(
            latest.get("FolderUrl", "")
        ),

        "timestamp": _clean(
            latest.get("Timestamp", "")
        ),

        "pilih_jenis": _clean(
            latest.get("Pilih Jenis", "")
        ),

        "parking_lot": _clean(
            latest.get("Pilih parking lot", "")
        ),

        "fnb_lot": _clean(
            latest.get("Pilih F&B Lot", "")
        ),

        # Baca kolum baru dahulu, fallback ke kolum lama
        "arts_lot": _clean(
            latest.get("Pilih Arts/Crafts & Others Lot", "")
            or latest.get("Pilih Arts & Crafts / Toys Lot", "")
        ),
    }


# ============================================================
# TITLE
# ============================================================
st.title("🔍 Semak Kelayakan")

st.caption(
    "Masukkan No. Pendaftaran Kenderaan/Plate Number "
    "anda untuk semak status permohonan."
)


# ============================================================
# LOAD VENDORS
# ============================================================
@st.cache_data(
    ttl=60,
    show_spinner="Memuatkan data..."
)
def load_vendors():

    conn = st.connection(
        "gsheets",
        type=GSheetsConnection
    )

    try:

        return (
            conn.read(
                worksheet="Vendors",
                ttl=60
            ),
            None
        )

    except Exception as e:

        return (
            None,
            str(e)
        )


# ============================================================
# LOAD PAYMENTS
# ============================================================
@st.cache_data(
    ttl=60,
    show_spinner=False
)
def load_payments():

    conn = st.connection(
        "gsheets",
        type=GSheetsConnection
    )

    try:

        return (
            conn.read(
                worksheet="Payments",
                ttl=60
            ),
            None
        )

    except Exception as e:

        return (
            None,
            str(e)
        )


# ============================================================
# GET VENDORS DATA
# ============================================================
df, err = load_vendors()


if df is None:

    error_msg = (err or "").lower()

    if (
        "429" in error_msg
        or "quota" in error_msg
    ):

        st.warning(
            "⏳ **Sistem sedang sibuk.** "
            "Terlalu banyak permintaan. "
            "Sila tunggu **1-2 minit** dan cuba lagi."
        )

        if st.button("🔄 Cuba Lagi"):

            st.cache_data.clear()
            st.rerun()

    else:

        st.error(
            "⚠️ Sistem tidak dapat memuatkan data. "
            "Sila cuba lagi."
        )

        with st.expander(
            "Butiran teknikal"
        ):

            st.code(err)

    st.stop()


# ============================================================
# NORMALIZE STATUS
# ============================================================
if "Status" not in df.columns:

    df["Status"] = "Pending"

else:

    df["Status"] = df["Status"].apply(
        normalize_status
    )


# ============================================================
# WHATSAPP ADMIN
# ============================================================
WA_ADMIN = "601157727459"

WA_TEXT = (
    "Hi! Pertanyaan tentang vendor carbootsale PFM : ."
)


def _encode_wa(text):

    return (
        text
        .replace(" ", "%20")
        .replace("\n", "%0A")
        .replace(",", "%2C")
        .replace("?", "%3F")
        .replace("&", "%26")
    )


WA_URL = (
    f"https://wa.me/{WA_ADMIN}"
    f"?text={_encode_wa(WA_TEXT)}"
)


# ============================================================
# SEARCH FORM
# ============================================================
with st.form("search"):

    query = st.text_input(
        "No. Pendaftaran Kenderaan/Plate Number",
        placeholder="Contoh: NNA1806"
    ).strip().upper()

    col1, col2, col3, col4 = st.columns(
        [1, 1, 1, 1]
    )

    with col2:

        submitted = st.form_submit_button(
            "Semak Status",
            type="primary",
            use_container_width=True
        )

    with col3:

        st.link_button(
            "💬 WhatsApp Admin",
            WA_URL,
            use_container_width=True,
            key="wa_admin_btn",
        )


# ============================================================
# RESULT
# ============================================================
if submitted and query:

    result = df[
        df[COL_PLATE]
        .astype(str)
        .str.upper()
        .str.replace(" ", "")
        == query.replace(" ", "")
    ]


    # ========================================================
    # NO RESULT
    # ========================================================
    if result.empty:

        st.divider()

        with st.container(border=True):

            st.error(
                "❌ **Tiada permohonan dijumpai**"
            )

            st.markdown(
                f"**{query}** tidak ada dalam sistem. "
                "Sila daftar terlebih dahulu atau "
                "hubungi admin."
            )

            st.link_button(
                "📝 Daftar Sekarang",
                "https://forms.gle/bheUdQTvKRTCns4eA",
                use_container_width=True,
                type="primary",
            )


    # ========================================================
    # FOUND
    # ========================================================
    else:

        row = result.iloc[0]

        status = str(
            row["Status"]
        ).strip()

        paid = (
            bool(row["Paid"])
            if "Paid" in row
            and pd.notna(row["Paid"])
            else False
        )

        plate_norm = (
            str(row[COL_PLATE])
            .upper()
            .replace(" ", "")
        )


        st.divider()


        # ====================================================
        # INFO CARD
        # ====================================================
        with st.container(border=True):

            st.caption(
                "MAKLUMAT PERMOHONAN"
            )

            st.subheader(
                str(row[COL_PLATE])
            )

            st.markdown(
                f"**Nama:** {row[COL_NAME]}"
            )

            st.markdown(
                f"**Kategori:** {row[COL_TYPE]}"
            )

            if (
                pd.notna(row.get(COL_CAT))
                and str(row.get(COL_CAT)).strip()
            ):

                st.markdown(
                    f"**F&B Category:** "
                    f"{row[COL_CAT]}"
                )


        # ====================================================
        # AMBIL INFO PAYMENT
        # ====================================================
        payments_df, _ = load_payments()

        payment_info = (
            get_vendor_payment_info(
                payments_df,
                plate_norm
            )
        )

        has_uploaded_proof = bool(
            payment_info.get(
                "proof_url"
            )
        )

        proof_upload_time = (
            payment_info.get(
                "timestamp",
                ""
            )
        )

        parking_lot = (
            payment_info.get(
                "parking_lot",
                ""
            )
        )

        fnb_lot = (
            payment_info.get(
                "fnb_lot",
                ""
            )
        )

        arts_lot = (
            payment_info.get(
                "arts_lot",
                ""
            )
        )


        # ====================================================
        # STATUS KAD
        # ====================================================

        # ====================================================
        # PENDING
        # ====================================================
        if status == "Pending":

            with st.container(border=True):

                st.warning(
                    "⏳ **Permohonan Sedang Disemak**"
                )

                st.markdown(
                    "Permohonan anda telah diterima "
                    "dan sedang dalam proses semakan "
                    "admin. Sila semak semula dalam "
                    "**1-2 hari**."
                )

            st.info(
                "📌 **Belum perlu buat bayaran.** "
                "Bayaran hanya diperlukan selepas "
                "permohonan anda diluluskan."
            )


        # ====================================================
        # REJECTED
        # ====================================================
        elif status == "Rejected":

            with st.container(border=True):

                st.error(
                    "✕ **Permohonan Tidak Berjaya**"
                )

                st.markdown(
                    "Maaf, permohonan anda tidak "
                    "dipilih untuk event ini. "
                    "Hubungi admin untuk maklumat lanjut."
                )


            reject_reason = ""

            if (
                pd.notna(row.get("Notes"))
                and str(row.get("Notes")).strip()
            ):

                reject_reason = str(
                    row.get("Notes")
                ).strip()


            if reject_reason:

                with st.container(
                    border=True
                ):

                    st.caption(
                        "📋 SEBAB PENOLAKAN"
                    )

                    st.markdown(
                        reject_reason
                    )


        # ====================================================
        # CANCELLED
        # ====================================================
        elif status == "Cancelled":

            with st.container(border=True):

                st.error(
                    "🚫 **Slot Dibatalkan**"
                )

                st.markdown(
                    "Slot anda telah dibatalkan "
                    "kerana bayaran tidak diterima "
                    "sebelum tarikh akhir. "
                    "Hubungi admin jika ada masalah."
                )


        # ====================================================
        # APPROVED
        # ====================================================
        elif status == "Approved":


            # ==================================================
            # CASE 1:
            # APPROVED + BELUM PAID + DAH UPLOAD BUKTI
            # ==================================================
            if (
                not paid
                and has_uploaded_proof
            ):

                with st.container(
                    border=True
                ):

                    st.info(
                        "📤 **Bukti Bayaran "
                        "Telah Dihantar**"
                    )

                    if proof_upload_time:

                        st.markdown(
                            "Terima kasih! Bukti bayaran "
                            "anda telah diterima pada "
                            f"**{proof_upload_time}**. "
                            "Admin akan semak dan sahkan "
                            "slot anda tidak lama lagi."
                        )

                    else:

                        st.markdown(
                            "Terima kasih! Bukti bayaran "
                            "anda telah diterima. "
                            "Admin akan semak dan sahkan "
                            "slot anda tidak lama lagi."
                        )

                st.info(
                    "📌 **Seterusnya:** "
                    "Sila tunggu pengesahan admin."
                )


            # ==================================================
            # CASE 2:
            # APPROVED + BELUM PAID + BELUM UPLOAD
            # ==================================================
            elif (
                not paid
                and not has_uploaded_proof
            ):

                # ==============================================
                # KAD HARGA
                # ==============================================
                vendor_type = str(
                    row.get(
                        COL_TYPE,
                        ""
                    )
                ).strip()

                cat_price = get_category_price(
                    vendor_type
                )

                deposit_amount = get_deposit(
                    vendor_type
                )

                addon_str_raw = str(
                    row.get(
                        COL_ADDON,
                        ""
                    )
                    or ""
                )

                addon_price = get_addon_price(
                    addon_str_raw
                )

                total_price = (
                    cat_price
                    + deposit_amount
                    + addon_price
                )


                if total_price > 0:

                    with st.container(
                        border=True
                    ):

                        st.caption(
                            "💰 JUMLAH PERLU DIBAYAR"
                        )

                        st.markdown(
                            f"# {format_rm(total_price)}"
                        )

                        st.divider()

                        st.markdown(
                            f"📦 **{vendor_type}**: "
                            f"{format_rm(cat_price)}"
                        )

                        if deposit_amount > 0:

                            st.markdown(
                                "🔒 **Deposit "
                                "(Refundable):** "
                                f"{format_rm(deposit_amount)}"
                            )

                        if addon_price > 0:

                            st.markdown(
                                "➕ **Add On:** "
                                f"{format_rm(addon_price)}"
                            )


                # ==============================================
                # STATUS APPROVED
                # ==============================================
                with st.container(
                    border=True
                ):

                    st.success(
                        "✓ **Permohonan Diluluskan**"
                    )

                    st.markdown(
                        "Tahniah! Permohonan anda telah "
                        "diluluskan. Sila buat bayaran "
                        "dan pilih slot anda."
                    )


                # ==============================================
                # MAKLUMAT PEMBAYARAN
                # ==============================================
                with st.container(
                    border=True
                ):

                    st.caption(
                        "💳 MAKLUMAT PEMBAYARAN"
                    )

                    st.markdown(
                        "🏦 <b>Bank:</b> MAYBANK",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "👤 <b>Nama Akaun:</b> "
                        "PRINTHERO MERCHANDISE SDN. BHD.",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "🔢 <b>No. Akaun:</b> "
                        "557054621057",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "📝 <b>Remark:</b> "
                        "PFMCBS (4 digit terakhir No. Telefon)",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "📋 <b>Contoh:</b> PFMCBS1234",
                        unsafe_allow_html=True
                    )


                # ==============================================
                # NOTA PENTING
                # ==============================================
                st.warning(
                    "⚠️ **Penting:** Kalau bayaran "
                    "tidak diterima **2 hari sebelum event**, "
                    "slot anda akan dibatalkan automatik."
                )


                # ==============================================
                # UPLOAD PAYMENT PROOF
                # ==============================================
                st.link_button(
                    "📤 Upload Bukti Bayaran dan Pemilihan Slot",
                    st.secrets["event"][
                        "payment_form_url"
                    ],
                    use_container_width=True,
                    type="primary",
                )


            # ==================================================
            # CASE 3:
            # APPROVED + DAH PAID
            # ==================================================
            else:

                # ==============================================
                # STATUS CONFIRMED
                # ==============================================
                with st.container(
                    border=True
                ):

                    st.success(
                        "✓ **Permohonan Disahkan**"
                    )

                    st.markdown(
                        "Tahniah! Anda telah berjaya "
                        "mendaftar dan membuat pembayaran. "
                        "Berikut adalah maklumat slot anda:"
                    )


                # ==============================================
                # DETAIL SLOT
                #
                # Termasuk:
                # - Car Boot Sales (parking lot)
                # - F&B (F&B lot)
                # - Arts/Crafts & Others (arts lot)
                # ==============================================
                if (
                    parking_lot
                    or fnb_lot
                    or arts_lot
                ):

                    with st.container(
                        border=True
                    ):

                        st.caption(
                            "📍 MAKLUMAT SLOT ANDA"
                        )


                        # --------------------------------------
                        # PARKING LOT
                        # --------------------------------------
                        if parking_lot:

                            st.markdown(
                                f"""
                                <div style="
                                    background-color: #f7f3ee;
                                    border-radius: 10px;
                                    padding: 14px 16px;
                                    margin-bottom: 10px;
                                ">
                                    <b>🅿️ Parking Lot:</b>
                                    {parking_lot}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                        # --------------------------------------
                        # F&B LOT
                        # --------------------------------------
                        if fnb_lot:

                            st.markdown(
                                f"""
                                <div style="
                                    background-color: #f7f3ee;
                                    border-radius: 10px;
                                    padding: 14px 16px;
                                    margin-bottom: 10px;
                                ">
                                    <b>🍴 F&B Lot:</b>
                                    {fnb_lot}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                        # --------------------------------------
                        # ARTS/CRAFTS & OTHERS LOT
                        # --------------------------------------
                        if arts_lot:

                            st.markdown(
                                f"""
                                <div style="
                                    background-color: #f7f3ee;
                                    border-radius: 10px;
                                    padding: 14px 16px;
                                ">
                                    <b>🎨 Arts/Crafts & Others Lot:</b>
                                    {arts_lot}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                # ==============================================
                # EVENT INFORMATION
                # ==============================================
                with st.container(
                    border=True
                ):

                    st.markdown(
                        """
                        <h2 style="
                            margin-top: 0;
                            margin-bottom: 0.75rem;
                            font-size: 1.6rem;
                            font-weight: 700;
                        ">
                            📅 Jumpa anda pada 6-8 November 2026!
                        </h2>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        """
                        Anda diminta untuk **setup sebelum 4 petang**.

                        📌 Jangan lupa untuk **join WhatsApp Group Vendor**
                        bagi mendapatkan maklumat terkini tentang event,
                        susun atur booth, parking lot dan update penting.
                        """
                    )


                # ==============================================
                # WHATSAPP GROUP
                # ==============================================
                st.markdown(
                    "**Sertai WhatsApp Group Vendor**"
                )

                st.caption(
                    "Dapatkan maklumat terkini tentang event, "
                    "susun atur booth, parking lot, dan update penting."
                )


                st.link_button(
                    "💬 Join WhatsApp Group",
                    st.secrets["event"][
                        "whatsapp_group"
                    ],
                    use_container_width=True,
                    type="primary",
                )


                st.balloons()


        # ====================================================
        # UNKNOWN STATUS
        # ====================================================
        else:

            st.warning(
                "⚠️ Status permohonan tidak dikenali: "
                f"**{status}**. "
                "Sila hubungi admin untuk maklumat lanjut."
            )
