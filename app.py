import streamlit as st
import os
from src.services.orchestrator import Orchestrator

# Configuração da página
st.set_page_config(
    page_title="Memória de Cálculo - Gerador",
    page_icon="📄",
    layout="wide"
)

st.title("Gerador de Memória de Cálculo 📄")
st.markdown("Automatize a geração de MC a partir da base Geração GD e Template de Destino.")

# --- BARRA LATERAL ---
st.sidebar.header("📁 Arquivos")

# Para o Streamlit Cloud, permitiremos o upload. Mas localmente podemos pré-carregar
# se estiver na pasta, para agilizar testes.
default_base_path = "gd_gestao_cobranca-1771957245_2026-02-24.xlsx"
default_mc_path = "mc.xlsx"

base_file = None
template_file = None

if os.path.exists(default_base_path):
    st.sidebar.success(f"Base local encontrada: `{default_base_path}`")
    base_file = default_base_path
else:
    base_file = st.sidebar.file_uploader("Upload: Base Geração (gd_gestao_cobranca.xlsx)", type=["xlsx"])

template_file = "mc.xlsx"
if not os.path.exists(template_file):
    st.sidebar.error("❌ ERRO: Template 'mc.xlsx' não encontrado na raiz do sistema.")
    st.stop()

# --- LÓGICA PRINCIPAL ---
if base_file and template_file:
    try:
        with st.spinner("Carregando base de dados..."):
            orch = Orchestrator(base_file, template_file)
            
        st.subheader("Configuração de Grupos de Emissão")
        st.markdown("Crie grupos para definir quais clientes sairão juntos em uma planilha separada.")
        
        available_periods = orch.get_available_periods()
        available_clients = orch.get_available_clients()
        
        # Mês é universal para a geração
        selected_period = st.selectbox(
            "Mês de Referência Global", 
            options=[""] + available_periods,
            help="Selecione o Mês e Ano de referência para gerar as faturas."
        )
        
        st.markdown("---")
        
        # Gerenciamento de estado dos grupos
        if 'groups' not in st.session_state:
            # Inicializa com 1 grupo padrão
            st.session_state.groups = [{"id": 1, "name": "Grupo_1", "clients": []}]
        if 'group_counter' not in st.session_state:
            st.session_state.group_counter = 1
            
        def add_group():
            st.session_state.group_counter += 1
            st.session_state.groups.append({
                "id": st.session_state.group_counter, 
                "name": f"Grupo_{st.session_state.group_counter}", 
                "clients": []
            })
            
        def remove_group(group_id):
            st.session_state.groups = [g for g in st.session_state.groups if g['id'] != group_id]

        # Exibir a interface para cada grupo
        for i, group in enumerate(st.session_state.groups):
            with st.container(border=True):
                col_name, col_btn = st.columns([0.9, 0.1])
                with col_name:
                    # Atualiza o nome do grupo no state
                    group['name'] = st.text_input(
                        f"Nome do Arquivo {i+1}", 
                        value=group['name'], 
                        key=f"name_{group['id']}"
                    )
                with col_btn:
                    st.write("")
                    st.write("")
                    # Botão para remover grupo (desabilitado se houver só 1)
                    if len(st.session_state.groups) > 1:
                        if st.button("🗑️", key=f"del_{group['id']}", help="Remover grupo"):
                            remove_group(group['id'])
                            st.rerun()

                # Atualiza a lista de clientes no state
                group['clients'] = st.multiselect(
                    "Clientes incluídos no arquivo:", 
                    options=available_clients,
                    default=group['clients'],
                    key=f"clients_{group['id']}"
                )

        st.button("➕ Adicionar Novo Grupo", on_click=add_group)
            
        st.markdown("---")
        
        if st.button("Gerar Planilhas Selecionadas", type="primary", use_container_width=True):
            if not selected_period:
                st.warning("Por favor, selecione um Mês de Referência Global.")
            else:
                # Validar grupos vazios
                valid_groups = {g['name']: g['clients'] for g in st.session_state.groups if g['clients']}
                
                if not valid_groups:
                    st.warning("É necessário que pelo menos um grupo tenha clientes selecionados.")
                else:
                    with st.spinner("Processando planilhas..."):
                        
                        # Se houver apenas 1 grupo, gera o Excel direto
                        if len(valid_groups) == 1:
                            group_name, clients = list(valid_groups.items())[0]
                            excel_data = orch.generate(clients, selected_period)
                            
                            if excel_data:
                                safe_name = "".join([c if c.isalnum() else "_" for c in group_name])
                                filename = f"MC_{safe_name}_{selected_period}.xlsx"
                                
                                st.success("Planilha gerada com sucesso!")
                                st.download_button(
                                    label="📥 Baixar Arquivo Gerado",
                                    data=excel_data,
                                    file_name=filename,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                            else:
                                st.warning("Nenhum dado encontrado para gerar a planilha.")
                                
                        # Se houver múltiplos grupos, empacota em zip
                        else:
                            zip_data = orch.generate_multiple(valid_groups, selected_period)
                            
                            if zip_data:
                                st.success(f"{len(valid_groups)} planilhas geradas e empacotadas com sucesso!")
                                st.download_button(
                                    label="📦 Baixar Lote (ZIP)",
                                    data=zip_data,
                                    file_name=f"Memoria_De_Calculo_Lote_{selected_period}.zip",
                                    mime="application/zip"
                                )
                            else:
                                st.warning("Nenhum dado encontrado para gerar as planilhas.")
                        
    except Exception as e:
        st.error(f"Erro ao processar as planilhas: {str(e)}")
else:
    st.info("Por favor, garanta que tanto a Base quanto o Template foram providenciados na barra lateral.")
