import streamlit as st

def render_header() -> None:
    """Renderiza o cabeçalho estilizado da aplicação."""
    st.markdown("""
<div class="main-header">
    <h1>⚡ Gerador de Memória de Cálculo</h1>
    <p>Automatize a geração de MC a partir da base Balanço Energético e Template de Destino</p>
</div>
""", unsafe_allow_html=True)
