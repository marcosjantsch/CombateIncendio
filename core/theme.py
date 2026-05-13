import streamlit as st


def apply_locked_light_theme() -> None:
    st.markdown(
        """
        <style>
        footer {visibility: hidden !important;}

        html, body, [class*="css"] {
            color-scheme: light !important;
        }

        #MainMenu {
            visibility: visible !important;
        }

        header[data-testid="stHeader"],
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"],
        div[data-testid="stStatusWidget"],
        button[kind="header"] {
            visibility: visible !important;
            display: flex !important;
        }

        .stApp {
            background-color: #FFFFFF !important;
            color: #111111 !important;
        }

        header[data-testid="stHeader"] {
            background: rgba(244, 247, 250, 0.92) !important;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(22, 41, 63, 0.10) !important;
        }

        div[data-testid="stToolbar"] button,
        button[kind="header"] {
            color: #24415f !important;
        }

        section[data-testid="stSidebar"] {
            color: #eaf4fb !important;
        }

        section[data-testid="stSidebar"] * {
            color: inherit !important;
        }

        .stMarkdown, .stText, .stCaption, .stCode, .stAlert, .stDataFrame, .stTable {
            color: #111111 !important;
        }

        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        div[data-baseweb="textarea"] > div,
        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea,
        .stSelectbox div,
        .stMultiSelect div {
            background-color: #FFFFFF !important;
            color: #111111 !important;
        }

        .stButton > button,
        .stDownloadButton > button,
        .stFormSubmitButton > button {
            background-color: #FFFFFF !important;
            color: #111111 !important;
            border: 1px solid #C9D5E3 !important;
        }

        button[data-baseweb="tab"] {
            color: #111111 !important;
        }

        details, summary {
            background-color: #FFFFFF !important;
            color: #111111 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
