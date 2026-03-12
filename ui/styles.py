"""
CSS customizado para a aplicação Streamlit.
Extraído de app.py para manter separação de responsabilidades.
"""
import streamlit as st

CUSTOM_CSS = """
<style>
    /* Importar fonte Inter do Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Reset geral de tipografia */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Cabeçalho principal estilizado */
    .main-header {
        background: linear-gradient(135deg, #0f4c75 0%, #1b7fa3 50%, #00b4d8 100%);
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        margin-bottom: 0.8rem;
        color: white;
        box-shadow: 0 4px 15px rgba(15, 76, 117, 0.2);
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    .main-header p {
        margin: 0.4rem 0 0 0;
        opacity: 0.85;
        font-size: 0.95rem;
        font-weight: 300;
    }

    /* Sidebar refinada - Adaptável ao tema */
    section[data-testid="stSidebar"] {
        background-color: var(--secondary-background-color);
        background-image: linear-gradient(180deg, var(--secondary-background-color) 0%, var(--background-color) 100%);
    }
    section[data-testid="stSidebar"] .stMetric {
        background: var(--background-color);
        padding: 0.7rem 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        border-left: 3px solid #1b7fa3;
    }

    /* Botão principal — gradiente verde/azul (mantido para destaque) */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0f4c75 0%, #00b4d8 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        letter-spacing: 0.02em;
        padding: 0.7rem 1.5rem !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 14px rgba(0, 180, 216, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(0, 180, 216, 0.45) !important;
        transform: translateY(-1px);
    }

    /* Badge de status dos grupos */
    .group-badge-ready {
        display: inline-block;
        background: #d4edda;
        color: #155724;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 500;
    }
    .group-badge-incomplete {
        display: inline-block;
        background: #fff3cd;
        color: #856404;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 500;
    }

    /* Preview de registros */
    .record-preview {
        font-size: 0.82rem;
        color: var(--text-color);
        opacity: 0.8;
        padding: 0.3rem 0;
        font-weight: 400;
    }
    .record-preview strong {
        color: #00b4d8;
        font-weight: 600;
    }

    /* Botão adicionar grupo */
    div.stButton > button:not([kind="primary"]) {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }

    /* Separador suave */
    hr {
        border: none;
        border-top: 1px solid var(--secondary-background-color);
        margin: 1.2rem 0;
        opacity: 0.3;
    }
</style>
"""


def inject_styles():
    """Injeta o CSS customizado na página Streamlit."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
