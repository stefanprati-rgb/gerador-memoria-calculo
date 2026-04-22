from dataclasses import dataclass
from typing import Optional, Dict
from config.settings import settings, ConfigurationError
from logic.adapters.firebase_adapter import FirebaseAdapter, FirebaseAdapterError

@dataclass
class AdminState:
    fatal_error: Optional[str] = None
    warning_message: Optional[str] = None
    can_sync_local: bool = False
    local_path: Optional[str] = None
    firebase_adapter: Optional[FirebaseAdapter] = None
    firebase_warning: Optional[str] = None

class AdminViewModel:
    def __init__(self, mode: str = "development"):
        self.mode = mode

    def get_state(self) -> AdminState:
        """
        Calcula o estado do painel admin sem depender do Streamlit.
        Avalia configurações, ambiente e conectividade.
        """
        state = AdminState()

        # 1. Validação do Runtime
        try:
            runtime_status = settings.validate_for_runtime(mode=self.mode)
            
            if not runtime_status.get("admin_secure"):
                state.warning_message = "Segurança: A senha de administrador está usando o valor padrão inseguro ('mudar_aqui'). Configure a variável ADMIN_PASSWORD."
                
            # 2. Sync Local
            if runtime_status.get("network_ready"):
                state.can_sync_local = True
                state.local_path = settings.network_balanco_path
                
            # 3. Inicializa Firebase no State
            fb, fb_warn = self._initialize_firebase()
            state.firebase_adapter = fb
            state.firebase_warning = fb_warn
                
        except ConfigurationError as e:
            state.fatal_error = f"Bloqueio de Segurança Operacional:\n{e}"
            return state

        return state

    def _initialize_firebase(self) -> tuple[Optional[FirebaseAdapter], Optional[str]]:
        """
        Tenta inicializar o Firebase. Retorna a instância e/ou uma mensagem de aviso.
        """
        try:
            fb = FirebaseAdapter(settings.firebase_credentials_path, settings.firebase_storage_bucket)
            return fb, None
        except FirebaseAdapterError as e:
            return None, f"Backup na nuvem indisponível: {e}"
        except Exception as e:
            return None, f"Erro inesperado no adaptador Firebase: {e}"

    def process_uploads(self, balanco_bytes: bytes, gestao_bytes: bytes, state: AdminState) -> bool:
        """Processa os uploads de arquivos em cache e opcionalmente no Firebase."""
        from logic.services.orchestrator import build_consolidated_cache_from_uploads
        success, _ = build_consolidated_cache_from_uploads(balanco_bytes, gestao_bytes, state.firebase_adapter)
        return success
