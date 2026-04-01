import time
import streamlit as st
from typing import List, Any
from ui.state.group_state import (
    Group, initialize_groups, add_group, remove_group, 
    update_group_name, update_group_clients, clear_group_clients, 
    select_clients, update_group_periods
)
from ui.utils.search_utils import build_search_index, filter_values
from ui.utils.format_utils import format_period_label, safe_key, sanitize_filename

def render_groups_section_v2(available_clients: List[str], available_periods: List[str], orch: Any) -> None:
    """Renderiza a seção de grupos (container global) usando a nova interface V2 (Cards)."""
    st.subheader("Gerador de Memória de Cálculo", anchor=False)
    st.markdown("<p style='opacity: 0.8; font-size: 0.95rem; margin-top: -10px; margin-bottom: 2rem;'>Selecione os clientes e os períodos para gerar a(s) planilha(s). Use múltiplos grupos se quiser planilhas separadas.</p>", unsafe_allow_html=True)

    initialize_groups()

    for i, group in enumerate(st.session_state.groups):
        render_group_card_v2(group, i, available_clients, available_periods, orch)

    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.button("➕ Adicionar Novo Arquivo / Grupo", on_click=add_group, use_container_width=True, help="Útil se você quiser baixar vários arquivos separados de uma vez num ZIP.")
    st.markdown("---")


@st.fragment
def render_group_card_v2(group: Group, index: int, available_clients: List[str], available_periods: List[str], orch: Any) -> None:
    """Renderiza um Card limpo (sem expander) contendo o fluxo óbvio de preenchimento."""
    is_complete = bool(group.clients) and bool(group.periods)
    
    # CSS Customizado garantido via st.markdown para o Card da Apple
    st.markdown("""
        <style>
        .apple-card {
            background: var(--background-color);
            border-radius: 16px;
            padding: 1.5rem 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 24px rgba(0,0,0,0.06);
            border: 1px solid var(--secondary-background-color);
            transition: all 0.3s ease;
        }
        .apple-card:hover {
            box-shadow: 0 8px 32px rgba(0,0,0,0.08);
            transform: translateY(-2px);
        }
        .step-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-color);
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .step-number {
            background: var(--primary-color);
            color: white;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.85rem;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="apple-card">', unsafe_allow_html=True)
        
        # Cabeçalho do Card
        col_header, col_del = st.columns([0.95, 0.05])
        with col_header:
            if is_complete:
                 st.markdown("##### ✅ Configuração Pronta", unsafe_allow_html=True)
            else:
                 st.markdown("##### ⚙️ Configurando Arquivo...", unsafe_allow_html=True)
                 
            # Nome do arquivo mais elegante
            new_name = st.text_input(
                "Nome do Arquivo Final",
                value=group.name,
                key=f"name_v2_{group.id}",
                label_visibility="collapsed",
                placeholder="Exemplo: Memoria_Calculo_Novembro..."
            )
            if new_name != group.name:
                update_group_name(group.id, new_name)
                
        with col_del:
            if len(st.session_state.groups) > 1:
                if st.button("🗑️", key=f"del_v2_{group.id}", help="Deletar este grupo"):
                    remove_group(group.id)
                    st.rerun()

        st.markdown("<hr style='opacity: 0.2; margin: 1.5rem 0;'>", unsafe_allow_html=True)

        # Passo 1: Quem
        st.markdown('<div class="step-title"><span class="step-number">1</span> Quem? (Clientes)</div>', unsafe_allow_html=True)
        _render_client_selector_v2(group, available_clients)
        
        st.markdown("<hr style='opacity: 0.2; margin: 1.5rem 0;'>", unsafe_allow_html=True)

        # Passo 2: Quando
        st.markdown('<div class="step-title"><span class="step-number">2</span> Quando? (Períodos referentes)</div>', unsafe_allow_html=True)
        _render_period_selector_v2(group, available_periods)

        st.markdown("<hr style='opacity: 0.2; margin: 1.5rem 0;'>", unsafe_allow_html=True)

        # Rodapé do Card
        _render_record_preview_v2(group, orch)

        st.markdown('</div>', unsafe_allow_html=True)

def _render_client_selector_v2(group: Group, available_clients: List[str]) -> None:
    """Interface moderna de seleção estilo Cesta de Etiquetas (Tokens)."""
    
    # 1. Área de "Cesta" (O que já está selecionado)
    if group.clients:
        st.markdown("<p style='font-size: 0.9rem; font-weight: 500; margin-bottom: 0.2rem; color: var(--text-color);'>Na Planilha:</p>", unsafe_allow_html=True)
        # Usamos pílulas (pills) para mostrar e permitir remoção
        if hasattr(st, "pills"):
            selected_to_remove = st.pills(
                "Remover clientes da seleção",
                options=group.clients,
                default=[], # Nada selecionado para remover inicialmente
                key=f"pill_remove_v2_{group.id}",
                label_visibility="collapsed"
            )
            # Se o usuário clicar em uma pílula, ela entra em selected_to_remove
            if selected_to_remove:
                for client_to_remove in selected_to_remove:
                     update_group_clients(group.id, client_to_remove, False)
                st.rerun()
        else:
             # Fallback visual caso não tenha pills
             st.markdown(f"<div style='padding: 10px; background: rgba(0, 180, 216, 0.1); border-radius: 8px; border: 1px solid rgba(0, 180, 216, 0.2); font-size: 0.85rem; margin-bottom: 10px;'><b>Selecionados ({len(group.clients)}):</b> {', '.join(group.clients)}</div>", unsafe_allow_html=True)
             if st.button("🧹 Limpar todos os selecionados", key=f"clear_all_v2_{group.id}", help="Remove todos os clientes escolhidos"):
                  clear_group_clients(group.id)
                  st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Área de Busca
    search_index = build_search_index(available_clients)
    
    search_term = st.text_input(
        "Buscar cliente para adicionar...", 
        key=f"search_cli_v2_{group.id}", 
        placeholder="🔍 Digite parte do nome da empresa para buscar variações..."
    )
    
    filtered_clients = filter_values(search_term, search_index) if search_term else []
    
    # Remove os que já estão selecionados da lista de resultados
    unselected_clients = [c for c in filtered_clients if c not in group.clients]

    # 3. Resultados da Busca (Botões de Adição Rápida)
    if not search_term:
        st.caption("Digite acima para encontrar e adicionar clientes.")
    elif not unselected_clients:
        st.info("Nenhuma variação nova encontrada para esta busca.")
    else:
        st.markdown("<p style='font-size: 0.9rem; font-weight: 500; margin-bottom: 0.5rem; color: var(--text-color); margin-top: 1rem;'>Resultados da Busca (Clique para adicionar):</p>", unsafe_allow_html=True)
        
        # Botão de adicionar em lote (útil para as variações)
        if len(unselected_clients) > 1:
             if st.button(f"✨ Adicionar todas as {len(unselected_clients)} variações encontradas", key=f"add_all_search_{group.id}", type="secondary"):
                  # Adiciona apenas os filtrados que não estavam na lista
                  select_clients(group.id, group.clients + unselected_clients)
                  st.rerun()
                  
        st.markdown("<div style='max-height: 200px; overflow-y: auto; padding-right: 10px;'>", unsafe_allow_html=True)
        # Exibe os resultados como minúsculos botões em fluxo
        for client in unselected_clients:
             # st.button retorna True no exato momento do clique
             if st.button(f"+ {client}", key=f"add_btn_{group.id}_{safe_key(client)}", use_container_width=True):
                 update_group_clients(group.id, client, True)
                 st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def _render_period_selector_v2(group: Group, available_periods: List[str]) -> None:
    """Substitui o st.multiselect por st.pills (botões amigáveis)."""
    # Mapeia os períodos reais para lables bonitos para o usuário
    options = available_periods
    format_func = format_period_label
    
    st.markdown("<p style='font-size: 0.9rem; opacity: 0.8;'>Clique nos botões abaixo para selecionar múltiplas datas:</p>", unsafe_allow_html=True)

    # st.pills está disponível no Streamlit 1.40+ e é perfeito para design da Apple
    if hasattr(st, "pills"):
        new_periods = st.pills(
            "Selecione os períodos",
            options=options,
            default=group.periods,
            format_func=format_func,
            selection_mode="multi",
            key=f"pill_periods_v2_{group.id}",
            label_visibility="collapsed"
        )
        if new_periods != group.periods:
            update_group_periods(group.id, list(new_periods))
            st.rerun()  # Forçar re-render para atualizar o botão de gerar
    else:
        # Fallback caso a versão do ST seja mais antiga que 1.40
        new_periods = st.multiselect(
            "Períodos", 
            options=options,
            default=group.periods,
            format_func=format_func,
            key=f"multi_periods_v2_{group.id}",
            label_visibility="collapsed"
        )
        if new_periods != group.periods:
            update_group_periods(group.id, new_periods)
            st.rerun()  # Forçar re-render para atualizar o botão de gerar

def _render_record_preview_v2(group: Group, orch: Any) -> None:
    """Um resumo minimalista de "pronto para gerar?"."""
    if group.clients and group.periods:
        count = orch.count_filtered(group.clients, group.periods)
        st.success(f"**Pronto:** {count} linhas de faturamento encontradas e prontas para exportação.", icon="🎯")
    else:
        st.info("👆 Selecione pelo menos 1 cliente e 1 período para prosseguir.", icon="⏳")


def render_generation_button_v2(orch: Any) -> None:
    """Botão primário gigante no final (idêntico à lógica do V1, só design V2)."""
    valid_groups = [g for g in st.session_state.groups if g.clients and g.periods]
    
    if not valid_groups:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.button("⚡ Gerar Planilhas Selecionadas", type="primary", use_container_width=True, disabled=True)
        return

    # 1. Verificar faturas incompletas em todos os grupos
    alerts = []
    total_incomplete = 0
    total_complete = 0
    for g in valid_groups:
        incomplete_info = orch.check_incomplete_rows(g.clients, g.periods)
        inc = incomplete_info["registros_incompletos"]
        total_incomplete += inc
        total_complete += incomplete_info["total_registros"] - inc
        if inc > 0:
            alerts.append({
                "group_name": g.name,
                "count": inc,
                "details": incomplete_info["ucs_afetadas"]
            })
    
    incomplete_filter = "all"
    if alerts:
        with st.container(border=True):
            st.warning(f"⚠ **{total_incomplete}** faturas sem vencimento detectadas ({total_complete} completas).")
            
            for alert in alerts:
                with st.expander(f"No arquivo '{alert['group_name']}', faltam {alert['count']} datas"):
                    st.dataframe(alert["details"], use_container_width=True)
            
            st.markdown("<p style='font-weight: 600; margin-bottom: 5px;'>Como deseja gerar?</p>", unsafe_allow_html=True)
            total_all = total_incomplete + total_complete
            incomplete_filter = st.radio(
                "Modo de geração",
                options=["all", "complete_only", "incomplete_only"],
                format_func=lambda x: {
                    "all": f"📋 Tudo ({total_all} registros — inclui incompletos)",
                    "complete_only": f"✅ Somente Completos ({total_complete} registros)",
                    "incomplete_only": f"⚠️ Somente Incompletos ({total_incomplete} registros)"
                }[x],
                index=0,
                key="v2_incomplete_filter",
                label_visibility="collapsed"
            )

    # 2. Botão de geração
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🪄 Criar Planilha(s) Agora", type="primary", use_container_width=True):
        start_time = time.time()
        
        if len(valid_groups) == 1:
            _generate_single_v2(valid_groups[0], orch, start_time, incomplete_filter)
        else:
            _generate_multiple_v2(valid_groups, orch, start_time, incomplete_filter)


def _generate_single_v2(group: Group, orch: Any, start_time: float, incomplete_filter: str = "all") -> None:
    with st.spinner("Processando... Quase pronto!"):
        excel_data = orch.generate(group.clients, group.periods, incomplete_filter=incomplete_filter)
    
    elapsed = time.time() - start_time
    
    if excel_data:
        filename = f"{sanitize_filename(group.name)}.xlsx"
        st.success(f"Tudo Certo! Arquivo **{filename}** gerado em {elapsed:.1f} segundos.", icon="🎉")
        st.download_button(
            label="⬇️ Baixar Excel (.xlsx)",
            data=excel_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
    else:
        st.warning("Nenhum dado encontrado para gerar a planilha com os filtros aplicados.")


def _generate_multiple_v2(valid_groups: List[Group], orch: Any, start_time: float, incomplete_filter: str = "all") -> None:
    with st.spinner(f"Processando múltiplos arquivos..."):
        groups_payload = [
            {"name": sanitize_filename(g.name), "clients": g.clients, "periods": g.periods}
            for g in valid_groups
        ]
        zip_data = orch.generate_multiple(groups_payload, incomplete_filter=incomplete_filter)
    
    elapsed = time.time() - start_time
    
    if zip_data:
        st.success(f"Tudo Certo! O lote com as planilhas foi criado em arquivos (.zip)", icon="🎉")
        st.download_button(
            label="⬇️ Baixar Lote Compactado (.zip)",
            data=zip_data,
            file_name="Memoria_De_Calculo_Lote.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary"
        )
    else:
        st.warning("Nenhum dado encontrado.")
