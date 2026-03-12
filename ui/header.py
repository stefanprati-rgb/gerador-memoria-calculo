import streamlit as st

def render_header() -> None:
    """Renderiza o cabeçalho estilizado da aplicação."""
    st.markdown("""
<div class="main-header">
    <h1 style="font-size: 1.2rem; margin: 0;">⚡ Gerador de Memória de Cálculo</h1>
</div>
""", unsafe_allow_html=True)
