import pytest
import os
from config.settings import Settings, ConfigurationError

def test_settings_default_insecure():
    # Deve falhar em modo produção
    s = Settings(admin_password="mudar_aqui", firebase_storage_bucket="dummy")
    with pytest.raises(ConfigurationError, match="inseguro padrão"):
        s.validate_for_runtime(mode="production")
        
    # Mas em dev apenas retorna o status sem exception
    status = s.validate_for_runtime(mode="development")
    assert status["admin_secure"] is False

def test_settings_firebase_missing_prod():
    s = Settings(admin_password="senha_forte_segura", firebase_storage_bucket=None)
    with pytest.raises(ConfigurationError, match="FIREBASE_STORAGE_BUCKET e FIREBASE_CREDENTIALS_PATH são obrigatórios"):
        s.validate_for_runtime(mode="production")

def test_settings_network_ready(tmp_path):
    # Usando temp path para simular o network_balanco_path
    f = tmp_path / "teste_balanco.xlsm"
    f.touch()
    
    s = Settings(admin_password="senha_forte", firebase_storage_bucket="bkt", firebase_credentials_path="cred.json", NETWORK_SHARE_PATH=str(f))
    status = s.validate_for_runtime(mode="production")
    
    assert status["network_ready"] is True
    assert status["admin_secure"] is True
    assert status["firebase_ready"] is True

def test_settings_network_not_ready():
    s = Settings(NETWORK_SHARE_PATH="/caminho/fake/que/nao/existe")
    status = s.validate_for_runtime(mode="development")
    assert status["network_ready"] is False
