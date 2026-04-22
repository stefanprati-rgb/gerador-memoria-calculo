"""
Painel administrativo para sincronização de bases.
Extraído de app.py para manter separação de responsabilidades.
"""
import time
import streamlit as st

from config.settings import settings, ConfigurationError
from logic.services.sync_service import (
    build_consolidated_cache_from_uploads, 
    build_consolidated_cache_from_local_network,
    get_pendencias
)
from logic.adapters.firebase_adapter import FirebaseAdapter, FirebaseAdapterError
import os
import pandas as pd

from ui.utils.notifications import notify_completion


def render_admin_panel():
    """Renderiza o painel admin na sidebar para upload e sincronização de bases."""
    with st.sidebar.expander("Atualizar Bases (Admin)", expanded=False):
        admin_senha = st.text_input("Senha Admin", type="password")
        if admin_senha == settings.admin_password:
            from ui.viewmodels.admin_viewmodel import AdminViewModel
            
            vm = AdminViewModel(mode="development")
            state = vm.get_state()
            
            if state.fatal_error:
                st.error(f"🔒 {state.fatal_error}")
                return
                
            if state.warning_message:
                st.warning(f"⚠️ {state.warning_message}")

            # === FEATURE: Sincronização Local Rápida ===
            if state.can_sync_local and state.local_path:
                st.markdown("---")
                st.markdown("**Sincronização Automática**")
                st.info("O Balanço Energético foi encontrado no caminho configurado.")
                
                if st.button("Atualizar Bases Diretamente", width='stretch', type="primary", icon="⬇️"):
                    with st.spinner("Puxando arquivo ultrarrápido da rede local..."):
                        success, _ = build_consolidated_cache_from_local_network(state.local_path)
                        if success:
                            st.success("Base sincronizada da rede com sucesso.")
                            notify_completion("Base sincronizada da rede.")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("Falha ao gerar o cache local a partir da rede. Verifique logs do sistema.")

            # === FEATURE: Sincronização Manual / Nuvem ===
            st.markdown("---")
            st.markdown("**Sincronização via Upload**")
            balanco_up = st.file_uploader("Balanço Energético (.xlsm)", type=["xlsm", "xlsx"])
            gestao_up = st.file_uploader("Gestão Cobrança (.xlsx)", type=["xlsx"])
            
            can_sync = balanco_up is not None and gestao_up is not None
            
            if not can_sync:
                st.caption("Carregue ambas as planilhas para backup e atualização manual.")

            if st.button("Sincronizar e Processar", width='stretch', disabled=not can_sync, icon="⚙️"):
                with st.spinner("Processando e cruzando dados. Isso pode levar alguns minutos..."):
                    if state.firebase_warning:
                        st.warning(state.firebase_warning)
                    
                    success = vm.process_uploads(balanco_up.getvalue(), gestao_up.getvalue(), state)
                    
                    if success:
                        st.success("Bases processadas com sucesso.")
                        notify_completion("Bases processadas e arquivos cruzados.")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Erro interno ao gerar o cache consolidado. Verifique os logs.")

            # === FEATURE: Relatório de Pendências ===
            st.markdown("---")
            st.subheader("Pendências de Dados")
            report = get_pendencias()
            
            if report is None:
                st.info("Nenhuma sincronização realizada ainda.")
            else:
                total = report.get("total_ucs_sem_vencimento", 0)
                if total == 0:
                    st.success("Todos os dados estão completos.")
                else:
                    st.warning(f"Detectadas {total} faturas sem Vencimento.")
                    
                    df_pend = pd.DataFrame(report["pendencias"])
                    if not df_pend.empty:
                        # Ordenar por tipo depois por referencia
                        df_pend = df_pend.sort_values(by=["tipo", "referencia"])
                        st.dataframe(
                            df_pend[["no_uc", "razao_social", "referencia", "tipo"]],
                            hide_index=True,
                            width='stretch'
                        )
                
                # Exibir data da verificação
                try:
                    dt_gen = pd.to_datetime(report["gerado_em"]).strftime("%d/%m/%Y às %H:%M")
                    st.caption(f"Última verificação: {dt_gen}")
                except:
                    pass
