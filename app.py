import streamlit as st
import os
import glob
from config.settings import settings
from logic.core.logging_config import setup_logging
from logic.services.orchestrator import Orchestrator
from logic.adapters.excel_adapter import ColumnValidationError, HeaderNotFoundError
from logic.services.sync_service import PARQUET_FILE, get_cache_update_time

from ui.styles import inject_styles
from ui.header import render_header
from ui.sidebar import render_sidebar_metrics
from ui.groups_ui import render_groups_section, render_generation_button
from ui.admin import render_admin_panel

# Inicializar logging
setup_logging(settings.log_level)

# Configuração da página
st.set_page_config(
    page_title="Memória de Cálculo - Gerador",
    page_icon="⚡",
    layout="wide"
)

# --- UI ---
inject_styles()
render_header()

# --- BARRA LATERAL ---
st.sidebar.header("📁 Arquivos")
render_admin_panel()

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
def load_orchestrator_v3(base_path: str, template_path: str, sheet: str):
    """Cria o Orchestrator cacheado para evitar releitura da planilha em cada rerun."""
    return Orchestrator(base_path, template_path, sheet_name=sheet)

if base_file and template_file:
    try:
        orch = load_orchestrator_v3(base_file, template_file, settings.base_sheet_name)
            
        available_periods = orch.get_available_periods()
        available_clients = orch.get_available_clients()

        render_sidebar_metrics(available_clients, available_periods, len(orch.reader.df))
        render_groups_section(available_clients, available_periods, orch)
        render_generation_button(orch)

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
