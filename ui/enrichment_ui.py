import streamlit as st
import pandas as pd
import time
from io import BytesIO
from logic.services import enrichment_service
from logic.core.mapping import ENRICHMENT_KEY, CLIENT_COLUMN
import logging

logger = logging.getLogger(__name__)

def render_enrichment_wizard(orchestrator):
    """
    Interface para o Enriquecimento de Dados.
    Agora refatorada para usar Abas (Batch Import vs Gestão de Base).
    """
    st.title("Gestão de Enriquecimento")
    
    tab1, tab2 = st.tabs(["📥 Importar em Lote", "🗄️ Gerenciar Base"])
    
    with tab1:
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

    with tab2:
        _render_tab_manage_base()

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
    st.write("Forneça os arquivos que precisam ser enriquecidos com códigos internos (Ex: Balanço, Gestão de Cobrança).")
    
    if "balanco_df" not in st.session_state:
        st.session_state.balanco_df = None
    if "cobranca_df" not in st.session_state:
        st.session_state.cobranca_df = None
        
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.markdown("##### Balanço Operacional")
            if st.session_state.balanco_df is not None:
                st.success("Arquivo carregado e pronto.")
                if st.button("Substituir Balanço", key="replace_balanco"):
                    st.session_state.balanco_df = None
                    st.rerun()
            else:
                file_balanco = st.file_uploader("Upload Balanço (.xlsx, .csv)", type=["csv", "xlsx"], key="up_bal", label_visibility="collapsed")
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
                st.success("Arquivo carregado e pronto.")
                if st.button("Substituir Gestão de Cobrança", key="replace_cobranca"):
                    st.session_state.cobranca_df = None
                    st.rerun()
            else:
                file_cobranca = st.file_uploader("Upload Gestão (.xlsx, .csv)", type=["csv", "xlsx"], key="up_cob", label_visibility="collapsed")
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
        can_advance = (st.session_state.balanco_df is not None) or (st.session_state.cobranca_df is not None)
        if st.button("Próximo", type="primary", width='stretch', disabled=not can_advance):
            st.session_state.enrichment_step = 2
            st.rerun()

def _render_step_2_config(orchestrator):
    st.markdown("<h4 style='margin-bottom: 0;'>2. Configuração e Perfil</h4>", unsafe_allow_html=True)
    st.write("Vincule códigos internos às UCs usando a base central no Firestore.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        profiles = enrichment_service.list_profiles()
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
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Carregar Perfil", width='stretch', type="primary", icon="⚙️"):
            if active_profile:
                st.session_state.active_profile = active_profile
                profile_result = enrichment_service.load_mapping(active_profile)
                
                # Se for dict (auto-bootstrap) ou nulo
                if profile_result is None or isinstance(profile_result, dict):
                     st.session_state.mapping_df = pd.DataFrame(columns=[ENRICHMENT_KEY, CLIENT_COLUMN])
                else:
                     st.session_state.mapping_df = profile_result
                st.success(f"Perfil '{active_profile}' ativo.")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Informe um nome para o perfil.")

    if not st.session_state.get("active_profile"):
        st.info("Informe um nome de perfil (ex: 'Embracon') e clique em Carregar para iniciar a configuração.")
        st.divider()
        col_back, _ = st.columns([0.3, 0.7])
        with col_back:
            if st.button("Anterior", width='stretch'):
                st.session_state.enrichment_step = 1
                st.rerun()
        return

    active_profile = st.session_state.active_profile
    if "mapping_df" not in st.session_state or st.session_state.mapping_df is None:
        st.session_state.mapping_df = pd.DataFrame(columns=[ENRICHMENT_KEY, CLIENT_COLUMN])
    current_mapping = st.session_state.mapping_df.copy()
    
    st.markdown("---")
    
    # Busca de UCs
    with st.expander("Importar UCs da Base Consolidada"):
        col_search, col_add = st.columns([3, 1])
        with col_search:
            search_term = st.text_input("Pesquisar por Razão Social", "")
        
        all_ucs_df = orchestrator.get_all_ucs_with_names()
        
        if search_term:
            filtered_ucs = all_ucs_df[all_ucs_df[CLIENT_COLUMN].str.contains(search_term, case=False, na=False)].copy()
            if not filtered_ucs.empty:
                st.info(f"Encontradas {len(filtered_ucs)} UCs para o termo '{search_term}'.")
                with col_add:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Importar UCs", width='stretch', icon="📥"):
                        new_entries = filtered_ucs[~filtered_ucs[ENRICHMENT_KEY].isin(current_mapping[ENRICHMENT_KEY])]
                        if not new_entries.empty:
                            current_mapping = pd.concat([current_mapping, new_entries], ignore_index=True)
                            st.session_state.mapping_df = current_mapping
                            st.success(f"{len(new_entries)} novas UCs importadas.")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.warning("Todas essas UCs já estão no mapeamento.")
            else:
                st.warning("Nenhuma UC localizada.")

    st.markdown(f"### Mapeamento: **{active_profile}**")
    
    col_new_col, col_btn_col = st.columns([3, 1])
    with col_new_col:
        new_col_name = st.text_input("Adicionar nova coluna (Ex: Centro de Custo)", key="new_col_input")
    with col_btn_col:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Adicionar Coluna", width='stretch', icon="➕"):
            if new_col_name and new_col_name not in current_mapping.columns:
                current_mapping[new_col_name] = pd.NA
                st.session_state.mapping_df = current_mapping
                st.success(f"Coluna '{new_col_name}' adicionada.")
                st.rerun()

    edited_df = st.data_editor(
        current_mapping,
        num_rows="dynamic",
        width='stretch',
        hide_index=True,
        column_config={
            ENRICHMENT_KEY: st.column_config.TextColumn("No. UC (Identificador)", disabled=False),
            CLIENT_COLUMN: st.column_config.TextColumn("Nome Cliente", disabled=False),
        },
        key=f"editor_{active_profile}"
    )
    
    col_save, _ = st.columns([0.4, 0.6])
    with col_save:
        if st.button("Salvar e Automatizar", width='stretch', type="primary", icon="💾"):
            if enrichment_service.save_mapping(active_profile, edited_df):
                st.session_state.mapping_df = edited_df
                st.success(f"Perfil '{active_profile}' salvo com sucesso.")
            else:
                st.error("Erro ao salvar perfil.")

    st.divider()
    col_back, _, col_next = st.columns([0.3, 0.4, 0.3])
    with col_back:
        if st.button("Anterior", width='stretch'):
            st.session_state.enrichment_step = 1
            st.rerun()
    with col_next:
        if st.button("Próximo", type="primary", width='stretch'):
            # Save implicitly on next if desired, but user already hit save button manually. 
            # We'll just carry forward the modified mapping
            st.session_state.mapping_df = edited_df
            st.session_state.enrichment_step = 3
            st.rerun()

def _render_step_3_processing():
    st.markdown("<h4 style='margin-bottom: 0;'>3. Processamento e Resultado</h4>", unsafe_allow_html=True)
    st.write("Aplica as configurações sobre os arquivos e realiza o cruzamento de informações.")
    
    mapping_df = st.session_state.get("mapping_df")
    active_profile = st.session_state.get("active_profile")
    
    if mapping_df is None or mapping_df.empty:
        st.warning("Nenhum mapeamento de regras válido encontrado. Retorne ao Passo 2.")
        return
        
    st.info(f"Aplicando Perfil: {active_profile}. Total de Regras: {len(mapping_df)}")
    
    balanco_df = st.session_state.get("balanco_df")
    cobranca_df = st.session_state.get("cobranca_df")
    
    if st.button("Processar Arquivos", width='stretch', type="primary", icon="⚙️"):
        with st.spinner("Processando..."):
            result_df = None
            logs = []
            
            # 1. Sanitização Rigorosa de Chaves
            def sanitize_key(df, col):
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                return df
                
            map_clean = mapping_df.copy()
            map_clean = sanitize_key(map_clean, ENRICHMENT_KEY)
            map_clean = map_clean.drop_duplicates(subset=[ENRICHMENT_KEY], keep="last")
            if CLIENT_COLUMN in map_clean.columns:
                 map_clean = map_clean.drop(columns=[CLIENT_COLUMN])
                 
            # 2. Processamento Principal (Prevenção de Explosão)
            if balanco_df is not None:
                balanco_clean = balanco_df.copy()
                balanco_clean = sanitize_key(balanco_clean, ENRICHMENT_KEY)
                
                if cobranca_df is not None:
                    cobranca_clean = cobranca_df.copy()
                    cobranca_clean = sanitize_key(cobranca_clean, ENRICHMENT_KEY)
                    
                    if "Referencia" in cobranca_clean.columns:
                        cobranca_clean["Referencia"] = cobranca_clean["Referencia"].astype(str).str.strip()
                    if "Referencia" in balanco_clean.columns:
                        balanco_clean["Referencia"] = balanco_clean["Referencia"].astype(str).str.strip()

                    # Drop de duplicatas para evitar linhas fantasmas no Balanço Operacional
                    if "Referencia" in cobranca_clean.columns:
                        before_count = len(cobranca_clean)
                        cobranca_clean = cobranca_clean.drop_duplicates(subset=[ENRICHMENT_KEY, "Referencia"], keep="last")
                        dropped = before_count - len(cobranca_clean)
                        if dropped > 0:
                            logger.info(f"Removidas {dropped} duplicatas na Gestão de Cobrança (prevenção de ghost rows).")
                            logs.append(f"Sanitização: {dropped} duplicatas removidas da Gestão.")

                    merge_keys = [ENRICHMENT_KEY]
                    if "Referencia" in balanco_clean.columns and "Referencia" in cobranca_clean.columns:
                         merge_keys.append("Referencia")
                         
                    # 3. Merge com Indicador de Qualidade
                    merged = balanco_clean.merge(cobranca_clean, on=merge_keys, how="left", indicator=True)
                    
                    found_in_gestao = merged['_merge'] == 'both'
                    pct = (found_in_gestao.sum() / len(merged)) * 100 if len(merged) > 0 else 0
                    logs.append(f"Resumo Técnico: {pct:.1f}% das faturas do Balanço Operacional foram encontradas na Gestão de Cobrança.")
                    logger.info("Merge B.O vs Gestão concluído. Match Rate: %.1f%%", pct)
                    
                    merged = merged.drop(columns=['_merge'])
                    result_df = merged.merge(map_clean, on=ENRICHMENT_KEY, how="left")
                else:
                    result_df = balanco_clean.merge(map_clean, on=ENRICHMENT_KEY, how="left")
            elif cobranca_df is not None:
                cobranca_clean = cobranca_df.copy()
                cobranca_clean = sanitize_key(cobranca_clean, ENRICHMENT_KEY)
                result_df = cobranca_clean.merge(map_clean, on=ENRICHMENT_KEY, how="left")
                
            # Finalização
            if result_df is not None:
                # 4. Faxina Visual Final: sóbrio, sem emojis de festa.
                st.success("Processamento concluído.")
                for msg in logs:
                    st.info(msg)
                    
                output = BytesIO()
                result_df.to_excel(output, index=False)
                output.seek(0)
                
                st.download_button(
                    label="Baixar Arquivo",
                    icon="💾",
                    data=output,
                    file_name=f"Arquivos_Enriquecidos_{active_profile}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width='stretch',
                    type="primary"
                )
            else:
                st.error("Nenhuma base providenciada no upload original.")

    st.divider()
    col_back, _, col_restart = st.columns([0.3, 0.4, 0.3])
    with col_back:
        if st.button("Anterior", width='stretch'):
            st.session_state.enrichment_step = 2
            st.rerun()
    with col_restart:
        if st.button("Novo Processo", width='stretch'):
            st.session_state.enrichment_step = 1
            st.session_state.balanco_df = None
            st.session_state.cobranca_df = None
            st.session_state.mapping_df = None
            st.session_state.active_profile = ""
            st.rerun()

def _render_tab_manage_base():
    """
    Renderiza a Tab 2: Gerenciar Base.
    Busca dados consolidados da service e permite edição/exclusão.
    """
    st.markdown("#### 🗄️ Base Consolidada de UCs Enriquecidas")
    st.write("Visualize, edite ou remova UCs da base central do Firestore. Útil para encerramento de contratos.")
    
    base_df = enrichment_service.get_all_enrichment_data()
    
    if base_df.empty:
        st.info("A base de enriquecimento (uc_enrichment) está vazia.")
    else:
        # Garantir No. UC na primeira coluna
        cols = [ENRICHMENT_KEY] + [c for c in base_df.columns if c != ENRICHMENT_KEY]
        base_df = base_df[cols]
        
        st.markdown("---")
        
        edited_df = st.data_editor(
            base_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="enrichment_batch_editor",
            column_config={
                ENRICHMENT_KEY: st.column_config.TextColumn(f"Identificador ({ENRICHMENT_KEY})", disabled=True),
            },
            disabled=[ENRICHMENT_KEY]
        )
        
        if st.button("💾 Salvar Alterações na Base", type="primary", use_container_width=True):
            changes = st.session_state.get("enrichment_batch_editor", {})
            
            has_changes = False
            
            # 1. Processar Deleções
            deleted_indices = changes.get("deleted_rows", [])
            if deleted_indices:
                ucs_to_delete = base_df.iloc[deleted_indices][ENRICHMENT_KEY].astype(str).tolist()
                if enrichment_service.delete_enrichment_data(ucs_to_delete):
                    has_changes = True
            
            # 2. Processar Edições e Adições
            edited_rows_raw = changes.get("edited_rows", {}) # {index: {col: val}}
            added_rows = changes.get("added_rows", [])
            
            rows_to_save = []
            
            # Edições
            for idx_str, mods in edited_rows_raw.items():
                idx = int(idx_str)
                # Pegar a linha completa do edited_df (que já contém as modificações)
                row_full = edited_df.iloc[idx].to_dict()
                rows_to_save.append(row_full)
                
            # Adições (Note: No. UC estará vazio se desabilitado, o que é um problema)
            for row in added_rows:
                if ENRICHMENT_KEY in row and str(row[ENRICHMENT_KEY]).strip():
                    rows_to_save.append(row)
                else:
                    st.warning("Uma nova linha foi ignorada por estar sem 'No. UC'.")

            if rows_to_save:
                df_to_save = pd.DataFrame(rows_to_save)
                if enrichment_service.save_enrichment_data(df_to_save):
                    has_changes = True
            
            if has_changes:
                st.toast("Base atualizada com sucesso!", icon="✅")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Nenhuma alteração detectada para salvar.")
