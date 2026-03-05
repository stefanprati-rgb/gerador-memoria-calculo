"""
Componentes de UI reutilizáveis para a aplicação Streamlit.
Extraídos de app.py para manter separação de responsabilidades.
"""
import time
import datetime
import streamlit as st
from typing import List


def render_header():
    """Renderiza o cabeçalho estilizado da aplicação."""
    st.markdown("""
<div class="main-header">
    <h1>⚡ Gerador de Memória de Cálculo</h1>
    <p>Automatize a geração de MC a partir da base Balanço Energético e Template de Destino</p>
</div>
""", unsafe_allow_html=True)


def format_period_label(raw_period: str) -> str:
    """Formata '2025-12-01 00:00:00' para '2025/Dez'."""
    try:
        dt = datetime.datetime.fromisoformat(str(raw_period).split(" ")[0])
        meses = {
            1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
            5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
            9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
        }
        return f"{dt.year}/{meses[dt.month]}"
    except Exception:
        return str(raw_period)


def render_sidebar_metrics(available_clients: List[str], available_periods: List[str], total_records: int):
    """Renderiza as métricas resumo na sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Resumo da Base")
    col_m1, col_m2 = st.sidebar.columns(2)
    col_m1.metric("Clientes", len(available_clients))
    col_m2.metric("Períodos", len(available_periods))
    st.sidebar.metric("Registros Totais", f"{total_records:,}".replace(",", "."))


def _render_group_card(group: dict, index: int, available_clients: List[str], available_periods: List[str], orch):
    """Renderiza um card individual de grupo com seleção de clientes e períodos."""
    has_clients = bool(group.get('clients'))
    has_periods = bool(group.get('periods'))
    is_complete = has_clients and has_periods

    with st.expander(f"📋 {group['name']}  —  {'✅ Pronto' if is_complete else '⚠️ Incompleto'}", expanded=(index == 0)):
        # Nome do grupo + botão remover
        col_name, col_btn = st.columns([0.9, 0.1])
        with col_name:
            group['name'] = st.text_input(
                f"Nome do Arquivo", 
                value=group['name'], 
                key=f"name_{group['id']}",
                label_visibility="collapsed",
                placeholder="Nome do arquivo de saída..."
            )
        with col_btn:
            if len(st.session_state.groups) > 1:
                if st.button("🗑️", key=f"del_{group['id']}", help="Remover grupo"):
                    st.session_state.groups = [g for g in st.session_state.groups if g['id'] != group['id']]
                    st.rerun()

        # Clientes: seleção + atalhos
        st.markdown("**Clientes**")
        col_sel_all_cli, col_clear_cli = st.columns([1, 1])
        with col_sel_all_cli:
            if st.button("✅ Selecionar Todos", key=f"all_cli_{group['id']}", use_container_width=True):
                group['clients'] = list(available_clients)
                st.rerun()
        with col_clear_cli:
            if st.button("🧹 Limpar", key=f"clear_cli_{group['id']}", use_container_width=True):
                group['clients'] = []
                st.rerun()
        
        group['clients'] = st.multiselect(
            "Clientes:", 
            options=available_clients,
            default=group['clients'],
            key=f"clients_{group['id']}",
            label_visibility="collapsed"
        )

        # Períodos: seleção + atalhos
        st.markdown("**Períodos de Referência**")
        col_sel_all_per, col_clear_per = st.columns([1, 1])
        with col_sel_all_per:
            if st.button("✅ Selecionar Todos", key=f"all_per_{group['id']}", use_container_width=True):
                group['periods'] = list(available_periods)
                st.rerun()
        with col_clear_per:
            if st.button("🧹 Limpar", key=f"clear_per_{group['id']}", use_container_width=True):
                group['periods'] = []
                st.rerun()

        group['periods'] = st.multiselect(
            "Períodos de Referência:", 
            options=available_periods,
            default=group.get('periods', []),
            format_func=format_period_label,
            key=f"periods_{group['id']}",
            label_visibility="collapsed"
        )

        # Preview da contagem de registros
        if group['clients'] and group['periods']:
            count = orch.count_filtered(group['clients'], group['periods'])
            st.markdown(
                f'<p class="record-preview">📄 Filtro atual: <strong>{count}</strong> registros encontrados</p>',
                unsafe_allow_html=True
            )
        elif group['clients'] or group['periods']:
            st.markdown(
                '<p class="record-preview">Selecione clientes <strong>e</strong> períodos para ver a prévia</p>',
                unsafe_allow_html=True
            )


def render_groups_section(available_clients: List[str], available_periods: List[str], orch):
    """Renderiza a seção completa de configuração de grupos."""
    st.subheader("Configuração de Grupos de Emissão")
    st.caption("Crie grupos para definir quais clientes e períodos sairão juntos em uma planilha separada.")
    st.markdown("---")

    # Gerenciamento de estado dos grupos
    if 'groups' not in st.session_state:
        st.session_state.groups = [{"id": 1, "name": "Grupo_1", "clients": [], "periods": []}]
    if 'group_counter' not in st.session_state:
        st.session_state.group_counter = 1

    def add_group():
        st.session_state.group_counter += 1
        st.session_state.groups.append({
            "id": st.session_state.group_counter, 
            "name": f"Grupo_{st.session_state.group_counter}", 
            "clients": [],
            "periods": []
        })

    # Exibir a interface para cada grupo
    for i, group in enumerate(st.session_state.groups):
        _render_group_card(group, i, available_clients, available_periods, orch)

    st.button("➕ Adicionar Novo Grupo", on_click=add_group, use_container_width=False)
    st.markdown("---")


def render_generation_button(orch):
    """Renderiza o botão de geração e lida com download de resultados."""
    if st.button("⚡ Gerar Planilhas Selecionadas", type="primary", use_container_width=True):
        valid_groups = [g for g in st.session_state.groups if g['clients'] and g['periods']]
        
        if not valid_groups:
            st.warning("É necessário que pelo menos um grupo tenha Clientes e Períodos selecionados.")
            return

        start_time = time.time()
        
        # Se houver apenas 1 grupo, gera o Excel direto
        if len(valid_groups) == 1:
            with st.spinner("Processando planilha..."):
                grp = valid_groups[0]
                excel_data = orch.generate(grp['clients'], grp['periods'])
            
            elapsed = time.time() - start_time
            
            if excel_data:
                safe_name = "".join([c if c.isalnum() else "_" for c in grp['name']])
                filename = f"{safe_name}.xlsx"
                
                st.toast(f"✅ Planilha gerada em {elapsed:.1f}s!", icon="⚡")
                st.balloons()
                st.success(f"Planilha **{filename}** gerada com sucesso!")
                st.download_button(
                    label="📥 Baixar Arquivo Gerado",
                    data=excel_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.warning("Nenhum dado encontrado para gerar a planilha com os filtros aplicados.")
                
        # Se houver múltiplos grupos, usa generate_multiple do Orchestrator
        else:
            with st.spinner(f"Gerando {len(valid_groups)} planilhas em lote..."):
                groups_payload = [
                    {"name": g['name'], "clients": g['clients'], "periods": g['periods']}
                    for g in valid_groups
                ]
                zip_data = orch.generate_multiple(groups_payload)
            
            elapsed = time.time() - start_time
            
            if zip_data:
                st.toast(f"✅ {len(valid_groups)} planilhas geradas em {elapsed:.1f}s!", icon="📦")
                st.balloons()
                st.success(f"**{len(valid_groups)} planilhas** geradas e empacotadas com sucesso!")
                st.download_button(
                    label="📦 Baixar Lote (ZIP)",
                    data=zip_data,
                    file_name="Memoria_De_Calculo_Lote.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            else:
                st.warning("Nenhum dado encontrado para gerar as planilhas com os filtros aplicados.")
