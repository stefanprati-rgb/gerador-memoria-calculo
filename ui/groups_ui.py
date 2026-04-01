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

def render_groups_section(available_clients: List[str], available_periods: List[str], orch: Any) -> None:
    """Renderiza a seção de grupos (container global) iterando sobre o modelo de estado."""
    st.subheader("Configuração de Grupos de Emissão")
    st.caption("Crie grupos para definir quais clientes e períodos sairão juntos em uma planilha separada.")
    st.markdown("---")

    initialize_groups()

    for i, group in enumerate(st.session_state.groups):
        render_group_card(group, i, available_clients, available_periods, orch)

    st.button("➕ Adicionar Novo Grupo", on_click=add_group, use_container_width=False)
    st.markdown("---")


@st.fragment
def render_group_card(group: GroupState, index: int, available_clients: List[str], available_periods: List[str], orch: Any) -> None:
    """Renderiza fragmento individual de um grupo com subcomponentes."""
    is_complete = bool(group.clients) and bool(group.periods)

    with st.expander(f"📋 {group.name}  —  {'✅ Pronto' if is_complete else '⚠️ Incompleto'}", expanded=(index == 0)):
        _render_group_header(group)
        _render_client_selector(group, available_clients)
        _render_period_selector(group, available_periods)
        _render_record_preview(group, orch)


def _render_group_header(group: GroupState) -> None:
    """Sub-função de renderização da edição de nome e botões de cabeçalho."""
    col_name, col_btn = st.columns([0.9, 0.1])
    
    with col_name:
        new_name = st.text_input(
            "Nome do Arquivo",
            value=group.name,
            key=f"name_{group.id}",
            label_visibility="collapsed",
            placeholder="Nome do arquivo de saída..."
        )
        if new_name != group.name:
            update_group_name(group.id, new_name)

    with col_btn:
        if len(st.session_state.groups) > 1:
            if st.button("🗑️", key=f"del_{group.id}", help="Remover grupo"):
                remove_group(group.id)
                st.rerun()


def _render_client_selector(group: GroupState, available_clients: List[str]) -> None:
    """Centraliza a lógica de seleção de clientes baseada com checkboxes."""
    total = len(available_clients)
    selected = len(group.clients)
    
    st.markdown(f"**Clientes** ({selected} selecionados / {total} disponíveis)")
    
    search_term = st.text_input(
        "Buscar cliente...", 
        key=f"search_cli_{group.id}", 
        label_visibility="collapsed",
        placeholder="🔍 Digite o nome (ou parte) e pressione ENTER..."
    )
    
    search_index = build_search_index(available_clients)
    
    if search_term:
        filtered_clients = filter_values(search_term, search_index)
        _render_client_bulk_actions(group, filtered_clients)
        _do_render_checkboxes(group, filtered_clients)
    else:
        st.info("☝️ Digite acima para buscar clientes ou veja os primeiros da lista.")
        _render_client_bulk_actions(group, None)
        _do_render_checkboxes(group, available_clients[:50])


def _render_client_bulk_actions(group: GroupState, filtered_clients: List[str] | None) -> None:
    """Rendere botões de selecionar lote ou limpar."""
    col_sel_all, col_clear = st.columns([1, 1])
    
    with col_sel_all:
        if filtered_clients is not None:
            btn_label = f"✅ Selecionar {len(filtered_clients)} Filtrados"
            if st.button(btn_label, key=f"all_cli_{group.id}", width='stretch'):
                select_clients(group.id, filtered_clients)
                st.rerun()
        else:
            if st.button("🧹 Limpar Selecionados", key=f"clear_cli_no_search_{group.id}", width='stretch'):
                clear_group_clients(group.id)
                st.rerun()
                
    with col_clear:
        if filtered_clients is not None:
            if st.button("🧹 Limpar Todos", key=f"clear_cli_{group.id}", width='stretch'):
                clear_group_clients(group.id)
                st.rerun()


def _do_render_checkboxes(group: GroupState, list_to_render: List[str]) -> None:
    """Implementa as interações de checkbox em loop dentro de scroll container."""
    if not list_to_render:
        st.info("Nenhum cliente encontrado com este termo.")
        return
        
    with st.container(height=250):
        for client in list_to_render:
            is_checked = client in group.clients
            k = f"client_checkbox_{group.id}_{safe_key(client)}"
            
            # Nota: atualizar o valor na tela gera event re-render automatico pelo Streamlit no escopo do st.fragment.
            # E nós não passamos action que força st.rerun
            checked_state = st.checkbox(client, value=is_checked, key=k)
            if checked_state != is_checked:
                update_group_clients(group.id, client, checked_state)


def _render_period_selector(group: GroupState, available_periods: List[str]) -> None:
    """Renderiza interface de seleção de períodos por multiselect nativo em Streamlit."""
    st.markdown("**Períodos de Referência**")
    
    col_sel_all, col_clear = st.columns([1, 1])
    
    with col_sel_all:
        if st.button("✅ Selecionar Todos", key=f"all_per_{group.id}", width='stretch'):
            update_group_periods(group.id, list(available_periods))
            st.rerun()
            
    with col_clear:
        if st.button("🧹 Limpar", key=f"clear_per_{group.id}", width='stretch'):
            update_group_periods(group.id, [])
            st.rerun()

    new_periods = st.multiselect(
        "Períodos de Referência:", 
        options=available_periods,
        default=group.periods,
        format_func=format_period_label,
        key=f"periods_{group.id}",
        label_visibility="collapsed"
    )
    
    if new_periods != group.periods:
        update_group_periods(group.id, new_periods)


def _render_record_preview(group: GroupState, orch: Any) -> None:
    """Valida via contagem do ORCH se existem items para render preview em tela."""
    if group.clients and group.periods:
        count = orch.count_filtered(group.clients, group.periods)
        st.markdown(
            f'<p class="record-preview">📄 Filtro atual: <strong>{count}</strong> registros encontrados</p>',
            unsafe_allow_html=True
        )
    elif group.clients or group.periods:
        st.markdown(
            '<p class="record-preview">Selecione clientes <strong>e</strong> períodos para ver a prévia</p>',
            unsafe_allow_html=True
        )


def render_generation_button(orch: Any) -> None:
    """Lógica do botão primário para geração em lote ou único file de memoria de calculo."""
    valid_groups = [g for g in st.session_state.groups if g.clients and g.periods]
    
    if not valid_groups:
        st.button("⚡ Gerar Planilhas Selecionadas", type="primary", width='stretch', disabled=True)
        st.info("Adicione clientes e períodos aos grupos para habilitar a geração.")
        return

    # 1. Verificar faturas incompletas em todos os grupos
    alerts = []
    for g in valid_groups:
        incomplete_info = orch.check_incomplete_rows(g.clients, g.periods)
        if incomplete_info["registros_incompletos"] > 0:
            alerts.append({
                "group_name": g.name,
                "count": incomplete_info["registros_incompletos"],
                "details": incomplete_info["ucs_afetadas"]
            })
    
    can_proceed = True
    if alerts:
        with st.container(border=True):
            st.warning("### ⚠ Dados incompletos detectados")
            st.write("Algumas faturas no Balanço não possuem correspondente na Gestão de Cobrança (Vencimento ausente).")
            
            for alert in alerts:
                with st.expander(f"Grupo: {alert['group_name']} — {alert['count']} pendências"):
                    st.dataframe(alert["details"], width='stretch')
            
            confirm = st.checkbox(
                "Estou ciente dos dados ausentes e quero gerar mesmo assim",
                key="confirm_incomplete_generation"
            )
            if not confirm:
                can_proceed = False
                st.info("Você precisa confirmar que está ciente para prosseguir.")

    # 2. Botão de geração (desabilitado se houver pendências não confirmadas)
    if st.button("⚡ Gerar Planilhas Selecionadas", type="primary", width='stretch', disabled=not can_proceed):
        start_time = time.time()
        
        if len(valid_groups) == 1:
            _generate_single(valid_groups[0], orch, start_time)
        else:
            _generate_multiple(valid_groups, orch, start_time)


def _generate_single(group: GroupState, orch: Any, start_time: float) -> None:
    """Extrai Excel individual utilizando object group na memoria."""
    with st.spinner("Processando planilha..."):
        excel_data = orch.generate(group.clients, group.periods)
    
    elapsed = time.time() - start_time
    
    if excel_data:
        filename = f"{sanitize_filename(group.name)}.xlsx"
        st.toast(f"✅ Planilha gerada em {elapsed:.1f}s!", icon="⚡")
        st.success(f"Planilha **{filename}** gerada com sucesso!")
        st.download_button(
            label="📥 Baixar Arquivo Gerado",
            data=excel_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch',
        )
    else:
        st.warning("Nenhum dado encontrado para gerar a planilha com os filtros aplicados.")


def _generate_multiple(valid_groups: List[GroupState], orch: Any, start_time: float) -> None:
    """Gera múltiplos Excels encadeados via batch process ZIP."""
    with st.spinner(f"Gerando {len(valid_groups)} planilhas em lote..."):
        groups_payload = [
            {"name": sanitize_filename(g.name), "clients": g.clients, "periods": g.periods}
            for g in valid_groups
        ]
        zip_data = orch.generate_multiple(groups_payload)
    
    elapsed = time.time() - start_time
    
    if zip_data:
        st.toast(f"✅ {len(valid_groups)} planilhas geradas em {elapsed:.1f}s!", icon="📦")
        st.success(f"**{len(valid_groups)} planilhas** geradas e empacotadas com sucesso!")
        st.download_button(
            label="📦 Baixar Lote (ZIP)",
            data=zip_data,
            file_name="Memoria_De_Calculo_Lote.zip",
            mime="application/zip",
            width='stretch',
        )
    else:
        st.warning("Nenhum dado encontrado para gerar as planilhas com os filtros aplicados.")
