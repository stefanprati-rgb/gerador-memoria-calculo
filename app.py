import streamlit as st
import os
import glob
import time
from config.settings import settings
from logic.core.logging_config import setup_logging
from logic.services.orchestrator import Orchestrator
from logic.adapters.excel_adapter import ColumnValidationError, HeaderNotFoundError

from logic.services.sync_service import PARQUET_FILE, get_cache_update_time, build_consolidated_cache_from_uploads
from logic.adapters.firebase_adapter import FirebaseAdapter

# Inicializar logging
setup_logging(settings.log_level)

# Configuração da página
st.set_page_config(
    page_title="Memória de Cálculo - Gerador",
    page_icon="⚡",
    layout="wide"
)

# --- CSS CUSTOMIZADO ---
st.markdown("""
<style>
    /* Importar fonte Inter do Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Reset geral de tipografia */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Cabeçalho principal estilizado */
    .main-header {
        background: linear-gradient(135deg, #0f4c75 0%, #1b7fa3 50%, #00b4d8 100%);
        padding: 1.8rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
        box-shadow: 0 4px 20px rgba(15, 76, 117, 0.25);
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    .main-header p {
        margin: 0.4rem 0 0 0;
        opacity: 0.85;
        font-size: 0.95rem;
        font-weight: 300;
    }

    /* Sidebar refinada */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f0f4f8 0%, #e2e8f0 100%);
    }
    section[data-testid="stSidebar"] .stMetric {
        background: white;
        padding: 0.7rem 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        border-left: 3px solid #0f4c75;
    }

    /* Botão principal — gradiente verde/azul */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0f4c75 0%, #00b4d8 100%) !important;
        border: none !important;
        font-weight: 600 !important;
        letter-spacing: 0.02em;
        padding: 0.7rem 1.5rem !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 14px rgba(0, 180, 216, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(0, 180, 216, 0.45) !important;
        transform: translateY(-1px);
    }

    /* Badge de status dos grupos */
    .group-badge-ready {
        display: inline-block;
        background: #d4edda;
        color: #155724;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 500;
    }
    .group-badge-incomplete {
        display: inline-block;
        background: #fff3cd;
        color: #856404;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 500;
    }

    /* Preview de registros */
    .record-preview {
        font-size: 0.82rem;
        color: #64748b;
        padding: 0.3rem 0;
        font-weight: 400;
    }
    .record-preview strong {
        color: #0f4c75;
        font-weight: 600;
    }

    /* Botão adicionar grupo */
    div.stButton > button:not([kind="primary"]) {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }

    /* Separador suave */
    hr {
        border: none;
        border-top: 1px solid #e2e8f0;
        margin: 1.2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ESTILIZADO ---
st.markdown("""
<div class="main-header">
    <h1>⚡ Gerador de Memória de Cálculo</h1>
    <p>Automatize a geração de MC a partir da base Balanço Energético e Template de Destino</p>
</div>
""", unsafe_allow_html=True)

# --- BARRA LATERAL ---
st.sidebar.header("📁 Arquivos")

# --- ÁREA ADMINISTRATIVA ---
with st.sidebar.expander("⚙️ Atualizar Bases (Admin)", expanded=False):
    admin_senha = st.text_input("Senha Admin", type="password")
    if admin_senha == "admin123":
        st.markdown("**1. Carregue as planilhas atualizadas:**")
        balanco_up = st.file_uploader("Balanço Energético (.xlsm)", type=["xlsm", "xlsx"])
        gestao_up = st.file_uploader("Gestão Cobrança (.xlsx)", type=["xlsx"])
        
        if st.button("Sincronizar e Processar", use_container_width=True):
            if balanco_up:
                with st.spinner("Processando e cruzando dados. Isso pode levar alguns minutos..."):
                    # Tentar inicializar Firebase para backup (opcional)
                    fb = None
                    try:
                        fb = FirebaseAdapter(settings.firebase_credentials_path, settings.firebase_storage_bucket)
                        if fb._app is None:
                            fb = None
                    except Exception:
                        fb = None
                    
                    # Processar localmente (Local First) + backup opcional no Firebase
                    gestao_bytes = gestao_up.getvalue() if gestao_up else None
                    if build_consolidated_cache_from_uploads(balanco_up.getvalue(), gestao_bytes, fb):
                        st.cache_resource.clear()
                        st.success("✅ Bases processadas com sucesso!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Erro interno ao gerar o cache consolidado. Verifique os logs.")
            else:
                st.warning("⚠️ O Balanço Energético (.xlsm) é obrigatório. A Gestão Cobrança (.xlsx) é opcional.")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**⚡ Status da Base Consolidada**  \nAtualizada em: `{get_cache_update_time()}`")

# Determinar base ativa (Preferência total pelo Cloud Cache)
if os.path.exists(PARQUET_FILE):
    base_file = PARQUET_FILE
else:
    # Fallback apenas para uso local/desenvolvimento
    base_matches = sorted(glob.glob(settings.base_file_pattern), reverse=True)
    base_file = base_matches[0] if base_matches else None
    
    if not base_file:
        st.sidebar.error("Base Cacheada vazia. Acione a ⚙️ Área Administrativa.")
        st.stop()

template_file = settings.template_file
if not os.path.exists(template_file):
    st.sidebar.error("❌ ERRO: Template 'mc.xlsx' não encontrado na raiz do sistema.")
    st.stop()

# --- LÓGICA PRINCIPAL ---

@st.cache_resource(show_spinner="Carregando base de dados...")
def load_orchestrator(base_path: str, template_path: str, sheet: str):
    """Cria o Orchestrator cacheado para evitar releitura da planilha em cada rerun."""
    return Orchestrator(base_path, template_path, sheet_name=sheet)

if base_file and template_file:
    try:
        orch = load_orchestrator(base_file, template_file, settings.base_sheet_name)
            
        available_periods = orch.get_available_periods()
        available_clients = orch.get_available_clients()

        # --- Métricas na Sidebar ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("📊 Resumo da Base")
        col_m1, col_m2 = st.sidebar.columns(2)
        col_m1.metric("Clientes", len(available_clients))
        col_m2.metric("Períodos", len(available_periods))
        st.sidebar.metric("Registros Totais", f"{len(orch.reader.df):,}".replace(",", "."))

        # --- Área principal: Configuração de Grupos ---       
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
            
        def remove_group(group_id):
            st.session_state.groups = [g for g in st.session_state.groups if g['id'] != group_id]

        # Exibir a interface para cada grupo
        for i, group in enumerate(st.session_state.groups):
            # Determinar status do grupo para badge
            has_clients = bool(group.get('clients'))
            has_periods = bool(group.get('periods'))
            is_complete = has_clients and has_periods
            
            if is_complete:
                badge = f'<span class="group-badge-ready">✅ Pronto — {len(group["clients"])} clientes, {len(group["periods"])} períodos</span>'
            elif has_clients or has_periods:
                missing = "períodos" if not has_periods else "clientes"
                badge = f'<span class="group-badge-incomplete">⚠️ Faltam {missing}</span>'
            else:
                badge = f'<span class="group-badge-incomplete">⚠️ Incompleto</span>'
            
            with st.expander(f"📋 {group['name']}  —  {'✅ Pronto' if is_complete else '⚠️ Incompleto'}", expanded=(i == 0)):
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
                            remove_group(group['id'])
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

        st.button("➕ Adicionar Novo Grupo", on_click=add_group, use_container_width=False)
            
        st.markdown("---")
        
        if st.button("⚡ Gerar Planilhas Selecionadas", type="primary", use_container_width=True):
            # Validar grupos vazios ou sem período
            valid_groups = [g for g in st.session_state.groups if g['clients'] and g['periods']]
            
            if not valid_groups:
                st.warning("É necessário que pelo menos um grupo tenha Clientes e Períodos selecionados.")
            else:
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
                        
                # Se houver múltiplos grupos, empacota em zip com progress bar
                else:
                    progress_bar = st.progress(0, text="Iniciando geração em lote...")
                    
                    # Gerar individualmente para atualizar progresso
                    import zipfile
                    import io
                    
                    zip_buffer = io.BytesIO()
                    generated_count = 0
                    
                    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                        for idx, grp in enumerate(valid_groups):
                            progress = (idx + 1) / len(valid_groups)
                            progress_bar.progress(progress, text=f"Gerando {grp['name']}... ({idx+1}/{len(valid_groups)})")
                            
                            excel_bytes = orch.generate(grp['clients'], grp['periods'])
                            if excel_bytes:
                                fname = grp['name'] if grp['name'].endswith(".xlsx") else f"{grp['name']}.xlsx"
                                zip_file.writestr(fname, excel_bytes)
                                generated_count += 1
                    
                    progress_bar.empty()
                    elapsed = time.time() - start_time
                    
                    if generated_count > 0:
                        st.toast(f"✅ {generated_count} planilhas geradas em {elapsed:.1f}s!", icon="📦")
                        st.balloons()
                        st.success(f"**{generated_count} planilhas** geradas e empacotadas com sucesso!")
                        st.download_button(
                            label="📦 Baixar Lote (ZIP)",
                            data=zip_buffer.getvalue(),
                            file_name="Memoria_De_Calculo_Lote.zip",
                            mime="application/zip",
                            use_container_width=True,
                        )
                    else:
                        st.warning("Nenhum dado encontrado para gerar as planilhas com os filtros aplicados.")

    except HeaderNotFoundError as e:
        st.error(f"🔍 Não foi possível detectar o cabeçalho na planilha: {e}")
    except ColumnValidationError as e:
        st.error(f"⚠️ Problema nas colunas da planilha: {e}")
    except FileNotFoundError as e:
        st.error(f"📁 Arquivo não encontrado: {e}")
    except ValueError as e:
        st.error(f"📊 Problema nos dados da planilha: {e}")
    except Exception as e:
        st.error(f"❌ Erro inesperado: {str(e)}")
else:
    st.info("Por favor, garanta que tanto a Base quanto o Template foram providenciados na barra lateral.")
