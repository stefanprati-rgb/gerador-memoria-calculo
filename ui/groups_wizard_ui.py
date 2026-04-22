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
from ui.utils.format_utils import format_period_label, safe_key, sanitize_filename, generate_suggested_filename
from logic.services import enrichment_service
from logic.services.client_group_service import save_client_group, list_client_groups

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
    st.markdown("<h4 style='margin-bottom: 10px;'>1. Selecione os Clientes</h4>", unsafe_allow_html=True)
    
    # --- BUSCA E CARREGAMENTO (Interface Limpa) ---
    col_search, col_saved = st.columns([0.65, 0.35])
    
    with col_saved:
        try:
            saved_groups = list_client_groups()
            if saved_groups:
                selected_shortcut = st.selectbox(
                    "Carregar grupo salvo",
                    options=["Grupos Salvos"] + saved_groups,
                    index=0,
                    key=f"wiz_shortcut_{group.id}",
                    label_visibility="collapsed"
                )
                
                if selected_shortcut != "Grupos Salvos":
                    from ui.viewmodels.wizard_viewmodel import WizardViewModel
                    sucesso = WizardViewModel.load_shortcut(group.id, selected_shortcut)
                    if sucesso:
                        st.success(f"'{selected_shortcut}' carregado.")
                        st.session_state[f"wiz_shortcut_{group.id}"] = "Grupos Salvos"
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
        with st.container():
            st.markdown("<div style='margin-top: -10px; margin-bottom: 15px;'>", unsafe_allow_html=True)
            cols_batch = st.columns([0.6, 0.4])
            with cols_batch[1]:
                if len(unselected_clients) > 1:
                    if st.button(f"Adicionar {len(unselected_clients)} variações", key=f"wiz_add_all_{group.id}", use_container_width=True):
                        select_clients(group.id, group.clients + unselected_clients)
                        st.rerun()
            
            st.markdown("<div style='max-height: 180px; overflow-y: auto; padding: 5px; border: 1px solid rgba(0,0,0,0.05); border-radius: 8px;'>", unsafe_allow_html=True)
            for client in unselected_clients:
                 if st.button(f"+ {client}", key=f"wiz_add_btn_{group.id}_{safe_key(client)}", use_container_width=True):
                     update_group_clients(group.id, client, True)
                     st.rerun()
            st.markdown("</div></div>", unsafe_allow_html=True)
    elif search_term and not unselected_clients:
        st.info("Nenhum cliente novo encontrado.")

    # 2. Cesta de Selecionados (Progressive Disclosure)
    if group.clients:
        st.markdown("<hr style='opacity: 0.1; margin: 15px 0;'>", unsafe_allow_html=True)
        col_lbl, col_clr, col_save_pop = st.columns([0.5, 0.25, 0.25])
        
        with col_lbl:
            st.markdown(f"<p style='font-size: 0.9rem; margin-top: 5px;'><b>Selecionados:</b> {len(group.clients)} clientes</p>", unsafe_allow_html=True)
        
        with col_clr:
            if st.button("Limpar", key=f"wiz_btn_clear_{group.id}", use_container_width=True):
                clear_group_clients(group.id)
                st.rerun()
        
        with col_save_pop:
            # NOVO: Popover para salvar grupo (Premium Minimalism)
            if hasattr(st, "popover"):
                with st.popover("💾 Salvar", use_container_width=True):
                    st.markdown("<p style='font-size: 0.85rem; font-weight: bold;'>Novo Grupo de Clientes</p>", unsafe_allow_html=True)
                    new_group_name = st.text_input("Nome do Grupo", key=f"wiz_new_grp_name_{group.id}", placeholder="Ex: Clientes Setor Norte...")
                    if st.button("Salvar Agora", key=f"wiz_save_grp_btn_{group.id}", type="primary", use_container_width=True):
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
        if st.button("Próximo →", type="primary", use_container_width=True, disabled=len(group.clients) == 0):
            if group.is_auto_name:
                suggested = generate_suggested_filename(group.name, group.clients, group.periods)
                update_group_name(group.id, suggested)
            st.session_state.wizard_step = 2
            st.rerun()

def _render_step_2_periods(group: GroupState, available_periods: List[str]) -> None:
    """Passo focado 100% em Tempo e Nome do Arquivo."""
    st.markdown("<h4 style='margin-bottom: 10px;'>2. Defina o Período</h4>", unsafe_allow_html=True)
    
    # Estilo das pílulas (Apple-like)
    st.markdown("""
        <style>
        div[data-testid="stPills"] button { border-radius: 12px !important; border: 1px solid #e0e0e0 !important; }
        div[data-testid="stPills"] button[aria-pressed="true"] { background-color: #007aff !important; border: none !important; }
        </style>
    """, unsafe_allow_html=True)

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
    new_name = st.text_input(
        "Nome do Arquivo Final",
        value=group.name,
        key=f"wiz_name_{group.id}",
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
        if st.button("← Voltar", use_container_width=True):
            st.session_state.wizard_step = 1
            st.rerun()
    with col_next:
        if st.button("Revisar →", type="primary", use_container_width=True, disabled=len(group.periods) == 0):
            st.session_state.wizard_step = 3
            st.rerun()

def _render_step_3_review(group: GroupState, orch: Any) -> None:
    """Resumo e botão Final de Geração. Esconde engrenagens em 'Avançado'."""
    st.markdown(
        """
        <div class="wiz-review-hero">
            <h4>3. Revisão e Geração</h4>
            <p>Esta etapa existe para confirmar o escopo da emissão antes de construir o arquivo. Revise volume, pendências e modo de apresentação.</p>
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
    metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
    metric_col_1.metric("Clientes", len(group.clients))
    metric_col_2.metric("Meses", len(group.periods))
    metric_col_3.metric("Faturas", metrics.total_invoices)

    output_mode_label = "ZIP por período" if len(group.periods) > 1 else "Excel único"
    with st.container(border=True):
        st.markdown(
            """
            <div class="wiz-panel-title">Decisão de saída</div>
            <div class="wiz-panel-copy">A interface já calculou o formato final com base no escopo escolhido. O objetivo aqui é evitar surpresa na hora do download.</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="wiz-chip-row">
                <span class="wiz-chip">{output_mode_label}</span>
                <span class="wiz-chip">{group.tipo_apresentacao}</span>
                <span class="wiz-chip">{'Com resumo executivo' if group.incluir_resumo else 'Sem resumo executivo'}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --- TRATAMENTO DE INCOMPLETOS (Fim do Data Dump) ---
    incomplete_filter = "all"  # default
    
    if metrics.incomplete_count > 0:
        st.info(f"💡 **{metrics.incomplete_count}** faturas precisam de atenção (vencimento ausente).")
        
        col_det, col_mode = st.columns([0.4, 0.6])
        with col_det:
            if hasattr(st, "popover"):
                with st.popover("🔍 Ver Detalhes", use_container_width=True):
                    st.dataframe(metrics.incomplete_details, hide_index=True)
            else:
                with st.expander("Ver Detalhes"):
                    st.dataframe(metrics.incomplete_details, hide_index=True)
        
        with col_mode:
            incomplete_filter = st.selectbox(
                "Filtrar:",
                options=["all", "complete_only", "incomplete_only"],
                format_func=lambda x: {
                    "all": "Gerar Tudo",
                    "complete_only": "Somente Completos",
                    "incomplete_only": "Somente Incompletos"
                }[x],
                label_visibility="collapsed",
                key="wiz_incomplete_filter"
            )
    else:
        st.success("Todas as faturas do escopo atual possuem vencimento identificado.")

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    from ui.state.group_state import (
        set_tipo_apresentacao, set_incluir_resumo, set_somente_pendencias, set_separar_auditoria
    )
    with st.container(border=True):
        st.markdown(
            """
            <div class="wiz-panel-title">Opções de apresentação</div>
            <div class="wiz-panel-copy">Estas escolhas alteram a forma de entrega do arquivo, não o conjunto base de dados selecionado.</div>
            """,
            unsafe_allow_html=True,
        )
        col_apres1, col_apres2 = st.columns(2)
        with col_apres1:
            new_tipo = st.radio(
                "Tipo de Apresentação",
                options=["Separadores Múltiplos", "Tabela Única"],
                index=0 if group.tipo_apresentacao == "Separadores Múltiplos" else 1,
                key=f"wiz_tipo_apres_{group.id}"
            )
            if new_tipo != group.tipo_apresentacao:
                set_tipo_apresentacao(group.id, new_tipo)

        with col_apres2:
            new_resumo = st.checkbox(
                "Incluir Resumo Executivo",
                value=group.incluir_resumo,
                key=f"wiz_resumo_{group.id}"
            )
            if new_resumo != group.incluir_resumo:
                set_incluir_resumo(group.id, new_resumo)

            new_pendencias = st.checkbox(
                "Gerar apenas faturas pendentes (Ocultar 'Pago')",
                value=group.somente_pendencias,
                key=f"wiz_pendencias_{group.id}"
            )
            if new_pendencias != group.somente_pendencias:
                set_somente_pendencias(group.id, new_pendencias)

            new_auditoria = st.checkbox(
                "Separar linhas de Auditoria (Regras/Filhas)",
                value=group.separar_auditoria,
                key=f"wiz_auditoria_{group.id}"
            )
            if new_auditoria != group.separar_auditoria:
                set_separar_auditoria(group.id, new_auditoria)

    # --- BOTÃO PRINCIPAL (O Caminho Feliz) ---
    with st.container(border=True):
        st.markdown(
            """
            <div class="wiz-panel-title">Geração final</div>
            <div class="wiz-panel-copy">Se o escopo estiver correto, siga com a construção do arquivo. O download é liberado no mesmo passo, sem navegação extra.</div>
            """,
            unsafe_allow_html=True,
        )
    if st.button("Gerar Memória de Cálculo", type="primary", use_container_width=True, icon="✨"):
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
                        period_label = format_period_label(period).replace("/", "_")
                        period_excel = orch.generate(
                            payload.clients,
                            [period],
                            incomplete_filter=payload.incomplete_filter,
                            group_by_distributor=payload.group_by_distributor,
                            enrichment_df=payload.enrichment_df,
                            somente_pendencias=payload.somente_pendencias,
                            tipo_apresentacao=payload.tipo_apresentacao,
                            incluir_resumo=payload.incluir_resumo,
                            separar_auditoria=payload.separar_auditoria
                        )
                        if period_excel:
                            f_name = f"{sanitize_filename(group.name)}_{period_label}.xlsx"
                            z.writestr(f_name, period_excel)
                
                final_data = zip_buffer.getvalue()
            else:
                # Geração Individual: Um único arquivo Excel
                final_data = orch.generate(
                    payload.clients, 
                    payload.periods, 
                    incomplete_filter=payload.incomplete_filter,
                    group_by_distributor=payload.group_by_distributor,
                    enrichment_df=payload.enrichment_df,
                    somente_pendencias=payload.somente_pendencias,
                    tipo_apresentacao=payload.tipo_apresentacao,
                    incluir_resumo=payload.incluir_resumo,
                    separar_auditoria=payload.separar_auditoria
                )
            
        elapsed = time.time() - start_time
        if final_data:
            st.toast(f"Planilha pronta em {elapsed:.1f}s!", icon="✅")
            st.download_button(
                label=f"📥 Baixar Arquivo {'ZIP' if payload.is_multiplexed else 'Excel'}",
                data=final_data,
                file_name=payload.filename,
                mime=payload.mime_type,
                use_container_width=True,
                type="primary"
            )
        else:
            st.error("Erro na geração: Verifique os critérios selecionados.")

    # --- OPÇÕES AVANÇADAS (As Engrenagens Escondidas) ---
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    with st.expander("⚙️ Opções Avançadas"):
        st.markdown("<p style='font-size: 0.85rem; color: #666;'>Configurações técnicas para usuários experientes.</p>", unsafe_allow_html=True)
        
        # Enriquecimento (automático — informativo)
        st.markdown("**Enriquecimento:** Aplicado automaticamente a partir de todos os perfis cadastrados na aba de Metadados.")
        
        from ui.state.group_state import set_group_by_distributor
        # Toggle de Distribuidora
        new_distrib = st.toggle(
            "Agrupar faturas por Distribuidora",
            value=group.group_by_distributor,
            key=f"wiz_distributor_toggle_{group.id}",
            help="Cria uma aba ou agrupamento por distribuidora de energia."
        )
        if new_distrib != group.group_by_distributor:
            set_group_by_distributor(group.id, new_distrib)
        
        st.checkbox("Habilitar modo de depuração (Logs detalhados)", value=False)

    # Footer de Navegação
    st.divider()
    col_back, col_restart = st.columns([0.5, 0.5])
    with col_back:
        if st.button("← Ajustar Período", use_container_width=True):
            st.session_state.wizard_step = 2
            st.rerun()
    with col_restart:
        if st.button("Reiniciar Wizard", use_container_width=True, help="Limpa tudo e volta ao passo 1"):
            clear_group_clients(group.id)
            update_group_periods(group.id, [])
            st.session_state.wizard_step = 1
            st.rerun()
