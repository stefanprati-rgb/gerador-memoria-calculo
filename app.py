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

if os.path.exists(default_mc_path):
    st.sidebar.success(f"Template local encontrado: `{default_mc_path}`")
    template_file = default_mc_path
else:
    template_file = st.sidebar.file_uploader("Upload: Template MC (mc.xlsx)", type=["xlsx"])

# --- LÓGICA PRINCIPAL ---
if base_file and template_file:
    try:
        # Inicializa o Orquestrador
        # Usa um spinner apenas se os métodos pesados forem chamados, mas o init carrega a base toda na mem
        with st.spinner("Carregando base de dados..."):
            orch = Orchestrator(base_file, template_file)
            
        st.subheader("Filtros de Geração")
        
        # Pega as opções
        available_periods = orch.get_available_periods()
        available_clients = orch.get_available_clients()
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_period = st.selectbox(
                "Mês de Referência", 
                options=[""] + available_periods,
                help="Selecione o Mês e Ano de referência para filtrar"
            )
            
        with col2:
            # Multiselect em uma coluna
            selected_clients = st.multiselect(
                "Clientes (Razão Social)", 
                options=available_clients,
                help="Selecione um ou mais clientes. Deixe vazio para processar todos sob os outros critérios."
            )
            
        st.markdown("---")
        
        if st.button("Gerar Planilha", type="primary"):
            if not selected_period:
                st.warning("Por favor, selecione um Mês de Referência obrigatório.")
            else:
                with st.spinner("Gerando arquivo de memória de cálculo..."):
                    
                    excel_data = orch.generate(selected_clients, selected_period)
                    
                    if excel_data:
                        st.success("Planilha gerada com sucesso!")
                        
                        # Define um nome legal para o arquivo
                        if selected_clients and len(selected_clients) == 1:
                            # formata o CNPJ/nome etc ou só pega uma string limpa
                            safe_name = "".join([c if c.isalnum() else "_" for c in selected_clients[0]])
                            filename = f"MC_{safe_name}_{selected_period}.xlsx"
                        else:
                            filename = f"MC_Agrupado_{selected_period}.xlsx"
                            
                        st.download_button(
                            label="📥 Baixar Planilha MC",
                            data=excel_data,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.warning("Nenhum dado encontrado para os filtros informados (Cliente/Período).")
                        
    except Exception as e:
        st.error(f"Erro ao processar as planilhas: {str(e)}")
else:
    st.info("Por favor, garanta que tanto a Base quanto o Template foram providenciados na barra lateral.")
