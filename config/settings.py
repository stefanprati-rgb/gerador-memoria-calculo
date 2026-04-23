"""
Configurações centralizadas do projeto Memória de Cálculo.
Carrega valores do .env se existir, permite override por variáveis de ambiente.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
import os
from typing import Optional, Dict

class ConfigurationError(Exception):
    """Exceção customizada para erros de configuração."""
    pass

class Settings(BaseSettings):
    """Configurações do projeto, carregáveis via .env ou variáveis de ambiente."""

    # Configurações de Arquivos Locais (Obrigatórias na operação offline)
    base_file_pattern: str = Field(default="Balanco_Energetico*.xlsm", description="Padrão glob para encontrar a planilha base automaticamente")
    base_sheet_name: str = Field(default="Balanco Operacional", description="Nome da aba a ser lida na planilha base")
    template_file: str = Field(default="mc.xlsx", description="Caminho do template de saída")
    
    # Logs
    log_level: str = Field(default="INFO", description="Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)")

    # Segurança Admin
    admin_password: str = Field(default="mudar_aqui", description="Senha de acesso ao painel administrativo")

    # Firebase (Opcional para operação offline, obrigatório para produção cloud)
    firebase_credentials_path: Optional[str] = Field(default=None, description="Caminho local ou var ambiente para chave do firebase")
    firebase_storage_bucket: Optional[str] = Field(default=None, description="Nome do bucket de storage no Firebase")

    # Caminho de Rede (Opcional, com fallback vazio)
    network_balanco_path_override: Optional[str] = Field(default=None, description="Caminho estrito definido no .env", validation_alias="NETWORK_SHARE_PATH")

    @property
    def network_balanco_path(self) -> Optional[str]:
        """Retorna o caminho de rede configurado. Não tenta adivinhar pastas do usuário Windows."""
        return self.network_balanco_path_override

    def _has_firebase_credentials_source(self) -> bool:
        """
        Verifica se existe alguma fonte de credencial Firebase disponível:
        1) caminho local configurado e existente
        2) secrets do Streamlit (firebase / firebase_credentials)
        """
        # 1) Arquivo local
        if self.firebase_credentials_path:
            try:
                abs_path = os.path.abspath(self.firebase_credentials_path)
                if os.path.exists(abs_path):
                    return True
            except Exception:
                pass

        # 2) Streamlit secrets (produção cloud)
        try:
            import streamlit as st
            if "firebase" in st.secrets or "firebase_credentials" in st.secrets:
                return True
        except Exception:
            pass

        return False

    def validate_for_runtime(self, mode: str = "production") -> Dict[str, bool]:
        """
        Valida a consistência das configurações baseado no modo de execução.
        Retorna dicionário com o status dos serviços, ou levanta erro grave.
        """
        status = {
            "admin_secure": True,
            "firebase_ready": True,
            "network_ready": False
        }

        # 1. Validação de Segurança Admin (Bloqueia produção se senha for fraca)
        if self.admin_password in ["mudar_aqui", "admin123", "", None]:
            if mode == "production":
                raise ConfigurationError(
                    "A senha do admin (ADMIN_PASSWORD) está com um valor inseguro padrão. "
                    "Configure uma senha forte no ambiente ou no .env para iniciar em produção."
                )
            status["admin_secure"] = False

        # 2. Validação Firebase
        firebase_has_bucket = bool(self.firebase_storage_bucket)
        firebase_has_credentials = self._has_firebase_credentials_source()
        if not firebase_has_bucket or not firebase_has_credentials:
            status["firebase_ready"] = False
            if mode == "production":
                raise ConfigurationError(
                    "FIREBASE_STORAGE_BUCKET e uma credencial Firebase válida "
                    "(arquivo local ou st.secrets) são obrigatórios no modo produção."
                )

        # 3. Caminho de Rede
        if self.network_balanco_path and os.path.exists(self.network_balanco_path):
            status["network_ready"] = True

        return status

    model_config = {
        "env_file": os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

# Instância global de configuração
settings = Settings()
