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

def initialize_groups() -> None:
    """Inicializa o estado dos grupos na sessão do Streamlit, se não existir."""
    if 'groups' not in st.session_state:
        st.session_state.groups = [GroupState(id=1, name="Grupo_1")]
    if 'group_counter' not in st.session_state:
        st.session_state.group_counter = 1
    
    # Adicionando group_state apontando para o grupo principal para facilitar o uso no Wizard
    if 'group_state' not in st.session_state and st.session_state.groups:
        st.session_state.group_state = st.session_state.groups[0]

def add_group() -> None:
    """Adiciona um novo grupo e incrementa o contador."""
    st.session_state.group_counter += 1
    new_id = st.session_state.group_counter
    st.session_state.groups.append(
        GroupState(id=new_id, name=f"Grupo_{new_id}")
    )

def remove_group(group_id: int) -> None:
    """Remove um grupo da sessão pelo seu ID."""
    st.session_state.groups = [g for g in st.session_state.groups if g.id != group_id]
    # Se removeu o grupo que estava em group_state, reseta se possível
    if st.session_state.groups:
        st.session_state.group_state = st.session_state.groups[0]

def update_group_name(group_id: int, new_name: str) -> None:
    """Atualiza o nome de um grupo específico."""
    for g in st.session_state.groups:
        if g.id == group_id:
            g.name = new_name
            break

def update_group_clients(group_id: int, client: str, checked: bool) -> None:
    """Adiciona ou remove um cliente da seleção do grupo de forma imutável."""
    for g in st.session_state.groups:
        if g.id == group_id:
            clients_set = set(g.clients)
            if checked:
                clients_set.add(client)
            else:
                clients_set.discard(client)
            g.clients = list(clients_set)
            break

def clear_group_clients(group_id: int) -> None:
    """Limpa todos os clientes selecionados para o grupo."""
    for g in st.session_state.groups:
        if g.id == group_id:
            g.clients = []
            break

def select_clients(group_id: int, clients_to_add: List[str]) -> None:
    """Seleciona em lote uma lista de clientes para o grupo."""
    for g in st.session_state.groups:
        if g.id == group_id:
            clients_set = set(g.clients)
            # Add preserving order optionally, or just using set is fine as sorting will happen later if needed
            clients_set.update(clients_to_add)
            g.clients = list(clients_set)
            break

def update_group_periods(group_id: int, periods: List[str]) -> None:
    """Atualiza a lista completa de períodos selecionados do grupo."""
    for g in st.session_state.groups:
        if g.id == group_id:
            g.periods = periods
            break
