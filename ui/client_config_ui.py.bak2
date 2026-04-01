"""
Interface de Configuração de Clientes (Enriquecimento de Dados).
Permite carregar perfis, pesquisar UCs na base principal e mapear códigos internos.
"""
import streamlit as st
import pandas as pd
from logic.services import enrichment_service
from logic.core.mapping import ENRICHMENT_KEY, CLIENT_COLUMN
import logging

logger = logging.getLogger(__name__)

def render_client_config(orchestrator):
    """
    Interface para gerenciamento de mapeamentos de códigos internos.
    """
    st.title("⚙️ Configurações de Clientes")
    st.write("Vincule códigos internos (Centro de Custo, Unidade, Fatura Pai) às UCs encontradas na base.")
    
    # 1. Escolha do Perfil
    col1, col2 = st.columns([3, 1])
    with col1:
        # Tenta carregar perfis existentes para um selectbox ou permite novo nome
        profiles = enrichment_service.list_profiles()
        profile_suggestion = profiles[0] if profiles else "Perfil_Novo"
        
        active_profile = st.text_input(
            "Nome do Perfil de Configuração (ex: Embracon)", 
            value=st.session_state.get("active_profile", ""),
            placeholder="Digite o nome para criar ou carregar..."
        )
        
        if profiles:
            selected_existing = st.selectbox("Ou selecione um perfil existente", [""] + profiles, index=0)
            if selected_existing:
                active_profile = selected_existing
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True) # Espaçamento
        if st.button("🚀 Carregar Perfil", use_container_width=True, type="primary"):
            if active_profile:
                st.session_state.active_profile = active_profile
                st.session_state.mapping_df = enrichment_service.load_mapping(active_profile)
                if st.session_state.mapping_df is None:
                     # Se não existe, inicia vazio com as colunas obrigatórias
                     st.session_state.mapping_df = pd.DataFrame(columns=[ENRICHMENT_KEY, CLIENT_COLUMN])
                st.success(f"Perfil '{active_profile}' ativo.")
            else:
                st.error("Informe um nome para o perfil.")

    if not st.session_state.get("active_profile"):
        st.info("💡 Informe um nome de perfil (ex: 'Embracon') e clique em Carregar para iniciar a configuração.")
        return

    active_profile = st.session_state.active_profile
    
    # 2. Busca de UCs na base principal
    st.markdown("---")
    st.markdown(f"### 🔍 Buscar UCs na Base Consolidada")
    st.caption("Pesquise por nome do parceiro para importar as UCs para este perfil.")
    
    col_search, col_add = st.columns([3, 1])
    with col_search:
        search_term = st.text_input("Pesquisar por Razão Social (ex: Embracon Admin)", "")
    
    # Obter todas as UCs via orchestrator
    all_ucs_df = orchestrator.get_all_ucs_with_names()
    
    # Preparar o mapeamento atual no estado
    if "mapping_df" not in st.session_state or st.session_state.mapping_df is None:
         st.session_state.mapping_df = pd.DataFrame(columns=[ENRICHMENT_KEY, CLIENT_COLUMN])

    current_mapping = st.session_state.mapping_df.copy()

    if search_term:
        filtered_ucs = all_ucs_df[all_ucs_df[CLIENT_COLUMN].str.contains(search_term, case=False, na=False)].copy()
        
        if not filtered_ucs.empty:
            st.info(f"Encontradas {len(filtered_ucs)} UCs para o termo '{search_term}'.")
            with col_add:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("📥 Importar UCs", use_container_width=True):
                    # Unir evitando duplicatas
                    new_entries = filtered_ucs[~filtered_ucs[ENRICHMENT_KEY].isin(current_mapping[ENRICHMENT_KEY])]
                    if not new_entries.empty:
                        # Adicionar preservando colunas que já existem no mapping
                        current_mapping = pd.concat([current_mapping, new_entries], ignore_index=True)
                        st.session_state.mapping_df = current_mapping
                        st.success(f"{len(new_entries)} novas UCs importadas.")
                        st.rerun()
                    else:
                        st.warning("Todas essas UCs já estão no mapeamento.")
        else:
            st.warning("Nenhuma UC localizada com este nome.")

    # 3. Editor de Mapeamento
    st.markdown("---")
    st.markdown(f"### 📋 Configurando Perfil: **{active_profile}**")
    
    st.info("💡 Dica: Você pode copiar células do Excel e colar diretamente na tabela abaixo.")
    
    # Botão para adicionar novas colunas
    col_new_col, col_btn_col = st.columns([3, 1])
    with col_new_col:
        new_col_name = st.text_input("Adicionar nova coluna (Ex: Centro de Custo, Unidade)", key="new_col_input")
    with col_btn_col:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Adicionar Coluna", use_container_width=True):
            if new_col_name and new_col_name not in current_mapping.columns:
                current_mapping[new_col_name] = pd.NA
                st.session_state.mapping_df = current_mapping
                st.success(f"Coluna '{new_col_name}' adicionada.")
                st.rerun()

    # Excluir linhas selecionadas (st.data_editor permite mas vamos dar um feedback)
    st.caption("Selecione e apague linhas se necessário (Del / Backspace).")
    
    edited_df = st.data_editor(
        current_mapping,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            ENRICHMENT_KEY: st.column_config.TextColumn("No. UC (Identificador)", disabled=True),
            CLIENT_COLUMN: st.column_config.TextColumn("Razão Social (Base)", disabled=True),
        },
        key=f"editor_{active_profile}"
    )

    # 4. Ação de Salvar e Excluir
    st.markdown("---")
    col_save, col_del_area = st.columns([0.7, 0.3])
    
    with col_save:
        if st.button("💾 Salvar Configuração de Enriquecimento", type="primary", use_container_width=True):
            if enrichment_service.save_mapping(active_profile, edited_df):
                st.session_state.mapping_df = edited_df
                st.success(f"✅ Configuração do perfil '{active_profile}' salva com sucesso!")
            else:
                st.error("Erro ao salvar o arquivo de mapeamento.")

    with col_del_area:
        with st.expander("🗑️ Excluir Perfil", expanded=False):
            st.warning(f"Isso apagará o perfil '{active_profile}' da Nuvem e do Local.")
            confirm = st.checkbox("Confirmo a exclusão", key=f"del_confirm_{active_profile}")
            if st.button("🔴 Excluir Definitivamente", disabled=not confirm, use_container_width=True):
                if enrichment_service.delete_profile(active_profile):
                    st.success(f"Perfil '{active_profile}' removido com sucesso.")
                    # Limpar o estado para forçar o recarregamento
                    del st.session_state["active_profile"]
                    del st.session_state["mapping_df"]
                    st.rerun()
                else:
                    st.error("Erro interno ao tentar excluir o perfil.")

    # Listagem de outros perfis na lateral? Ou apenas aqui no config.
