import streamlit as st
import pandas as pd
import time
from io import BytesIO
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
    Refatorada para interface Metadata-First: Foco no cadastro de unidades.
    """
    st.title("Sistema de Enriquecimento de Dados")
    
    tab1, tab2 = st.tabs(["🗄️ Cadastro de Metadados (Fixos)", "🧮 Auditoria e Cruzamento (Mensal)"])
    
    with tab1:
        _render_tab_metadata_registration(orchestrator)
        
    with tab2:
        st.info("💡 Esta aba serve para realizar o cruzamento mensal de faturas contra balanços. Para cadastrar dados permanentemente, use a aba Cadastro.")
        
        if "enrichment_step" not in st.session_state:
            st.session_state.enrichment_step = 1

        current_step = st.session_state.enrichment_step

        _render_stepper(current_step)
        st.markdown("<div style='margin-top: -15px;'></div>", unsafe_allow_html=True)
        
        if current_step == 1:
            _render_step_1_upload()
        elif current_step == 2:
            _render_step_2_config(orchestrator)
        elif current_step == 3:
            _render_step_3_processing()

def _render_tab_metadata_registration(orchestrator):
    """
    Aba principal de cadastro fixo de UCs e dados mestres (ex: Embracon).
    """
    st.markdown("#### 🗄️ Gestão de Metadados e Cadastro Fixo")
    st.write("Mantenha aqui os dados permanentes de suas UCs. Estes dados são usados automaticamente na geração das memórias de cálculo.")

    # 1. Seletor de Perfil
    profiles = enrichment_service.list_profiles()
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
                st.success(f"Perfil '{active_profile}' carregado.")
                time.sleep(0.5)
                st.rerun()

    if not st.session_state.get("active_profile"):
        st.info("Selecione ou crie um perfil para gerenciar os metadados.")
        return

    profile_name = st.session_state.active_profile
    
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
                        st.error(f"Coluna de Identificação (No. UC) não encontrada. Colunas disponíveis: {list(new_df.columns)}")
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
                            st.success(f"Planilha processada! {len(new_df)} registros registrados no perfil '{profile_name}'.")
                            time.sleep(1)
                            st.rerun()
                except Exception as e:
                    st.error(f"Erro ao processar planilha: {e}")
            else:
                st.warning("Selecione um arquivo primeiro.")

    # 3. Editor de Metadados
    st.markdown(f"---")
    st.markdown(f"##### Editor de Metadados: **{profile_name}**")
    
    current_mapping = st.session_state.get("mapping_df", pd.DataFrame(columns=[ENRICHMENT_KEY, CLIENT_COLUMN]))
    
    # Forçar colunas críticas para string para evitar erro de ColumnDataKind.FLOAT
    cols_to_fix = [ENRICHMENT_KEY, CLIENT_COLUMN, ACCOUNT_NUMBER_COL]
    for col in cols_to_fix:
        if col in current_mapping.columns:
            # Converter para string e limpar representações de nulos (nan, <NA>, etc)
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
            st.success("Alterações salvas com sucesso.")
            time.sleep(0.5)
            st.rerun()

def _render_stepper(current_step: int):
    """Renderiza uma barra de progresso visual estilo Wizard."""
    cols = st.columns(3)
    steps = ["1. Upload", "2. Configuração", "3. Resultado"]
    
    for i, col in enumerate(cols):
        step_num = i + 1
        color = "#00b4d8" if current_step == step_num else ("#4CAF50" if current_step > step_num else "#e0e0e0")
        weight = "bold" if current_step == step_num else "normal"
        
        with col:
            st.markdown(f"""
                <div style='text-align: center; border-bottom: 3px solid {color}; padding-bottom: 5px;'>
                    <span style='color: {color}; font-weight: {weight}; font-size: 0.9rem;'>{steps[i]}</span>
                </div>
            """, unsafe_allow_html=True)

def _render_step_1_upload():
    st.markdown("<h4 style='margin-bottom: 0;'>1. Upload de Arquivos</h4>", unsafe_allow_html=True)
    st.write("Forneça os arquivos que precisam ser enriquecidos com códigos internos.")
    
    if "balanco_df" not in st.session_state:
        st.session_state.balanco_df = None
    if "cobranca_df" not in st.session_state:
        st.session_state.cobranca_df = None
        
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.markdown("##### Balanço Operacional")
            if st.session_state.balanco_df is not None:
                st.success("Arquivo carregado.")
                if st.button("Substituir Balanço", key="replace_balanco"):
                    st.session_state.balanco_df = None
                    st.rerun()
            else:
                file_balanco = st.file_uploader("Upload Balanço", type=["csv", "xlsx"], key="up_bal", label_visibility="collapsed")
                if file_balanco:
                    try:
                        if file_balanco.name.endswith(".csv"):
                            st.session_state.balanco_df = pd.read_csv(file_balanco, sep=";", encoding="utf-8-sig")
                        else:
                            st.session_state.balanco_df = pd.read_excel(file_balanco)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")

    with col2:
        with st.container(border=True):
            st.markdown("##### Gestão de Cobrança")
            if st.session_state.cobranca_df is not None:
                st.success("Arquivo carregado.")
                if st.button("Substituir Gestão", key="replace_cobranca"):
                    st.session_state.cobranca_df = None
                    st.rerun()
            else:
                file_cobranca = st.file_uploader("Upload Gestão", type=["csv", "xlsx"], key="up_cob", label_visibility="collapsed")
                if file_cobranca:
                    try:
                        if file_cobranca.name.endswith(".csv"):
                            st.session_state.cobranca_df = pd.read_csv(file_cobranca, sep=";", encoding="utf-8-sig")
                        else:
                            st.session_state.cobranca_df = pd.read_excel(file_cobranca)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")

    st.divider()
    _, col_next = st.columns([0.7, 0.3])
    with col_next:
        if st.button("Próximo", type="primary", width='stretch'):
            st.session_state.enrichment_step = 2
            st.rerun()

def _render_step_2_config(orchestrator):
    st.markdown("<h4 style='margin-bottom: 0;'>2. Perfil de Metadados</h4>", unsafe_allow_html=True)
    st.write("Selecione o perfil que será usado para o cruzamento.")
    
    profiles = enrichment_service.list_profiles()
    active_profile = st.session_state.get("active_profile", "")
    
    selected_existing = st.selectbox("Selecione o perfil existente", [""] + profiles, index=profiles.index(active_profile)+1 if active_profile in profiles else 0)
    
    if st.button("Confirmar Perfil", type="primary", use_container_width=True):
        if selected_existing:
            st.session_state.active_profile = selected_existing
            profile_result = enrichment_service.load_mapping(selected_existing)
            if profile_result is not None and not isinstance(profile_result, dict):
                 st.session_state.mapping_df = profile_result
            st.success(f"Perfil '{selected_existing}' selecionado.")
            time.sleep(0.5)
            st.rerun()

    st.divider()
    col_back, _, col_next = st.columns([0.3, 0.4, 0.3])
    with col_back:
        if st.button("Anterior", width='stretch'):
            st.session_state.enrichment_step = 1
            st.rerun()
    with col_next:
        if st.button("Próximo", type="primary", width='stretch'):
            st.session_state.enrichment_step = 3
            st.rerun()

def _render_step_3_processing():
    st.markdown("<h4 style='margin-bottom: 0;'>3. Processamento e Resultado</h4>", unsafe_allow_html=True)
    
    mapping_df = st.session_state.get("mapping_df")
    active_profile = st.session_state.get("active_profile")
    
    if mapping_df is None or mapping_df.empty:
        st.warning("Nenhum perfil carregado. Retorne ao Passo 2.")
        return
        
    st.info(f"Aplicando Perfil: {active_profile}")
    
    if st.button("Processar Arquivos", width='stretch', type="primary", icon="⚙️"):
        with st.spinner("Processando..."):
            balanco_df = st.session_state.get("balanco_df")
            cobranca_df = st.session_state.get("cobranca_df")
            
            result_df = None
            
            def sanitize_key(df, col):
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                return df
                
            map_clean = mapping_df.copy()
            map_clean = sanitize_key(map_clean, ENRICHMENT_KEY)
            map_clean = map_clean.drop_duplicates(subset=[ENRICHMENT_KEY], keep="last")
            if CLIENT_COLUMN in map_clean.columns:
                 map_clean = map_clean.drop(columns=[CLIENT_COLUMN])
                 
            if balanco_df is not None:
                balanco_clean = balanco_df.copy()
                balanco_clean = sanitize_key(balanco_clean, ENRICHMENT_KEY)
                
                if cobranca_df is not None:
                    cobranca_clean = cobranca_df.copy()
                    cobranca_clean = sanitize_key(cobranca_clean, ENRICHMENT_KEY)
                    
                    merge_keys = [ENRICHMENT_KEY]
                    if "Referencia" in balanco_clean.columns and "Referencia" in cobranca_clean.columns:
                         merge_keys.append("Referencia")
                         
                    merged = balanco_clean.merge(cobranca_clean, on=merge_keys, how="left")
                    result_df = merged.merge(map_clean, on=ENRICHMENT_KEY, how="left")
                else:
                    result_df = balanco_clean.merge(map_clean, on=ENRICHMENT_KEY, how="left")
            
            if result_df is not None:
                st.success("Concluído!")
                output = BytesIO()
                result_df.to_excel(output, index=False)
                output.seek(0)
                
                st.download_button(
                    label="Baixar Resultado",
                    icon="💾",
                    data=output,
                    file_name=f"Resultado_{active_profile}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )

    st.divider()
    col_back, _, col_restart = st.columns([0.3, 0.4, 0.3])
    with col_back:
        if st.button("Anterior", width='stretch'):
            st.session_state.enrichment_step = 2
            st.rerun()
    with col_restart:
        if st.button("Novo Processo", width='stretch'):
            st.session_state.enrichment_step = 1
            st.rerun()

def _render_tab_manage_base():
    """DEPRECATED - Metadados agora gerenciados por perfil na Tab 1"""
    pass
