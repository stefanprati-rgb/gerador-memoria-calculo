import time
import logging
import io
import zipfile
import streamlit as st

logger = logging.getLogger(__name__)
from typing import List, Any
from ui.state.group_state import (
    GroupState, initialize_groups, add_group, remove_group, 
    update_group_name, update_group_clients, clear_group_clients, 
    select_clients, update_group_periods
)
from ui.utils.search_utils import build_search_index, filter_values
from ui.utils.format_utils import format_period_label, safe_key, sanitize_filename, generate_suggested_filename
from logic.services import enrichment_service
from logic.services.client_group_service import save_client_group, list_client_groups, get_clients_from_group
from ui.utils.notifications import notify_completion
import pandas as pd

def _get_wizard_group() -> GroupState:
    """O Wizard foca em apenas 1 grupo (projeto) por vez."""
    initialize_groups()
    if not st.session_state.groups:
        add_group()
    return st.session_state.groups[0]

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
                    group_clients = get_clients_from_group(selected_shortcut)
                    if group_clients:
                        select_clients(group.id, group_clients)
                        update_group_name(group.id, selected_shortcut) # Sincroniza o nome do grupo carregado
                        
                        try:
                            profile = enrichment_service.load_mapping(selected_shortcut)
                            if profile is not None:
                                val = False
                                if isinstance(profile, dict):
                                    val = profile.get("group_by_distributor", False)
                                elif hasattr(profile, "get"):
                                    res = profile.get("group_by_distributor", False)
                                    if not isinstance(res, (pd.Series, pd.DataFrame)):
                                        val = res
                                
                                st.session_state.group_state.group_by_distributor = bool(val)
                        except Exception as profile_err:
                            logger.error("Erro ao sincronizar regras de perfil: %s", profile_err)
                            
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
            # Se ainda estiver no modo automático, sugerir novo nome baseado nos períodos
            if group.is_auto_name:
                suggested = generate_suggested_filename(group.name, group.clients, list(new_periods))
                update_group_name(group.id, suggested)
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
        # Se o usuário editar manualmente, desativar o modo automático
        if group.is_auto_name:
            # Só desativa se o que ele digitou for diferente da sugestão que teríamos agora
            current_suggestion = generate_suggested_filename(group.name, group.clients, group.periods)
            if new_name != current_suggestion:
                group.is_auto_name = False
        update_group_name(group.id, new_name)
    
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
    st.markdown("<h4 style='margin-bottom: 10px;'>3. Revisão & Geração</h4>", unsafe_allow_html=True)
    
    # Card de Resumo Minimalista
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Clientes", len(group.clients))
        c2.metric("Meses", len(group.periods))
        
        count = orch.count_filtered(group.clients, group.periods)
        c3.metric("Faturas", count)

    # --- TRATAMENTO DE INCOMPLETOS (Fim do Data Dump) ---
    incomplete_info = orch.check_incomplete_rows(group.clients, group.periods)
    incomplete_count = incomplete_info["registros_incompletos"]
    complete_count = incomplete_info["total_registros"] - incomplete_count
    
    incomplete_filter = "all"  # default
    
    if incomplete_count > 0:
        st.info(f"💡 **{incomplete_count}** faturas precisam de atenção (vencimento ausente).")
        
        col_det, col_mode = st.columns([0.4, 0.6])
        with col_det:
            if hasattr(st, "popover"):
                with st.popover("🔍 Ver Detalhes", use_container_width=True):
                    st.dataframe(incomplete_info["ucs_afetadas"], hide_index=True)
            else:
                with st.expander("Ver Detalhes"):
                    st.dataframe(incomplete_info["ucs_afetadas"], hide_index=True)
        
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

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    # --- BOTÃO PRINCIPAL (O Caminho Feliz) ---
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
            if len(group.periods) > 1:
                # Geração Multiplexada: Um arquivo por referência dentro de um ZIP
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
                    for period in group.periods:
                        period_label = format_period_label(period).replace("/", "_")
                        period_excel = orch.generate(
                            group.clients,
                            [period],
                            incomplete_filter=incomplete_filter,
                            group_by_distributor=group.group_by_distributor,
                            enrichment_df=enrichment_df
                        )
                        if period_excel:
                            f_name = f"{sanitize_filename(group.name)}_{period_label}.xlsx"
                            z.writestr(f_name, period_excel)
                
                final_data = zip_buffer.getvalue()
                is_zip = True
            else:
                # Geração Individual: Um único arquivo Excel
                final_data = orch.generate(
                    group.clients, 
                    group.periods, 
                    incomplete_filter=incomplete_filter,
                    group_by_distributor=group.group_by_distributor,
                    enrichment_df=enrichment_df
                )
                is_zip = False
            
        elapsed = time.time() - start_time
        if final_data:
            if is_zip:
                filename = f"{sanitize_filename(group.name)}.zip"
                mime_type = "application/zip"
                label = "📥 Baixar Arquivo ZIP"
            else:
                filename = f"{sanitize_filename(group.name)}.xlsx"
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                label = "📥 Baixar Arquivo Excel"

            st.toast(f"Planilha pronta em {elapsed:.1f}s!", icon="✅")
            st.download_button(
                label=label,
                data=final_data,
                file_name=filename,
                mime=mime_type,
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
        
        # Toggle de Distribuidora
        group.group_by_distributor = st.toggle(
            "Agrupar faturas por Distribuidora",
            value=group.group_by_distributor,
            key=f"wiz_distributor_toggle_{group.id}",
            help="Cria uma aba ou agrupamento por distribuidora de energia."
        )
        
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
