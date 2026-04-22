from dataclasses import dataclass, field
from typing import List
import streamlit as st
from logic.core.mapping import GROUPING_MODE_DEFAULT, GROUPING_MODE_DISTRIBUTOR

@dataclass
class GroupState:
    """Modelo de dados tipado representando um grupo de exportação."""
    id: int
    name: str
    clients: List[str] = field(default_factory=list)
    periods: List[str] = field(default_factory=list)
    group_by_distributor: bool = False
    grouping_mode: str = GROUPING_MODE_DEFAULT
    include_child_rows: bool = True
    is_auto_name: bool = True
    somente_pendencias: bool = False
    tipo_apresentacao: str = "Separadores Múltiplos"
    incluir_resumo: bool = True
    separar_auditoria: bool = True

def initialize_groups() -> None:
    """Inicializa o estado dos grupos na sessão do Streamlit, se não existir."""
    if "groups" not in st.session_state:
        st.session_state.groups = [GroupState(id=1, name="Grupo_1")]

    if "group_counter" not in st.session_state:
        st.session_state.group_counter = max(g.id for g in st.session_state.groups) if st.session_state.groups else 1

    if "active_group_id" not in st.session_state:
        st.session_state.active_group_id = (
            st.session_state.groups[0].id if st.session_state.groups else None
        )

def get_group(group_id: int) -> GroupState | None:
    for group in st.session_state.groups:
        if group.id == group_id:
            return group
    return None

def get_active_group() -> GroupState | None:
    active_group_id = st.session_state.get("active_group_id")
    if active_group_id is None:
        return None
    return get_group(active_group_id)

def add_group() -> GroupState:
    """Adiciona um novo grupo e incrementa o contador."""
    st.session_state.group_counter += 1
    new_id = st.session_state.group_counter
    new_group = GroupState(id=new_id, name=f"Grupo_{new_id}")
    st.session_state.groups.append(new_group)
    st.session_state.active_group_id = new_id
    return new_group

def remove_group(group_id: int) -> None:
    """Remove um grupo da sessão pelo seu ID."""
    st.session_state.groups = [g for g in st.session_state.groups if g.id != group_id]

    if not st.session_state.groups:
        st.session_state.active_group_id = None
        return

    if st.session_state.active_group_id == group_id:
        st.session_state.active_group_id = st.session_state.groups[0].id

def update_group_name(group_id: int, new_name: str) -> None:
    """Atualiza o nome de um grupo específico."""
    group = get_group(group_id)
    if group:
        group.name = new_name.strip() or f"Grupo_{group_id}"

def update_group_name_if_auto(group_id: int) -> None:
    """Se o grupo estiver com nomeação automática, recalcula e atualiza o nome."""
    group = get_group(group_id)
    if group and group.is_auto_name:
        from ui.utils.format_utils import generate_suggested_filename
        suggested = generate_suggested_filename(group.name, group.clients, group.periods)
        group.name = suggested

def set_custom_group_name(group_id: int, new_name: str) -> None:
    """O usuário digitou um nome manualmente. Avalia se desliga o modo automático."""
    group = get_group(group_id)
    if group:
        from ui.utils.format_utils import generate_suggested_filename
        current_suggestion = generate_suggested_filename(group.name, group.clients, group.periods)
        if new_name != current_suggestion:
            group.is_auto_name = False
        group.name = new_name.strip() or f"Grupo_{group_id}"

def update_group_clients(group_id: int, client: str, checked: bool) -> None:
    """Adiciona ou remove um cliente da seleção do grupo de forma imutável."""
    group = get_group(group_id)
    if not group:
        return

    if checked:
        if client not in group.clients:
            group.clients.append(client)
    else:
        group.clients = [c for c in group.clients if c != client]

def clear_group_clients(group_id: int) -> None:
    """Limpa todos os clientes selecionados para o grupo."""
    group = get_group(group_id)
    if group:
        group.clients.clear()

def select_clients(group_id: int, clients_to_add: List[str]) -> None:
    """Seleciona em lote uma lista de clientes para o grupo."""
    group = get_group(group_id)
    if not group:
        return

    existing = set(group.clients)
    for client in clients_to_add:
        if client not in existing:
            group.clients.append(client)
            existing.add(client)

def update_group_periods(group_id: int, periods: List[str]) -> None:
    """Atualiza a lista completa de períodos selecionados do grupo."""
    group = get_group(group_id)
    if group:
        group.periods = list(periods)

def set_group_by_distributor(group_id: int, value: bool) -> None:
    group = get_group(group_id)
    if group:
        group.group_by_distributor = value
        group.grouping_mode = GROUPING_MODE_DISTRIBUTOR if value else GROUPING_MODE_DEFAULT

def set_grouping_mode(group_id: int, value: str) -> None:
    group = get_group(group_id)
    if group:
        group.grouping_mode = value
        group.group_by_distributor = value == GROUPING_MODE_DISTRIBUTOR

def set_include_child_rows(group_id: int, value: bool) -> None:
    group = get_group(group_id)
    if group:
        group.include_child_rows = value

def set_tipo_apresentacao(group_id: int, value: str) -> None:
    group = get_group(group_id)
    if group:
        group.tipo_apresentacao = value

def set_incluir_resumo(group_id: int, value: bool) -> None:
    group = get_group(group_id)
    if group:
        group.incluir_resumo = value

def set_somente_pendencias(group_id: int, value: bool) -> None:
    group = get_group(group_id)
    if group:
        group.somente_pendencias = value

def set_separar_auditoria(group_id: int, value: bool) -> None:
    group = get_group(group_id)
    if group:
        group.separar_auditoria = value
