import sys
from unittest.mock import MagicMock

from streamlit.testing.v1 import AppTest

sys.modules["firebase_admin"] = MagicMock()
sys.modules["firebase_admin.credentials"] = MagicMock()
sys.modules["firebase_admin.storage"] = MagicMock()
sys.modules["firebase_admin.firestore"] = MagicMock()

from ui.state.group_state import GroupState
from ui.viewmodels.admin_viewmodel import AdminViewModel


def _render_admin_test_app():
    from ui.admin import render_admin_panel

    render_admin_panel()


def _render_wizard_test_app(available_clients, available_periods, orch):
    from ui.groups_wizard_ui import render_groups_section_wizard

    render_groups_section_wizard(available_clients, available_periods, orch)


class FakeOrchestrator:
    def __init__(self):
        self.generate_calls = 0

    def count_filtered(self, clients, periods):
        return 3

    def check_incomplete_rows(self, clients, periods):
        return {
            "total_registros": 3,
            "registros_incompletos": 1,
            "ucs_afetadas": [
                {"no_uc": "UC001", "referencia": "01/2026", "razao_social": "Cliente A"}
            ],
        }

    def generate(self, clients, periods, **kwargs):
        self.generate_calls += 1
        return b"fake-excel-bytes"


def test_wizard_step_3_generate_smoke(monkeypatch):
    import ui.groups_wizard_ui as wizard_ui

    monkeypatch.setattr(wizard_ui.enrichment_service, "get_all_enrichment_data", lambda: None)
    orch = FakeOrchestrator()

    at = AppTest.from_function(
        _render_wizard_test_app,
        args=(["Cliente A"], ["01/2026"], orch),
    )
    at.session_state["groups"] = [
        GroupState(id=1, name="Projeto Teste", clients=["Cliente A"], periods=["01/2026"])
    ]
    at.session_state["group_counter"] = 1
    at.session_state["active_group_id"] = 1
    at.session_state["wizard_step"] = 3
    at.run()

    generate_button = next(button for button in at.button if button.label == "Gerar Memória de Cálculo")
    generate_button.click().run()

    assert any(metric.value == "3" for metric in at.metric)
    assert any("faturas precisam de atenção" in info.value for info in at.info)
    assert any("Planilha pronta em" in toast.value for toast in at.toast)
    assert orch.generate_calls == 1
    assert not at.error
