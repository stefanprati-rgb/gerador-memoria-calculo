import pytest
from unittest.mock import MagicMock, patch

import sys
sys.modules['firebase_admin'] = MagicMock()
sys.modules['firebase_admin.credentials'] = MagicMock()
sys.modules['firebase_admin.storage'] = MagicMock()
sys.modules['firebase_admin.firestore'] = MagicMock()
import firebase_admin
firebase_admin._apps = {}
from ui.viewmodels.admin_viewmodel import AdminViewModel, AdminState
from config.settings import ConfigurationError
from logic.adapters.firebase_adapter import FirebaseAdapterError

@patch('ui.viewmodels.admin_viewmodel.settings')
def test_admin_viewmodel_fatal_error(mock_settings):
    mock_settings.validate_for_runtime.side_effect = ConfigurationError("Erro fatal simulado")
    
    vm = AdminViewModel(mode="production")
    state = vm.get_state()
    
    assert state.fatal_error == "Bloqueio de Segurança Operacional:\nErro fatal simulado"
    assert state.can_sync_local is False

@patch('ui.viewmodels.admin_viewmodel.settings')
def test_admin_viewmodel_warning_and_local(mock_settings):
    mock_settings.validate_for_runtime.return_value = {
        "admin_secure": False,
        "firebase_ready": True,
        "network_ready": True
    }
    mock_settings.network_balanco_path = "caminho_mock"
    
    vm = AdminViewModel(mode="development")
    state = vm.get_state()
    
    assert state.fatal_error is None
    assert "Segurança: A senha" in state.warning_message
    assert state.can_sync_local is True
    assert state.local_path == "caminho_mock"

@patch('ui.viewmodels.admin_viewmodel.FirebaseAdapter')
def test_admin_viewmodel_firebase_success(mock_adapter_class):
    mock_adapter_instance = MagicMock()
    mock_adapter_class.return_value = mock_adapter_instance
    
    vm = AdminViewModel()
    fb, warn = vm._initialize_firebase()
    
    assert fb == mock_adapter_instance
    assert warn is None

@patch('ui.viewmodels.admin_viewmodel.FirebaseAdapter')
def test_admin_viewmodel_firebase_warning(mock_adapter_class):
    mock_adapter_class.side_effect = FirebaseAdapterError("Bucket missing")
    
    vm = AdminViewModel()
    fb, warn = vm._initialize_firebase()
    
    assert fb is None
    assert "Backup na nuvem indisponível: Bucket missing" in warn


def test_admin_viewmodel_process_uploads_uses_sync_service(monkeypatch):
    import logic.services.sync_service as sync_service

    captured = {}

    def fake_build_consolidated_cache_from_uploads(balanco_bytes, gestao_bytes, firebase_adapter):
        captured["balanco_bytes"] = balanco_bytes
        captured["gestao_bytes"] = gestao_bytes
        captured["firebase_adapter"] = firebase_adapter
        return True, None

    monkeypatch.setattr(sync_service, "build_consolidated_cache_from_uploads", fake_build_consolidated_cache_from_uploads)

    vm = AdminViewModel()
    state = AdminState(firebase_adapter="adapter-mock")

    success = vm.process_uploads(b"balanco", b"gestao", state)

    assert success is True
    assert captured == {
        "balanco_bytes": b"balanco",
        "gestao_bytes": b"gestao",
        "firebase_adapter": "adapter-mock",
    }
