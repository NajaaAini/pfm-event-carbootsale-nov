import streamlit as st


def apply_style():
    st.markdown("""
    <style>
    /* ========================================================= */
    /* === HIDE STREAMLIT DEFAULT (kecuali toggle button) === */
    /* ========================================================= */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stToolbar"] {visibility: hidden;}
    [data-testid="stDecoration"] {display: none;}

    /* Header jangan hide sepenuhnya — Streamlit letak toggle button kat sini */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: auto !important;
    }
    header[data-testid="stHeader"] button,
    header[data-testid="stHeader"] [data-testid="stSidebarCollapsedControl"],
    header[data-testid="stHeader"] [data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        display: flex !important;
        opacity: 1 !important;
    }

    /* ========================================================= */
    /* === MAIN BACKGROUND === */
    /* ========================================================= */
    .stApp {
        background-color: #faf7f2;
    }

    /* ========================================================= */
    /* === SIDEBAR — DEFAULT OPEN, BOLEH TOGGLE === */
    /* ========================================================= */
    [data-testid="stSidebar"] {
        background-color: #f2ebe0;
        border-right: 1px solid #e8dcc7;
        min-width: 260px !important;
        width: 260px !important;
    }

    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: #44403c !important;
    }
    [data-testid="stSidebar"] input {
        color: #44403c !important;
        background-color: #ffffff !important;
        border-radius: 8px;
        border: 1px solid #d6d3d1;
    }

    /* === SIDEBAR BUTTONS === */
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] .stButton > button[kind="primary"],
    [data-testid="stSidebar"] .stButton > button[kind="secondary"],
    [data-testid="stSidebar"] button[data-testid="baseButton-primary"],
    [data-testid="stSidebar"] button[data-testid="baseButton-secondary"] {
        background-color: #78350f !important;
        color: #ffffff !important;
        border: 1px solid #78350f !important;
        width: 100%;
        border-radius: 8px;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }
    [data-testid="stSidebar"] .stButton > button p,
    [data-testid="stSidebar"] .stButton > button span,
    [data-testid="stSidebar"] .stButton > button div,
    [data-testid="stSidebar"] .stButton > button * {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #92400e !important;
        border-color: #92400e !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover p,
    [data-testid="stSidebar"] .stButton > button:hover span,
    [data-testid="stSidebar"] .stButton > button:hover div,
    [data-testid="stSidebar"] .stButton > button:hover * {
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] [data-testid="stAlert"] {
        background-color: #e8dcc7 !important;
        border-radius: 8px;
        border: 1px solid #d6c4a3;
    }
    [data-testid="stSidebar"] [data-testid="stAlert"] p {
        color: #44403c !important;
    }

    /* === SIDEBAR NAVIGATION === */
    [data-testid="stSidebarNav"] {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    [data-testid="stSidebarNav"] > ul {
        padding-left: 0 !important;
    }
    [data-testid="stSidebarNav"] li {
        margin-bottom: 0.4rem;
    }
    [data-testid="stSidebarNav"] a {
        color: #57534e !important;
        border-radius: 10px;
        padding: 0.7rem 1rem !important;
        margin: 0.15rem 0;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        border: 1px solid transparent;
        background-color: transparent;
        transition: all 0.15s ease !important;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    [data-testid="stSidebarNav"] a:hover {
        background-color: #e8dcc7 !important;
        border-color: #d6c4a3 !important;
        color: #78350f !important;
        transform: translateX(3px);
        box-shadow: 0 2px 6px rgba(120, 53, 15, 0.08);
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background-color: #78350f !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-color: #78350f !important;
        box-shadow: 0 3px 8px rgba(120, 53, 15, 0.2);
    }
    [data-testid="stSidebarNav"] a[aria-current="page"]:hover {
        background-color: #92400e !important;
        border-color: #92400e !important;
        color: #ffffff !important;
        transform: translateX(3px);
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] span,
    [data-testid="stSidebarNav"] a[aria-current="page"] * {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* ========================================================= */
    /* === FORCE SHOW "OPEN SIDEBAR" BUTTON (bila collapse) === */
    /* ========================================================= */
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"] > button,
    [data-testid="collapsedControl"] > button {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        z-index: 999999 !important;
        background-color: #78350f !important;
        color: #ffffff !important;
        border-radius: 50% !important;
        width: 44px !important;
        height: 44px !important;
        min-width: 44px !important;
        min-height: 44px !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 12px rgba(120, 53, 15, 0.4) !important;
        position: fixed !important;
        top: 1rem !important;
        left: 1rem !important;
    }

    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="collapsedControl"] svg {
        fill: #ffffff !important;
        color: #ffffff !important;
        width: 20px !important;
        height: 20px !important;
    }

    [data-testid="stSidebarCollapsedControl"]:hover,
    [data-testid="collapsedControl"]:hover {
        background-color: #92400e !important;
        transform: scale(1.05) !important;
        box-shadow: 0 6px 16px rgba(120, 53, 15, 0.5) !important;
    }

    /* Extra selectors untuk Streamlit versi berbeza */
    button[data-testid="baseButton-header"],
    button[data-testid="baseButton-headerNoPadding"],
    header button[kind="header"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        z-index: 999999 !important;
    }

    /* ========================================================= */
    /* === ADMIN NAVIGATION BUTTONS (di atas page) === */
    /* ========================================================= */

    /* Button tak aktif */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        background-color: #ffffff !important;
        border: 1px solid #e8dcc7 !important;
        color: #57534e !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        border-radius: 10px !important;
        padding: 0.55rem 0.5rem !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 1px 2px rgba(120, 53, 15, 0.04) !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        background-color: #f2ebe0 !important;
        border-color: #d6c4a3 !important;
        color: #78350f !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 3px 8px rgba(120, 53, 15, 0.12) !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] p,
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] span,
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] * {
        color: #57534e !important;
        font-weight: 600 !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover p,
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover span,
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover * {
        color: #78350f !important;
    }

    /* Button aktif (primary) */
    div[data-testid="stHorizontalBlock"] button[kind="primary"] {
        background-color: #78350f !important;
        border: 1px solid #78350f !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        border-radius: 10px !important;
        padding: 0.55rem 0.5rem !important;
        box-shadow: 0 3px 8px rgba(120, 53, 15, 0.2) !important;
        transition: all 0.15s ease !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="primary"]:hover {
        background-color: #92400e !important;
        border-color: #92400e !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 10px rgba(120, 53, 15, 0.3) !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="primary"] p,
    div[data-testid="stHorizontalBlock"] button[kind="primary"] span,
    div[data-testid="stHorizontalBlock"] button[kind="primary"] * {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* ========================================================= */
    /* === MAIN AREA — TEXT COLOR === */
    /* ========================================================= */
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    section.main,
    .main {
        color: #44403c !important;
        background-color: #faf7f2 !important;
    }

    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] span,
    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] li,
    [data-testid="stMain"] p,
    [data-testid="stMain"] span,
    [data-testid="stMain"] label {
        color: #44403c !important;
    }

    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3,
    [data-testid="stAppViewContainer"] h4 {
        color: #292524 !important;
    }

    [data-testid="stAppViewContainer"] .stMarkdown,
    [data-testid="stAppViewContainer"] .stMarkdown p,
    [data-testid="stAppViewContainer"] .stMarkdown span {
        color: #44403c !important;
    }

    [data-testid="stAppViewContainer"] [data-testid="stText"],
    [data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] {
        color: #44403c !important;
    }

    [data-testid="stAppViewContainer"] [data-testid="stAlert"] p,
    [data-testid="stAppViewContainer"] [data-testid="stAlert"] span,
    [data-testid="stAppViewContainer"] [data-testid="stAlert"] div {
        color: #44403c !important;
    }

    [data-testid="stAppViewContainer"] input,
    [data-testid="stAppViewContainer"] textarea {
        color: #44403c !important;
    }

    [data-testid="stAppViewContainer"] input::placeholder,
    [data-testid="stAppViewContainer"] textarea::placeholder {
        color: #a8a29e !important;
    }

    [data-testid="stAppViewContainer"] code,
    [data-testid="stAppViewContainer"] pre {
        color: #44403c !important;
    }

    /* ========================================================= */
    /* === TITLES === */
    /* ========================================================= */
    h1 {
        font-weight: 600;
        color: #44403c;
        font-size: 1.75rem;
        margin-bottom: 0.5rem;
        padding-bottom: 0.5rem;
        border: none;
    }
    h2 {
        font-weight: 600;
        color: #44403c;
        font-size: 1.3rem;
        border: none;
    }
    h3 {
        font-weight: 600;
        color: #57534e;
        font-size: 1rem;
    }

    /* ========================================================= */
    /* === METRIC CARDS === */
    /* ========================================================= */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 1.25rem;
        border-radius: 12px;
        border: 1px solid #f0e6d6;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(120, 53, 15, 0.08);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        color: #78716c;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
        color: #78350f;
        font-weight: 600;
    }

    /* ========================================================= */
    /* === BUTTONS (MAIN AREA) === */
    /* ========================================================= */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        padding: 0.4rem 1.2rem;
        border: 1px solid #d6d3d1;
        background-color: #ffffff;
        color: #44403c;
        transition: transform 0.15s ease, box-shadow 0.15s ease,
                    background-color 0.15s ease, border-color 0.15s ease !important;
    }
    .stButton > button:hover {
        background-color: #faf7f2;
        border-color: #a8a29e;
        color: #292524;
        transform: translateY(-1px);
        box-shadow: 0 2px 6px rgba(120, 53, 15, 0.15);
    }
    .stButton > button:active {
        transform: translateY(0);
        box-shadow: none;
    }

    /* === PRIMARY BUTTON === */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button,
    button[kind="primaryFormSubmit"],
    button[data-testid="baseButton-primaryFormSubmit"],
    button[data-testid="baseButton-primary"] {
        background-color: #78350f !important;
        border: 1px solid #78350f !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="primary"] p,
    .stButton > button[kind="primary"] span,
    .stButton > button[kind="primary"] *,
    .stFormSubmitButton > button p,
    .stFormSubmitButton > button span,
    .stFormSubmitButton > button *,
    button[kind="primaryFormSubmit"] *,
    button[data-testid="baseButton-primaryFormSubmit"] *,
    button[data-testid="baseButton-primary"] * {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button:hover,
    button[kind="primaryFormSubmit"]:hover,
    button[data-testid="baseButton-primaryFormSubmit"]:hover,
    button[data-testid="baseButton-primary"]:hover {
        background-color: #92400e !important;
        border-color: #92400e !important;
        color: #ffffff !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(120, 53, 15, 0.25);
    }

    /* ========================================================= */
    /* === LINK BUTTON === */
    /* ========================================================= */
    [data-testid="stLinkButton"] > a,
    a[data-testid="stLinkButton"],
    .stLinkButton > a,
    [data-testid="stLinkButton"] a {
        background-color: #78350f !important;
        border: 1px solid #78350f !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        text-decoration: none !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease,
                    background-color 0.15s ease !important;
    }
    [data-testid="stLinkButton"] > a:hover,
    a[data-testid="stLinkButton"]:hover,
    .stLinkButton > a:hover,
    [data-testid="stLinkButton"] a:hover {
        background-color: #92400e !important;
        border-color: #92400e !important;
        color: #ffffff !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(120, 53, 15, 0.25);
    }
    [data-testid="stLinkButton"] > a p,
    [data-testid="stLinkButton"] > a span,
    [data-testid="stLinkButton"] > a *,
    .stLinkButton > a p,
    .stLinkButton > a span,
    .stLinkButton > a * {
        color: #ffffff !important;
        font-weight: 600 !important;
        text-decoration: none !important;
    }

    /* ========================================================= */
    /* === DATAFRAME === */
    /* ========================================================= */
    [data-testid="stDataFrame"] {
        border: 1px solid #f0e6d6;
        border-radius: 12px;
        overflow: hidden;
        transition: box-shadow 0.2s ease;
    }
    [data-testid="stDataFrame"]:hover {
        box-shadow: 0 2px 8px rgba(120, 53, 15, 0.06);
    }

    /* ========================================================= */
    /* === TEXT INPUTS === */
    /* ========================================================= */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 1px solid #d6d3d1;
        padding: 0.6rem 0.9rem;
        background-color: #ffffff;
        color: #44403c !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #78350f;
        box-shadow: 0 0 0 2px #f0e6d6;
    }

    /* ========================================================= */
    /* === FORMS === */
    /* ========================================================= */
    [data-testid="stForm"] {
        border: 1px solid #f0e6d6;
        border-radius: 12px;
        padding: 1.5rem;
        background-color: #ffffff;
        transition: box-shadow 0.2s ease;
    }

    /* ========================================================= */
    /* === EXPANDER === */
    /* ========================================================= */
    [data-testid="stExpander"] {
        border: 1px solid #f0e6d6;
        border-radius: 12px;
        background-color: #ffffff;
        transition: box-shadow 0.2s ease;
    }
    [data-testid="stExpander"]:hover {
        box-shadow: 0 2px 8px rgba(120, 53, 15, 0.06);
    }

    /* ========================================================= */
    /* === DIVIDER === */
    /* ========================================================= */
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 1px solid #f0e6d6;
    }

    /* ========================================================= */
    /* === ALERTS === */
    /* ========================================================= */
    [data-testid="stAlert"] {
        border-radius: 12px;
        border-width: 1px;
    }

    /* ========================================================= */
    /* === SELECTBOX === */
    /* ========================================================= */
    .stSelectbox > div > div {
        border-radius: 8px;
        border: 1px solid #d6d3d1;
    }

    /* ========================================================= */
    /* === CHECKBOX === */
    /* ========================================================= */
    [data-testid="stCheckbox"] label span {
        color: #44403c !important;
    }

    /* ========================================================= */
    /* === RADIO === */
    /* ========================================================= */
    [data-testid="stRadio"] label span {
        color: #44403c !important;
    }

    /* ========================================================= */
    /* === FILE UPLOADER === */
    /* ========================================================= */
    [data-testid="stFileUploader"] {
        border-radius: 12px;
    }
    [data-testid="stFileUploader"] button {
        background-color: #78350f !important;
        color: #ffffff !important;
        border: none !important;
    }
    [data-testid="stFileUploader"] button * {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* ========================================================= */
    /* === PROGRESS BAR === */
    /* ========================================================= */
    .stProgress > div > div > div > div {
        background-color: #78350f !important;
    }
    </style>
    """, unsafe_allow_html=True)
