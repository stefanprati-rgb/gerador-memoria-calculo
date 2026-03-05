"""
Painel administrativo para sincronização de bases.
Extraído de app.py para manter separação de responsabilidades.
"""
import time
import streamlit as st

from config.settings import settings
from logic.services.sync_service import build_consolidated_cache_from_uploads
from logic.adapters.firebase_adapter import FirebaseAdapter


def render_admin_panel():
    """Renderiza o painel admin na sidebar para upload e sincronização de bases."""
    with st.sidebar.expander("⚙️ Atualizar Bases (Admin)", expanded=False):
        admin_senha = st.text_input("Senha Admin", type="password")
        if admin_senha == settings.admin_password:
            st.markdown("**1. Carregue as planilhas atualizadas:**")
            balanco_up = st.file_uploader("Balanço Energético (.xlsm)", type=["xlsm", "xlsx"])
            gestao_up = st.file_uploader("Gestão Cobrança (.xlsx)", type=["xlsx"])
            
            if st.button("Sincronizar e Processar", use_container_width=True):
                if balanco_up:
                    with st.spinner("Processando e cruzando dados. Isso pode levar alguns minutos..."):
                        # Tentar inicializar Firebase para backup (opcional)
                        fb = None
                        try:
                            fb = FirebaseAdapter(settings.firebase_credentials_path, settings.firebase_storage_bucket)
                            if fb._app is None:
                                fb = None
                        except Exception:
                            fb = None
                        
                        # Processar localmente (Local First) + backup opcional no Firebase
                        gestao_bytes = gestao_up.getvalue() if gestao_up else None
                        if build_consolidated_cache_from_uploads(balanco_up.getvalue(), gestao_bytes, fb):
                            st.cache_resource.clear()
                            st.success("✅ Bases processadas com sucesso!")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("Erro interno ao gerar o cache consolidado. Verifique os logs.")
                else:
                    st.warning("⚠️ O Balanço Energético (.xlsm) é obrigatório. A Gestão Cobrança (.xlsx) é opcional.")
