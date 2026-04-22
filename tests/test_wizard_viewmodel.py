import pytest
from unittest.mock import MagicMock
from ui.viewmodels.wizard_viewmodel import WizardViewModel, GenerationPayload
from ui.state.group_state import GroupState

def test_wizard_viewmodel_metrics():
    mock_orch = MagicMock()
    mock_orch.count_filtered.return_value = 100
    mock_orch.check_incomplete_rows.return_value = {
        "total_registros": 100,
        "registros_incompletos": 5,
        "ucs_afetadas": []
    }
    
    vm = WizardViewModel(mock_orch)
    metrics = vm.get_review_metrics(["CLI_A"], ["01/2024"])
    
    assert metrics.total_invoices == 100
    assert metrics.incomplete_count == 5
    assert metrics.complete_count == 95

def test_wizard_viewmodel_empty_metrics():
    mock_orch = MagicMock()
    vm = WizardViewModel(mock_orch)
    metrics = vm.get_review_metrics([], [])
    assert metrics.total_invoices == 0
    mock_orch.count_filtered.assert_not_called()

def test_wizard_viewmodel_payload_single():
    mock_orch = MagicMock()
    vm = WizardViewModel(mock_orch)
    
    group = GroupState(id=1, name="Projeto Alpha", clients=["CLI_A"], periods=["01/2024"])
    payload = vm.prepare_generation_payload(group, "all", None)
    
    assert payload.is_multiplexed is False
    assert payload.filename == "Projeto_Alpha.xlsx"
    assert "spreadsheetml.sheet" in payload.mime_type
    assert payload.clients == ["CLI_A"]
    assert payload.periods == ["01/2024"]

def test_wizard_viewmodel_payload_multiplexed():
    mock_orch = MagicMock()
    vm = WizardViewModel(mock_orch)
    
    group = GroupState(id=1, name="Projeto Alpha", clients=["CLI_A"], periods=["01/2024", "02/2024"])
    payload = vm.prepare_generation_payload(group, "complete_only", None)
    
    assert payload.is_multiplexed is True
    assert payload.filename == "Projeto_Alpha.zip"
    assert "zip" in payload.mime_type
    assert payload.incomplete_filter == "complete_only"
