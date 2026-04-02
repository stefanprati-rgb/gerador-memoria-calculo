import time
import streamlit as st
from typing import List, Any
from ui.state.group_state import (
    GroupState, initialize_groups, add_group, remove_group, 
    update_group_name, update_group_clients, clear_group_clients, 
    select_clients, update_group_periods
)
from ui.utils.search_utils import build_search_index, filter_values
from ui.utils.format_utils import format_period_label, safe_key, sanitize_filename
from logic.services import enrichment_service
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
    st.markdown("<h4 style='margin-bottom: 0;'>1. Selecione os Clientes</h4>", unsafe_allow_html=True)
    
    # 1. Área de Cesta
    if group.clients:
        col_lbl, col_clr = st.columns([0.7, 0.3])
        with col_lbl:
             st.markdown("<p style='font-size: 0.85rem; margin-bottom: 0;'><b>Na Planilha:</b></p>", unsafe_allow_html=True)
        with col_clr:
             if st.button("🧹 Limpar Tudo", key=f"wiz_btn_clear_{group.id}", width='stretch'):
                  clear_group_clients(group.id)
                  st.rerun()

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
             st.markdown(f"<div style='padding: 10px; background: rgba(0, 180, 216, 0.1); border-radius: 8px; border: 1px solid rgba(0, 180, 216, 0.2); font-size: 0.85rem; margin-bottom: 10px;'><b>Selecionados ({len(group.clients)}):</b> {', '.join(group.clients)}</div>", unsafe_allow_html=True)
             if st.button("🧹 Limpar selecionados", key=f"wiz_clear_all_{group.id}"):
                  clear_group_clients(group.id)
                  st.rerun()

    st.markdown("<hr style='opacity: 0.2;'>", unsafe_allow_html=True)

    # 2. Área de Busca
    search_index = build_search_index(available_clients)
    search_term = st.text_input(
        "Buscar cliente para adicionar...", 
        key=f"wiz_search_cli_{group.id}", 
        placeholder="🔍 Digite parte do nome da empresa..."
    )
    
    filtered_clients = filter_values(search_term, search_index) if search_term else []
    unselected_clients = [c for c in filtered_clients if c not in group.clients]

    if not search_term:
        st.caption("Digite acima para encontrar e adicionar clientes.")
    elif not unselected_clients:
        st.info("Nenhuma variação nova encontrada para esta busca.")
    else:
        st.caption("Resultados da Busca (Clique para adicionar):")
        if len(unselected_clients) > 1:
             if st.button(f"✨ Lote: Adicionar as {len(unselected_clients)} variações", key=f"wiz_add_all_{group.id}", type="secondary"):
                  select_clients(group.id, group.clients + unselected_clients)
                  st.rerun()
                  
        st.markdown("<div style='max-height: 180px; overflow-y: auto;'>", unsafe_allow_html=True)
        for client in unselected_clients:
             if st.button(f"+ {client}", key=f"wiz_add_btn_{group.id}_{safe_key(client)}", width='stretch'):
                 update_group_clients(group.id, client, True)
                 st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Controles de Navegação (Fixo em baixo)
    st.divider()
    _, col_next = st.columns([0.7, 0.3])
    with col_next:
        if st.button("Próximo ➔", type="primary", width='stretch', disabled=len(group.clients) == 0):
            st.session_state.wizard_step = 2
            st.rerun()

def _render_step_2_periods(group: GroupState, available_periods: List[str]) -> None:
    """Pede os períodos e o nome final do arquivo."""
    st.markdown("<h4 style='margin-bottom: 0;'>2. Selecione os Meses</h4>", unsafe_allow_html=True)
    
    # Injetar CSS para destacar as pílulas (Borda e Sombra)
    st.markdown("""
        <style>
        div[data-testid="stPills"] button {
            border: 2px solid #00b4d8 !important;
            box-shadow: 0 2px 4px rgba(0, 180, 216, 0.1);
            transition: all 0.2s ease;
        }
        div[data-testid="stPills"] button[aria-pressed="true"] {
            background-color: #00b4d8 !important;
            color: white !important;
            border-color: #0f4c75 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    options = available_periods
    format_func = format_period_label
    
    if hasattr(st, "pills"):
        new_periods = st.pills(
            "Períodos",
            options=options,
            default=group.periods,
            format_func=format_func,
            selection_mode="multi",
            key=f"wiz_pill_periods_{group.id}",
            label_visibility="collapsed"
        )
        if new_periods != group.periods:
            update_group_periods(group.id, list(new_periods))
            st.rerun()
    else:
        new_periods = st.multiselect(
            "Períodos", 
            options=options,
            default=group.periods,
            format_func=format_func,
            key=f"wiz_multi_periods_{group.id}"
        )
        if new_periods != group.periods:
            update_group_periods(group.id, new_periods)
            st.rerun()

    st.markdown("<div style='margin-top: -15px;'></div>", unsafe_allow_html=True)
    new_name = st.text_input(
        "Nome do Arquivo Final",
        value=group.name,
        key=f"wiz_name_{group.id}",
        placeholder="Memoria_Calculo_Final..."
    )
    if new_name != group.name:
        update_group_name(group.id, new_name)
    
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    st.session_state.group_state.group_by_distributor = st.toggle(
        "Agrupar faturas por Distribuidora",
        value=st.session_state.group_state.group_by_distributor,
        key=f"wiz_distributor_{group.id}"
    )
    
    # Controles
    st.divider()
    col_back, _, col_next = st.columns([0.3, 0.4, 0.3])
    with col_back:
        if st.button("⬅️ Voltar", width='stretch'):
            st.session_state.wizard_step = 1
            st.rerun()
    with col_next:
        if st.button("Revisar ➔", type="primary", width='stretch', disabled=len(group.periods) == 0):
            st.session_state.wizard_step = 3
            st.rerun()

def _render_step_3_review(group: GroupState, orch: Any) -> None:
    """Resumo e botão Final de Geração com opções de filtro de completude."""
    st.markdown("<h4 style='margin-bottom: 0;'>3. Revisão Final</h4>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown(f"<p style='margin-bottom: 5px;'><b>📄 Arquivo:</b> {group.name}.xlsx</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin-bottom: 5px;'><b>🏢 Clientes:</b> {len(group.clients)}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin-bottom: 5px;'><b>📅 Meses:</b> {len(group.periods)}</p>", unsafe_allow_html=True)
        
        count = orch.count_filtered(group.clients, group.periods)
        st.markdown(f"<p style='color: green; font-weight: bold;'>🎯 {count} registros encontrados</p>", unsafe_allow_html=True)

    # Verificar dados incompletos
    incomplete_info = orch.check_incomplete_rows(group.clients, group.periods)
    incomplete_count = incomplete_info["registros_incompletos"]
    complete_count = incomplete_info["total_registros"] - incomplete_count
    
    incomplete_filter = "all"  # default
    
    if incomplete_count > 0:
        st.warning(f"⚠ **{incomplete_count}** faturas sem vencimento detectadas ({complete_count} completas).")
        
        with st.expander("Ver detalhes das ausências"):
            st.dataframe(incomplete_info["ucs_afetadas"], width='stretch')
        
        # Opções de geração
        st.markdown("<p style='font-weight: 600; margin-bottom: 5px;'>Como deseja gerar?</p>", unsafe_allow_html=True)
        incomplete_filter = st.radio(
            "Modo de geração",
            options=["all", "complete_only", "incomplete_only"],
            format_func=lambda x: {
                "all": f"📋 Tudo ({count} registros — inclui incompletos)",
                "complete_only": f"✅ Somente Completos ({complete_count} registros)",
                "incomplete_only": f"⚠️ Somente Incompletos ({incomplete_count} registros)"
            }[x],
            index=0,
            key="wiz_incomplete_filter",
            label_visibility="collapsed"
        )

    st.divider()

    # Perfil de Enriquecimento
    st.markdown("<p style='font-weight: 600; margin-bottom: 5px;'>Enriquecimento de Dados (Opcional)</p>", unsafe_allow_html=True)
    profiles = enrichment_service.list_profiles()
    selected_enrichment = st.selectbox(
        "Selecione um perfil mapeado para incluir códigos internos",
        options=["Nenhum"] + profiles,
        index=0,
        key=f"wiz_enrichment_{group.id}",
        help="Se selecionado, o sistema fará o merge dos dados do perfil com a base usando o No. UC antes de gerar o Excel."
    )
    
    enrichment_df = None
    if selected_enrichment != "Nenhum":
         enrichment_df = enrichment_service.load_mapping(selected_enrichment)
         if enrichment_df is not None:
              st.success(f"✅ Enriquecimento aplicado usando o perfil: **{selected_enrichment}**")

    # Botão de geração
    if st.button("🪄 Gerar Planilha Agora", type="primary", width='stretch'):
        start_time = time.time()
        with st.spinner("Construindo planilha..."):
            excel_data = orch.generate(
                group.clients, 
                group.periods, 
                incomplete_filter=incomplete_filter,
                group_by_distributor=st.session_state.group_state.group_by_distributor,
                enrichment_df=enrichment_df
            )
            
        elapsed = time.time() - start_time
        if excel_data:
            filename = f"{sanitize_filename(group.name)}.xlsx"
            st.success(f"Tudo Certo! Arquivo gerado em {elapsed:.1f} segundos.", icon="🎉")
            st.download_button(
                label="⬇️ Baixar Excel (.xlsx)",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='stretch',
                type="primary"
            )
        else:
            st.error("Nenhum dado encontrado para gerar a planilha.")

    st.divider()
    col_back, _, col_restart = st.columns([0.3, 0.4, 0.3])
    with col_back:
        if st.button("⬅️ Voltar", width='stretch'):
            st.session_state.wizard_step = 2
            st.rerun()
    with col_restart:
        if st.button("Limpar e Iniciar Novo", width='stretch'):
            clear_group_clients(group.id)
            update_group_periods(group.id, [])
            st.session_state.wizard_step = 1
            st.rerun()
