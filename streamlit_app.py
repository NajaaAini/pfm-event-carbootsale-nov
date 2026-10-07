import streamlit as st
from style import apply_style
import base64
from pathlib import Path

st.set_page_config(
    page_title="PFM Car Boot Sale Portal",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_style()


# ============================================================
# SIDEBAR — BRANDED HEADER + LOGIN
# ============================================================
def _image_base64(image_path):
    path = Path(image_path)
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


with st.sidebar:

    # --- Brand header dengan icon PFM ---
    logo_b64 = _image_base64("assets/icon.jpg")

    if logo_b64:
        st.markdown(f"""
        <div style="
            text-align: center;
            padding: 1.25rem 0.5rem 1.25rem 0.5rem;
            border-bottom: 1px solid #e8dcc7;
            margin-bottom: 1.5rem;
        ">
            <img src="data:image/jpeg;base64,{logo_b64}" style="
                width: 90px;
                height: 90px;
                object-fit: contain;
                margin-bottom: 0.75rem;
                border-radius: 12px;
            ">
            <h3 style="
                color: #292524 !important;
                margin: 0;
                font-size: 1rem;
                font-weight: 700;
                letter-spacing: 1px;
            ">PFM CAR BOOT SALE</h3>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="
            text-align: center;
            padding: 1.25rem 0.5rem 1.25rem 0.5rem;
            border-bottom: 1px solid #e8dcc7;
            margin-bottom: 1.5rem;
        ">
            <div style="
                width: 56px;
                height: 56px;
                background-color: #f2ebe0;
                border-radius: 12px;
                margin: 0 auto 0.75rem auto;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.75rem;
            ">🎪</div>
            <h3 style="
                color: #292524 !important;
                margin: 0;
                font-size: 1rem;
                font-weight: 700;
                letter-spacing: 1px;
            ">PFM CAR BOOT SALE</h3>
        </div>
        """, unsafe_allow_html=True)

    # --- Log Masuk ---
    st.markdown("### 🔐 Admin Access")

    if not st.session_state.get("is_admin", False):
        pwd = st.text_input(
            "Kata Laluan",
            type="password",
            key="sidebar_pwd",
            placeholder="Masukkan kata laluan"
        )
        if st.button("Log Masuk", type="primary"):
            if pwd == st.secrets["admin"]["password"]:
                st.session_state.is_admin = True
                st.session_state.admin_name = "Admin"
                st.rerun()
            else:
                st.error("❌ Kata laluan salah")
    else:
        if st.button("Log Keluar"):
            st.session_state.is_admin = False
            st.session_state.admin_name = "Admin"
            st.rerun()


# ============================================================
# PAGES
# ============================================================
public_page = st.Page("public_page.py", title="Check Status", default=True)
admin_page = st.Page("admin_page.py", title="Admin Panel")

pages = [public_page]
if st.session_state.get("is_admin", False):
    pages.append(admin_page)

pg = st.navigation(pages)
pg.run()
