import streamlit as st
from typing import List
from ui.utils.format_utils import format_number

def render_sidebar_metrics(available_clients: List[str], available_periods: List[str], total_records: int) -> None:
    """Renderiza as métricas com totais numéricos na barra lateral."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Resumo da Base")
    
    col_m1, col_m2 = st.sidebar.columns(2)
    col_m1.metric("Clientes", format_number(len(available_clients)))
    col_m2.metric("Períodos", format_number(len(available_periods)))
    
    st.sidebar.metric("Registros Totais", format_number(total_records))
