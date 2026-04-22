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

    /* Home operacional */
    .ops-hero {
        background:
            radial-gradient(circle at top right, rgba(0, 180, 216, 0.18), transparent 32%),
            linear-gradient(135deg, rgba(15, 76, 117, 0.98) 0%, rgba(18, 103, 130, 0.96) 55%, rgba(0, 180, 216, 0.92) 100%);
        color: #f7fbfd;
        border-radius: 18px;
        padding: 1.4rem 1.5rem 1.2rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 14px 28px rgba(15, 76, 117, 0.18);
        overflow: hidden;
    }
    .ops-hero h2 {
        margin: 0 0 0.35rem 0;
        font-size: 1.7rem;
        letter-spacing: -0.03em;
    }
    .ops-hero p {
        margin: 0;
        max-width: 720px;
        line-height: 1.45;
        opacity: 0.92;
        font-size: 0.98rem;
    }
    .ops-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.8rem;
        margin: 0.9rem 0 1.2rem 0;
    }
    .ops-card {
        border-radius: 16px;
        padding: 1rem 1rem 0.9rem 1rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(248,251,252,0.98) 100%);
        border: 1px solid rgba(16, 76, 117, 0.08);
        box-shadow: 0 8px 20px rgba(12, 37, 53, 0.06);
        min-height: 136px;
    }
    .ops-card[data-state="ready"] {
        border-top: 4px solid #1f8a70;
    }
    .ops-card[data-state="warn"] {
        border-top: 4px solid #d98e04;
    }
    .ops-card[data-state="idle"] {
        border-top: 4px solid #6c7a89;
    }
    .ops-label {
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 0.68;
        margin-bottom: 0.35rem;
        font-weight: 600;
    }
    .ops-value {
        font-size: 1.55rem;
        line-height: 1.05;
        margin-bottom: 0.45rem;
        font-weight: 700;
        color: #11384a;
    }
    .ops-help {
        font-size: 0.86rem;
        line-height: 1.4;
        color: rgba(17, 56, 74, 0.76);
    }
    .ops-section-title {
        margin: 1.1rem 0 0.45rem 0;
        font-size: 1.02rem;
        font-weight: 700;
        color: #153b4b;
        letter-spacing: -0.01em;
    }
    .ops-panel {
        border-radius: 18px;
        padding: 1rem 1.05rem;
        background: linear-gradient(180deg, rgba(250,252,253,0.98) 0%, rgba(245,248,250,0.95) 100%);
        border: 1px solid rgba(16, 76, 117, 0.08);
    }
    .ops-kicker {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        color: #0f6f88;
        margin-bottom: 0.35rem;
    }
    .ops-summary {
        font-size: 1.02rem;
        line-height: 1.5;
        color: #153b4b;
    }
    @media (max-width: 900px) {
        .ops-strip {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    /* Revisão do wizard */
    .wiz-review-hero {
        background:
            linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(244,249,251,0.96) 100%);
        border: 1px solid rgba(16, 76, 117, 0.08);
        border-radius: 18px;
        padding: 1.2rem 1.25rem;
        box-shadow: 0 10px 22px rgba(12, 37, 53, 0.05);
        margin-bottom: 0.9rem;
    }
    .wiz-review-hero h4 {
        margin: 0 0 0.25rem 0;
        font-size: 1.2rem;
        letter-spacing: -0.02em;
        color: #153b4b;
    }
    .wiz-review-hero p {
        margin: 0;
        color: rgba(21, 59, 75, 0.78);
        line-height: 1.45;
    }
    .wiz-summary-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.8rem;
        margin: 0.8rem 0 1rem 0;
    }
    .wiz-summary-card {
        border-radius: 16px;
        padding: 0.95rem 1rem;
        background: linear-gradient(180deg, rgba(250,252,253,0.98) 0%, rgba(245,248,250,0.96) 100%);
        border: 1px solid rgba(16, 76, 117, 0.08);
    }
    .wiz-summary-label {
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        color: rgba(21, 59, 75, 0.62);
        margin-bottom: 0.35rem;
    }
    .wiz-summary-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #153b4b;
        line-height: 1.05;
        margin-bottom: 0.25rem;
    }
    .wiz-summary-help {
        font-size: 0.86rem;
        color: rgba(21, 59, 75, 0.74);
    }
    .wiz-panel {
        border-radius: 18px;
        padding: 1rem 1.05rem;
        background: linear-gradient(180deg, rgba(250,252,253,0.98) 0%, rgba(245,248,250,0.95) 100%);
        border: 1px solid rgba(16, 76, 117, 0.08);
        margin-bottom: 0.9rem;
    }
    .wiz-panel-title {
        font-size: 1rem;
        font-weight: 700;
        color: #153b4b;
        margin-bottom: 0.25rem;
        letter-spacing: -0.01em;
    }
    .wiz-panel-copy {
        color: rgba(21, 59, 75, 0.78);
        line-height: 1.45;
        margin-bottom: 0.8rem;
    }
    .wiz-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.65rem;
    }
    .wiz-chip {
        display: inline-block;
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        background: rgba(0, 180, 216, 0.1);
        color: #0f6f88;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .wiz-step-hero {
        background: linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(244,249,251,0.96) 100%);
        border: 1px solid rgba(16, 76, 117, 0.08);
        border-radius: 18px;
        padding: 1.15rem 1.25rem;
        box-shadow: 0 10px 22px rgba(12, 37, 53, 0.05);
        margin-bottom: 0.9rem;
    }
    .wiz-step-hero h4 {
        margin: 0 0 0.25rem 0;
        font-size: 1.18rem;
        letter-spacing: -0.02em;
        color: #153b4b;
    }
    .wiz-step-hero p {
        margin: 0;
        color: rgba(21, 59, 75, 0.78);
        line-height: 1.45;
    }
    .wiz-step-summary {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin: 0.8rem 0 0.1rem 0;
    }
    .wiz-step-summary .wiz-chip {
        background: rgba(15, 76, 117, 0.08);
        color: #15546d;
    }
    .wiz-search-shell {
        border-radius: 18px;
        padding: 0.95rem 1rem;
        background: linear-gradient(180deg, rgba(250,252,253,0.98) 0%, rgba(245,248,250,0.95) 100%);
        border: 1px solid rgba(16, 76, 117, 0.08);
        margin-bottom: 0.9rem;
    }
    .wiz-search-title {
        font-size: 0.98rem;
        font-weight: 700;
        color: #153b4b;
        margin-bottom: 0.2rem;
    }
    .wiz-search-copy {
        color: rgba(21, 59, 75, 0.76);
        line-height: 1.42;
        margin-bottom: 0.7rem;
        font-size: 0.92rem;
    }
    @media (max-width: 900px) {
        .wiz-summary-grid {
            grid-template-columns: 1fr;
        }
    }
</style>
"""


def inject_styles():
    """Injeta o CSS customizado na página Streamlit."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
