import pytest
import os
import uuid
import shutil
from pathlib import Path
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
    with pytest.raises(ConfigurationError, match="FIREBASE_STORAGE_BUCKET e uma credencial Firebase válida"):
        s.validate_for_runtime(mode="production")

def test_settings_network_ready():
    # Evita tmp_path do pytest (ambientes Windows/sandbox podem bloquear diretórios temporários).
    base = Path(os.getcwd()) / ".pytest_tmp_cfg" / f"cfg_{uuid.uuid4().hex[:8]}"
    base.mkdir(parents=True, exist_ok=True)
    try:
        f = base / "teste_balanco.xlsm"
        f.write_bytes(b"")

        cred = base / "cred.json"
        cred.write_text("{}", encoding="utf-8")

        s = Settings(
            admin_password="senha_forte",
            firebase_storage_bucket="bkt",
            firebase_credentials_path=str(cred),
            NETWORK_SHARE_PATH=str(f),
        )
        status = s.validate_for_runtime(mode="production")

        assert status["network_ready"] is True
        assert status["admin_secure"] is True
        assert status["firebase_ready"] is True
    finally:
        shutil.rmtree(base, ignore_errors=True)

def test_settings_network_not_ready():
    s = Settings(NETWORK_SHARE_PATH="/caminho/fake/que/nao/existe")
    status = s.validate_for_runtime(mode="development")
    assert status["network_ready"] is False


def test_settings_firebase_ready_via_fallback(monkeypatch):
    s = Settings(admin_password="senha_forte", firebase_storage_bucket="bkt")
    monkeypatch.setattr(s, "_has_firebase_credentials_source", lambda: True)
    status = s.validate_for_runtime(mode="production")
    assert status["firebase_ready"] is True
