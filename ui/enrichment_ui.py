import streamlit as st
import pandas as pd
import time
from logic.services import enrichment_service
from logic.core.mapping import ENRICHMENT_KEY, CLIENT_COLUMN, ACCOUNT_NUMBER_COL
import logging

@st.cache_data(ttl=60, show_spinner=False)
def _get_cached_enrichment_data():
    """Busca dados de enriquecimento com cache de 60s."""
    return enrichment_service.get_all_enrichment_data()

logger = logging.getLogger(__name__)

def render_enrichment_wizard(orchestrator):
    """
    Interface para o Enriquecimento de Dados.
    Foco exclusivo no cadastro de metadados fixos por perfil (Firebase).
    """
    st.markdown(
        """
        <div class="wiz-step-hero">
            <h4>Enriquecimento de Dados</h4>
            <p>Use esta área para manter metadados permanentes das UCs. Esses dados entram automaticamente na geração das memórias de cálculo quando estiverem disponíveis.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Seletor de Perfil
    profiles = enrichment_service.list_profiles()
    with st.container(border=True):
        st.markdown(
            """
            <div class="wiz-search-title">Perfil de metadados</div>
            <div class="wiz-search-copy">Abra um perfil existente ou informe um nome novo para iniciar um cadastro limpo.</div>
            """,
            unsafe_allow_html=True,
        )
        col_p1, col_p2 = st.columns([3, 1])

        with col_p1:
            active_profile = st.text_input(
                "Nome do Perfil de Metadados (ex: Embracon)",
                value=st.session_state.get("active_profile", ""),
                placeholder="Digite para criar ou selecione abaixo..."
            )
            if profiles:
                selected_existing = st.selectbox("Perfis Salvos", [""] + profiles, index=0)
                if selected_existing:
                    st.session_state.active_profile = selected_existing
                    active_profile = selected_existing

        with col_p2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Carregar Dados", use_container_width=True, type="primary", icon="📁"):
                if active_profile:
                    st.session_state.active_profile = active_profile
                    profile_result = enrichment_service.load_mapping(active_profile)
                    if profile_result is None or isinstance(profile_result, dict):
                        st.session_state.mapping_df = pd.DataFrame(columns=[ENRICHMENT_KEY, CLIENT_COLUMN])
                    else:
                        st.session_state.mapping_df = profile_result
                    st.success(f"Perfil '{active_profile}' carregado e pronto para edição.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.warning("Informe ou selecione um perfil antes de carregar os dados.")

    if not st.session_state.get("active_profile"):
        st.info("Selecione ou crie um perfil para começar a gerenciar os metadados.")
        return

    profile_name = st.session_state.active_profile
    current_mapping = st.session_state.get("mapping_df", pd.DataFrame(columns=[ENRICHMENT_KEY, CLIENT_COLUMN]))

    st.markdown(
        f"""
        <div class="wiz-step-summary">
            <span class="wiz-chip">Perfil ativo: {profile_name}</span>
            <span class="wiz-chip">{len(current_mapping)} registro(s) em memória</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Carga Rápida (Importação em Massa)
    with st.expander("📥 Importação em Massa (Excel/CSV)", expanded=False):
        uploaded_file = st.file_uploader("Upload de Planilha de Metadados", type=["xlsx", "csv"], key="bulk_upload")
        replace_all = st.checkbox("⚠️ Substituir todos os dados existentes deste perfil?", value=False, help="Se marcado, limpa o cadastro atual do perfil antes de subir o novo arquivo.")

        if st.button("💾 Salvar Planilha na Memória do Sistema", type="primary", use_container_width=True, icon="🚀"):
            if uploaded_file:
                try:
                    # Carregar arquivo
                    if uploaded_file.name.endswith(".csv"):
                        new_df = pd.read_csv(uploaded_file, sep=";", encoding="utf-8-sig")
                    else:
                        new_df = pd.read_excel(uploaded_file)

                    # Normalizar colunas
                    new_df.columns = new_df.columns.str.strip()

                    # Identificar colunas vitais
                    possible_uc_cols = [ENRICHMENT_KEY, "Instalação", "UC", "Nº UC"]
                    uc_col_found = next((c for c in possible_uc_cols if c in new_df.columns), None)

                    if not uc_col_found:
                        st.error("A planilha enviada não possui uma coluna de identificação de UC reconhecida.")
                        st.caption(f"Colunas encontradas: {list(new_df.columns)}")
                    else:
                        # Rename para o padrão interno
                        if uc_col_found != ENRICHMENT_KEY:
                            new_df.rename(columns={uc_col_found: ENRICHMENT_KEY}, inplace=True)

                        # Sanitização e Casting para String
                        new_df[ENRICHMENT_KEY] = new_df[ENRICHMENT_KEY].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                        if ACCOUNT_NUMBER_COL in new_df.columns:
                            new_df[ACCOUNT_NUMBER_COL] = new_df[ACCOUNT_NUMBER_COL].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

                        # Lógica de Substituição vs Upsert
                        if replace_all:
                            final_df = new_df
                        else:
                            current_df = st.session_state.get("mapping_df", pd.DataFrame(columns=[ENRICHMENT_KEY]))
                            final_df = pd.concat([current_df, new_df], ignore_index=True)
                            final_df = final_df.drop_duplicates(subset=[ENRICHMENT_KEY], keep="last")

                        # Salvar no Firebase
                        if enrichment_service.save_mapping(profile_name, final_df):
                            st.session_state.mapping_df = final_df
                            action_text = "substituídos" if replace_all else "incorporados"
                            st.success(
                                f"Importação concluída. {len(new_df)} registro(s) foram {action_text} no perfil '{profile_name}'."
                            )
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("A importação foi lida, mas não foi possível persistir os dados do perfil.")
                except Exception as e:
                    st.error("Falha ao processar a planilha de metadados.")
                    st.caption(str(e))
            else:
                st.warning("Selecione uma planilha antes de iniciar a importação.")

    # 3. Editor de Metadados
    st.markdown(f"---")
    st.markdown(f"##### Editor de Metadados: **{profile_name}**")

    # Forçar colunas críticas para string para evitar erro de ColumnDataKind.FLOAT
    cols_to_fix = [ENRICHMENT_KEY, CLIENT_COLUMN, ACCOUNT_NUMBER_COL]
    for col in cols_to_fix:
        if col in current_mapping.columns:
            current_mapping[col] = current_mapping[col].astype(str).replace(["nan", "None", "NaN", "<NA>", "nat", "NaT"], "")

    edited_df = st.data_editor(
        current_mapping,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            ENRICHMENT_KEY: st.column_config.TextColumn("No. UC (ID)", disabled=False, required=True),
            ACCOUNT_NUMBER_COL: st.column_config.TextColumn("Número da Conta", disabled=False),
            CLIENT_COLUMN: st.column_config.TextColumn("Razão Social", disabled=False),
        },
        key=f"editor_meta_{profile_name}"
    )

    if st.button("💾 Salvar Alterações Manuais", type="primary", use_container_width=True, icon="✅"):
        if enrichment_service.save_mapping(profile_name, edited_df):
            st.session_state.mapping_df = edited_df
            st.success("Alterações manuais salvas com sucesso.")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Não foi possível salvar as alterações manuais deste perfil.")
