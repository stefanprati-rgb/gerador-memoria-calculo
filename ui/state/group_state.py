from dataclasses import dataclass, field
from typing import List
import streamlit as st

@dataclass
class GroupState:
    """Modelo de dados tipado representando um grupo de exportação."""
    id: int
    name: str
    clients: List[str] = field(default_factory=list)
    periods: List[str] = field(default_factory=list)
    group_by_distributor: bool = False
    is_auto_name: bool = True
    somente_pendencias: bool = False

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
