"""
Configurações centralizadas do projeto Memória de Cálculo.
Carrega valores do .env se existir, permite override por variáveis de ambiente.
"""

from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Configurações do projeto, carregáveis via .env ou variáveis de ambiente."""

    # Padrão glob para encontrar a planilha base automaticamente
    base_file_pattern: str = "Balanco_Energetico*.xlsm"
    
    # Nome da aba a ser lida na planilha base
    base_sheet_name: str = "Balanco Operacional"
    
    # Caminho do template de saída
    template_file: str = "mc.xlsx"
    
    # Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_level: str = "INFO"

    # Senha de acesso ao painel administrativo
    admin_password: str = "admin123"

    # Firebase
    firebase_credentials_path: str = "firebase-credentials.json"
    firebase_storage_bucket: str = "hube-energy.appspot.com" # Exemplo, o usuário vai sobrescrever no .env

    @property
    def network_balanco_path(self) -> str:
        """Caminho absoluto dinâmico baseado no perfil do usuário hospedeiro."""
        base_dir = os.path.expanduser("~")
        return os.path.join(
            base_dir, 
            "GRUPO GERA", 
            "Gestão GDC - Documentos", 
            "RAÍZEN", 
            "05 - Gestao", 
            "Balanco_Energetico_Raizen.xlsm"
        )

    model_config = {
        "env_file": os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# Instância global de configuração
settings = Settings()
