import time
import logging
import io
import zipfile
import streamlit as st

logger = logging.getLogger(__name__)
from typing import List, Any
from ui.state.group_state import (
    GroupState, initialize_groups, add_group,
    update_group_name, update_group_clients, clear_group_clients, 
    select_clients, update_group_periods, get_active_group
)
from ui.utils.search_utils import build_search_index, filter_values
from ui.utils.format_utils import (
    format_period_label,
    build_zip_entry_filename,
    safe_key,
    sanitize_filename,
    generate_suggested_filename,
)
from logic.services import enrichment_service
from logic.services.client_group_service import save_client_group, list_client_groups
from logic.core.mapping import (
    GROUPING_MODE_DEFAULT,
    GROUPING_MODE_DISTRIBUTOR,
    GROUPING_MODE_CNPJ,
    GROUPING_MODE_NONE,
)

def _get_wizard_group() -> GroupState:
    """O Wizard foca em apenas 1 grupo (projeto) por vez."""
    initialize_groups()
    active_group = get_active_group()
    if not active_group:
        active_group = add_group()
    return active_group

def render_groups_section_wizard(available_clients: List[str], available_periods: List[str], orch: Any) -> None:
    """Renderiza a interface guiada passo a passo (Wizard)."""
    
    # Inicia o estado do Wizard
    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 1

    group = _get_wizard_group()
    current_step = st.session_state.wizard_step

    # Controle de navegação visual
    _render_stepper(current_step)

    st.markdown("<div style='margin-top: -15px;'></div>", unsafe_allow_html=True)
    
    # Renderização Condicional baseada no passo
    if current_step == 1:
        _render_step_1_clients(group, available_clients)
    elif current_step == 2:
        _render_step_2_periods(group, available_periods)
    elif current_step == 3:
        _render_step_3_review(group, orch)

def _render_stepper(current_step: int):
    """Renderiza uma barra de progresso visual estilo Wizard."""
    cols = st.columns(3)
    steps = ["1. Clientes", "2. Períodos", "3. Gerar"]
    
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

def _render_step_1_clients(group: GroupState, available_clients: List[str]) -> None:
    """Pede apenas os clientes."""
    st.markdown(
        """
        <div class="wiz-step-hero">
            <h4>1. Selecione os clientes</h4>
            <p>Monte o escopo do projeto escolhendo os clientes que participarão da memória de cálculo. Você pode buscar rapidamente ou carregar um grupo salvo.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="wiz-step-summary">
            <span class="wiz-chip">{len(group.clients)} cliente(s) no escopo</span>
            <span class="wiz-chip">{len(available_clients)} cliente(s) disponíveis</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # --- BUSCA E CARREGAMENTO (Interface Limpa) ---
    with st.container(border=True):
        st.markdown(
            """
            <div class="wiz-search-title">Busca e atalhos</div>
            <div class="wiz-search-copy">Use a busca para montar o escopo manualmente ou carregue um grupo salvo para acelerar a operação.</div>
            """,
            unsafe_allow_html=True,
        )
        col_search, col_saved = st.columns([0.65, 0.35])
    
        with col_saved:
            try:
                saved_groups = list_client_groups()
                if saved_groups:
                    shortcut_key = f"wiz_shortcut_{group.id}"
                    reset_flag_key = f"{shortcut_key}_reset_pending"

                    # Reset seguro: só atualiza session_state antes de instanciar o widget.
                    if st.session_state.get(reset_flag_key):
                        st.session_state[shortcut_key] = "Grupos Salvos"
                        st.session_state[reset_flag_key] = False

                    selected_shortcut = st.selectbox(
                        "Carregar grupo salvo",
                        options=["Grupos Salvos"] + saved_groups,
                        index=0,
                        key=shortcut_key,
                        label_visibility="collapsed"
                    )
                    
                    if selected_shortcut != "Grupos Salvos":
                        from ui.viewmodels.wizard_viewmodel import WizardViewModel
                        sucesso = WizardViewModel.load_shortcut(group.id, selected_shortcut)
                        if sucesso:
                            st.success(f"'{selected_shortcut}' carregado.")
                            # Evita erro de mutação tardia do session_state.
                            st.session_state[reset_flag_key] = True
                            time.sleep(0.5)
                            st.rerun()
            except Exception as e:
                logger.error("Erro na interface de atalhos de grupos: %s", e)

        # 1. Área de Busca (Foco Central)
        with col_search:
            search_index = build_search_index(available_clients)
            search_term = st.text_input(
                "Buscar cliente...", 
                key=f"wiz_search_cli_{group.id}", 
                placeholder="🔎 Digite o nome da empresa...",
                label_visibility="collapsed"
            )
    
    filtered_clients = filter_values(search_term, search_index) if search_term else []
    unselected_clients = [c for c in filtered_clients if c not in group.clients]

    if search_term and unselected_clients:
        with st.container(border=True):
            st.markdown(
                """
                <div class="wiz-search-title">Resultados da busca</div>
                <div class="wiz-search-copy">Adicione clientes individualmente ou inclua todas as variações retornadas na pesquisa.</div>
                """,
                unsafe_allow_html=True,
            )
            cols_batch = st.columns([0.6, 0.4])
            with cols_batch[1]:
                if len(unselected_clients) > 1:
                    if st.button(f"Adicionar {len(unselected_clients)} variações", key=f"wiz_add_all_{group.id}", width="stretch"):
                        select_clients(group.id, group.clients + unselected_clients)
                        st.rerun()
            
            st.markdown("<div style='max-height: 180px; overflow-y: auto; padding: 5px; border: 1px solid rgba(0,0,0,0.05); border-radius: 8px;'>", unsafe_allow_html=True)
            for client in unselected_clients:
                 if st.button(f"+ {client}", key=f"wiz_add_btn_{group.id}_{safe_key(client)}", width="stretch"):
                     update_group_clients(group.id, client, True)
                     st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    elif search_term and not unselected_clients:
        st.info("Nenhum cliente novo encontrado.")

    # 2. Cesta de Selecionados (Progressive Disclosure)
    if group.clients:
        with st.container(border=True):
            st.markdown(
                """
                <div class="wiz-search-title">Escopo selecionado</div>
                <div class="wiz-search-copy">Revise os clientes adicionados, limpe o escopo ou salve a seleção como atalho para reutilizar depois.</div>
                """,
                unsafe_allow_html=True,
            )
            col_lbl, col_clr, col_save_pop = st.columns([0.5, 0.25, 0.25])
            
            with col_lbl:
                st.markdown(f"<p style='font-size: 0.9rem; margin-top: 5px;'><b>Selecionados:</b> {len(group.clients)} clientes</p>", unsafe_allow_html=True)
            
            with col_clr:
                if st.button("Limpar", key=f"wiz_btn_clear_{group.id}", width="stretch"):
                    clear_group_clients(group.id)
                    st.rerun()
            
            with col_save_pop:
                # NOVO: Popover para salvar grupo (Premium Minimalism)
                if hasattr(st, "popover"):
                    with st.popover("💾 Salvar", width="stretch"):
                        st.markdown("<p style='font-size: 0.85rem; font-weight: bold;'>Novo Grupo de Clientes</p>", unsafe_allow_html=True)
                        new_group_name = st.text_input("Nome do Grupo", key=f"wiz_new_grp_name_{group.id}", placeholder="Ex: Clientes Setor Norte...")
                        if st.button("Salvar Agora", key=f"wiz_save_grp_btn_{group.id}", type="primary", width="stretch"):
                            if new_group_name:
                                try:
                                    if save_client_group(new_group_name, group.clients):
                                        st.success(f"Salvo!")
                                        time.sleep(0.8)
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")
                            else:
                                st.warning("Digite um nome.")
                else:
                    with st.expander("💾 Salvar"):
                        new_group_name = st.text_input("Nome do Grupo", key=f"wiz_new_grp_name_{group.id}")
                        if st.button("Salvar", key=f"wiz_save_grp_btn_{group.id}"):
                            save_client_group(new_group_name, group.clients)
                            st.rerun()

            # Pills para remoção rápida
            if hasattr(st, "pills"):
                selected_to_remove = st.pills(
                    "Remover",
                    options=group.clients,
                    default=[],
                    key=f"wiz_pill_remove_{group.id}",
                    label_visibility="collapsed"
                )
                if selected_to_remove:
                    for client in selected_to_remove:
                         update_group_clients(group.id, client, False)
                    st.rerun()
            else:
                 st.markdown(f"<div style='font-size: 0.8rem; color: #555;'>{', '.join(group.clients[:10])}{'...' if len(group.clients)>10 else ''}</div>", unsafe_allow_html=True)

    # Controles de Navegação
    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    st.divider()
    _, col_next = st.columns([0.7, 0.3])
    with col_next:
        if st.button("Próximo →", type="primary", width="stretch", disabled=len(group.clients) == 0):
            if group.is_auto_name:
                suggested = generate_suggested_filename(group.name, group.clients, group.periods)
                update_group_name(group.id, suggested)
            st.session_state.wizard_step = 2
            st.rerun()

def _render_step_2_periods(group: GroupState, available_periods: List[str]) -> None:
    """Passo focado 100% em Tempo e Nome do Arquivo."""
    st.markdown(
        """
        <div class="wiz-step-hero">
            <h4>2. Defina o período</h4>
            <p>Escolha os meses que entrarão na emissão e confirme o nome final do arquivo. Esta etapa fecha o escopo temporal antes da revisão final.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="wiz-step-summary">
            <span class="wiz-chip">{len(group.clients)} cliente(s) selecionado(s)</span>
            <span class="wiz-chip">{len(group.periods)} período(s) escolhido(s)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Estilo das pílulas (Apple-like)
    st.markdown("""
        <style>
        div[data-testid="stPills"] button { border-radius: 12px !important; border: 1px solid #e0e0e0 !important; }
        div[data-testid="stPills"] button[aria-pressed="true"] { background-color: #007aff !important; border: none !important; }
        </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(
            """
            <div class="wiz-search-title">Janela de emissão</div>
            <div class="wiz-search-copy">Selecione um ou mais meses. Se houver mais de um período, a geração final será multiplexada em ZIP por referência.</div>
            """,
            unsafe_allow_html=True,
        )
        if hasattr(st, "pills"):
            new_periods = st.pills(
                "Meses",
                options=available_periods,
                default=group.periods,
                format_func=format_period_label,
                selection_mode="multi",
                key=f"wiz_pill_periods_{group.id}",
                label_visibility="collapsed"
            )
            if new_periods != group.periods:
                update_group_periods(group.id, list(new_periods))
                from ui.state.group_state import update_group_name_if_auto
                update_group_name_if_auto(group.id)
                st.rerun()
        else:
            new_periods = st.multiselect(
                "Selecione os meses", 
                options=available_periods,
                default=group.periods,
                format_func=format_period_label,
                key=f"wiz_multi_periods_{group.id}"
            )
            if new_periods != group.periods:
                update_group_periods(group.id, new_periods)
                st.rerun()

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    
    # Nome do Arquivo com foco limpo
    with st.container(border=True):
        st.markdown(
            """
            <div class="wiz-search-title">Nome do arquivo final</div>
            <div class="wiz-search-copy">Você pode manter o nome sugerido automaticamente ou definir um nome manual para a entrega.</div>
            """,
            unsafe_allow_html=True,
        )
        name_key = f"wiz_name_{group.id}"
        # Mantém o campo sincronizado com o nome automático ao alterar períodos.
        if group.is_auto_name:
            st.session_state[name_key] = group.name
        elif name_key not in st.session_state:
            st.session_state[name_key] = group.name

        new_name = st.text_input(
            "Nome do Arquivo Final",
            key=name_key,
            placeholder="Ex: Memória de Cálculo Abril 2024",
            help="Este será o nome do arquivo .xlsx gerado."
        )
        if new_name != group.name:
            from ui.state.group_state import set_custom_group_name
            set_custom_group_name(group.id, new_name)
    
    # Controles
    st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
    st.divider()
    col_back, _, col_next = st.columns([0.3, 0.4, 0.3])
    with col_back:
        if st.button("← Voltar", width="stretch"):
            st.session_state.wizard_step = 1
            st.rerun()
    with col_next:
        if st.button("Revisar →", type="primary", width="stretch", disabled=len(group.periods) == 0):
            st.session_state.wizard_step = 3
            st.rerun()

def _render_step_3_review(group: GroupState, orch: Any) -> None:
    """Passo 3 com fluxo simples: revisão, configuração essencial, avançado e geração."""
    current_sort_by = getattr(group, "sort_by", "Economia Gerada (Desc)")
    tipo_apresentacao_label = {
        "Separadores Múltiplos": "Uma aba por agrupamento",
        "Tabela Única": "Tudo em uma aba",
    }.get(group.tipo_apresentacao, group.tipo_apresentacao)

    st.markdown(
        """
        <div class="wiz-review-hero">
            <h4>3. Revisão e Geração</h4>
            <p>Revise o escopo e ajuste apenas o essencial antes de gerar o arquivo final.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    from ui.viewmodels.wizard_viewmodel import WizardViewModel
    vm = WizardViewModel(orch)
    metrics = vm.get_review_metrics(group.clients, group.periods)

    st.markdown(
        f"""
        <div class="wiz-summary-grid">
            <div class="wiz-summary-card">
                <div class="wiz-summary-label">Clientes</div>
                <div class="wiz-summary-value">{len(group.clients)}</div>
                <div class="wiz-summary-help">Escopo atual da emissão.</div>
            </div>
            <div class="wiz-summary-card">
                <div class="wiz-summary-label">Períodos</div>
                <div class="wiz-summary-value">{len(group.periods)}</div>
                <div class="wiz-summary-help">Meses que entrarão no arquivo final.</div>
            </div>
            <div class="wiz-summary-card">
                <div class="wiz-summary-label">Faturas</div>
                <div class="wiz-summary-value">{metrics.total_invoices}</div>
                <div class="wiz-summary-help">Volume estimado após aplicar os filtros selecionados.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    output_mode_label = "ZIP por período" if len(group.periods) > 1 else "Excel único"
    with st.container(border=True):
        st.markdown(
            """
            <div class="wiz-panel-title">Resumo rápido</div>
            <div class="wiz-panel-copy">Visão direta de como o arquivo será entregue.</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="wiz-chip-row">
                <span class="wiz-chip">{output_mode_label}</span>
                <span class="wiz-chip">{tipo_apresentacao_label}</span>
                <span class="wiz-chip">{'Apenas pendentes' if group.somente_pendencias else 'Todos os status'}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --- 1) Pendências ---
    incomplete_filter = "all"  # default
    with st.container(border=True):
        st.markdown(
            """
            <div class="wiz-panel-title">Pendências de cobrança</div>
            <div class="wiz-panel-copy">Defina se o arquivo deve incluir tudo ou focar apenas em itens completos/pendentes.</div>
            """,
            unsafe_allow_html=True,
        )
        if metrics.incomplete_count > 0:
            st.warning(f"{metrics.incomplete_count} faturas estão sem vencimento identificado.")
            incomplete_filter = st.selectbox(
                "Tratamento das pendências",
                options=["all", "complete_only", "incomplete_only"],
                format_func=lambda x: {
                    "all": "Manter todas as faturas",
                    "complete_only": "Apenas com vencimento",
                    "incomplete_only": "Apenas sem vencimento"
                }[x],
                key="wiz_incomplete_filter"
            )
            if hasattr(st, "popover"):
                with st.popover("Ver faturas com pendência", width="stretch"):
                    st.dataframe(metrics.incomplete_details, hide_index=True)
            else:
                with st.expander("Ver faturas com pendência"):
                    st.dataframe(metrics.incomplete_details, hide_index=True)
        else:
            st.success("Nenhuma pendência de vencimento encontrada no escopo atual.")

    from ui.state.group_state import (
        set_grouping_mode, set_include_child_rows, set_tipo_apresentacao, set_incluir_resumo, set_somente_pendencias, set_separar_auditoria, set_sort_by
    )

    # --- 2) Configuração Essencial ---
    with st.container(border=True):
        st.markdown(
            """
            <div class="wiz-panel-title">Configuração essencial</div>
            <div class="wiz-panel-copy">Ajustes principais que impactam a leitura final do relatório.</div>
            """,
            unsafe_allow_html=True,
        )
        new_grouping_mode = st.radio(
            "Agrupamento",
            options=[
                GROUPING_MODE_DEFAULT,
                GROUPING_MODE_DISTRIBUTOR,
                GROUPING_MODE_CNPJ,
                GROUPING_MODE_NONE,
            ],
            format_func=lambda x: {
                GROUPING_MODE_DEFAULT: "Padrão",
                GROUPING_MODE_DISTRIBUTOR: "Por distribuidora",
                GROUPING_MODE_CNPJ: "Por CNPJ",
                GROUPING_MODE_NONE: "Sem agrupamento",
            }[x],
            index=[
                GROUPING_MODE_DEFAULT,
                GROUPING_MODE_DISTRIBUTOR,
                GROUPING_MODE_CNPJ,
                GROUPING_MODE_NONE,
            ].index(group.grouping_mode),
            key=f"wiz_grouping_mode_{group.id}",
        )
        if new_grouping_mode != group.grouping_mode:
            set_grouping_mode(group.id, new_grouping_mode)

        new_tipo = st.radio(
            "Estrutura das abas",
            options=["Separadores Múltiplos", "Tabela Única"],
            format_func=lambda x: {
                "Separadores Múltiplos": "Uma aba por agrupamento",
                "Tabela Única": "Tudo em uma aba",
            }[x],
            index=0 if group.tipo_apresentacao == "Separadores Múltiplos" else 1,
            key=f"wiz_tipo_apres_{group.id}",
        )
        if new_tipo != group.tipo_apresentacao:
            set_tipo_apresentacao(group.id, new_tipo)

        sort_options = ["Economia Gerada (Desc)", "Razão Social", "Instalação (UC)"]
        safe_sort_value = current_sort_by if current_sort_by in sort_options else "Economia Gerada (Desc)"
        new_sort = st.selectbox(
            "Ordenação",
            options=sort_options,
            index=sort_options.index(safe_sort_value),
            key=f"wiz_sort_{group.id}",
        )
        if new_sort != current_sort_by:
            set_sort_by(group.id, new_sort)

    # --- 3) Configuração Avançada ---
    with st.expander("⚙️ Configuração avançada", expanded=False):
        col_adv_1, col_adv_2 = st.columns(2)
        with col_adv_1:
            new_include_child_rows = st.checkbox(
                "Incluir UCs filhas",
                value=group.include_child_rows,
                disabled=group.grouping_mode == GROUPING_MODE_NONE,
                help="Quando desativado, o agrupamento exibe apenas a linha consolidada do grupo.",
                key=f"wiz_include_children_{group.id}",
            )
            if group.grouping_mode == GROUPING_MODE_NONE and group.include_child_rows:
                set_include_child_rows(group.id, False)
            elif group.grouping_mode != GROUPING_MODE_NONE and new_include_child_rows != group.include_child_rows:
                set_include_child_rows(group.id, new_include_child_rows)

            new_auditoria = st.checkbox(
                "Separar abas de auditoria",
                value=group.separar_auditoria,
                key=f"wiz_auditoria_{group.id}",
                help="Itens de auditoria ficam em abas 'Aud - ...' separadas das abas financeiras."
            )
            if new_auditoria != group.separar_auditoria:
                set_separar_auditoria(group.id, new_auditoria)

        with col_adv_2:
            new_resumo = st.checkbox(
                "Incluir Resumo Executivo",
                value=group.incluir_resumo,
                key=f"wiz_resumo_{group.id}"
            )
            if new_resumo != group.incluir_resumo:
                set_incluir_resumo(group.id, new_resumo)

            new_pendencias = st.checkbox(
                "Ocultar faturas pagas",
                value=group.somente_pendencias,
                key=f"wiz_pendencias_{group.id}"
            )
            if new_pendencias != group.somente_pendencias:
                set_somente_pendencias(group.id, new_pendencias)

    # --- BOTÃO PRINCIPAL (O Caminho Feliz) ---
    with st.container(border=True):
        st.markdown(
            """
            <div class="wiz-panel-title">Geração final</div>
            <div class="wiz-panel-copy">Se estiver tudo certo, gere e baixe o arquivo nesta mesma etapa.</div>
            """,
            unsafe_allow_html=True,
        )
    if st.button("Preparar Arquivo para Download", type="primary", width="stretch", icon="✨"):
        # Enriquecimento Automático: busca TODOS os perfis de metadados registrados no sistema
        enrichment_df = None
        try:
            all_enrichment = enrichment_service.get_all_enrichment_data()
            if all_enrichment is not None and not all_enrichment.empty:
                enrichment_df = all_enrichment
                logger.info("Enriquecimento automático: %d registros carregados de todos os perfis.", len(enrichment_df))
        except Exception as enrich_err:
            logger.warning("Falha ao carregar enriquecimento automático: %s. Continuando sem enriquecimento.", enrich_err)

        start_time = time.time()
        with st.spinner("Refinando dados e construindo Excel..."):
            payload = vm.prepare_generation_payload(group, incomplete_filter, enrichment_df)
            
            if payload.is_multiplexed:
                # Geração Multiplexada: Um arquivo por referência dentro de um ZIP
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
                    for period in payload.periods:
                        period_excel = orch.generate(
                            payload.clients,
                            [period],
                            incomplete_filter=payload.incomplete_filter,
                            grouping_mode=payload.grouping_mode,
                            include_child_rows=payload.include_child_rows,
                            enrichment_df=payload.enrichment_df,
                            somente_pendencias=payload.somente_pendencias,
                            tipo_apresentacao=payload.tipo_apresentacao,
                            incluir_resumo=payload.incluir_resumo,
                            separar_auditoria=payload.separar_auditoria,
                            sort_by=payload.sort_by
                        )
                        if period_excel:
                            f_name = build_zip_entry_filename(group.name, payload.clients, period)
                            z.writestr(f_name, period_excel)
                
                final_data = zip_buffer.getvalue()
            else:
                # Geração Individual: Um único arquivo Excel
                final_data = orch.generate(
                    payload.clients, 
                    payload.periods, 
                    incomplete_filter=payload.incomplete_filter,
                    grouping_mode=payload.grouping_mode,
                    include_child_rows=payload.include_child_rows,
                    enrichment_df=payload.enrichment_df,
                    somente_pendencias=payload.somente_pendencias,
                    tipo_apresentacao=payload.tipo_apresentacao,
                    incluir_resumo=payload.incluir_resumo,
                    separar_auditoria=payload.separar_auditoria,
                    sort_by=payload.sort_by
                )
            
        elapsed = time.time() - start_time
        if final_data:
            st.toast(f"Planilha pronta em {elapsed:.1f}s!", icon="✅")
            with st.container(border=True):
                st.success(
                    f"Arquivo preparado com sucesso em {elapsed:.1f}s. "
                    f"Formato final: {'ZIP por período' if payload.is_multiplexed else 'Excel único'}."
                )
                if metrics.incomplete_count > 0:
                    if payload.incomplete_filter == "all":
                        st.warning("O arquivo foi gerado incluindo registros completos e incompletos.")
                    elif payload.incomplete_filter == "complete_only":
                        st.info("O arquivo foi gerado somente com registros completos.")
                    elif payload.incomplete_filter == "incomplete_only":
                        st.info("O arquivo foi gerado apenas com registros que exigem revisão.")
                elif group.somente_pendencias:
                    st.info("O filtro para ocultar registros pagos foi aplicado na geração.")

            st.download_button(
                label=f"📥 Baixar Arquivo {'ZIP' if payload.is_multiplexed else 'Excel'}",
                data=final_data,
                file_name=payload.filename,
                mime=payload.mime_type,
                width="stretch",
                type="primary"
            )
        else:
            st.error("Nenhum arquivo foi gerado para o escopo atual. Revise clientes, períodos e filtros aplicados.")

    # Informação técnica (somente leitura)
    st.caption("Enriquecimento de metadados: aplicado automaticamente a partir dos perfis cadastrados.")

    # Footer de Navegação
    st.divider()
    col_back, col_restart = st.columns([0.5, 0.5])
    with col_back:
        if st.button("← Ajustar Período", width="stretch"):
            st.session_state.wizard_step = 2
            st.rerun()
    with col_restart:
        if st.button("Começar de Novo", width="stretch", help="Limpa a seleção atual e volta ao primeiro passo"):
            clear_group_clients(group.id)
            update_group_periods(group.id, [])
            st.session_state.wizard_step = 1
            st.rerun()
