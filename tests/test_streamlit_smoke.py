import sys
from unittest.mock import MagicMock

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.modules["firebase_admin"] = MagicMock()
sys.modules["firebase_admin.credentials"] = MagicMock()
sys.modules["firebase_admin.storage"] = MagicMock()
sys.modules["firebase_admin.firestore"] = MagicMock()

from ui.state.group_state import GroupState
from ui.viewmodels.admin_viewmodel import AdminState, AdminViewModel


def _render_admin_test_app():
    from ui.admin import render_admin_panel

    render_admin_panel()


def _render_wizard_test_app(available_clients, available_periods, orch):
    from ui.groups_wizard_ui import render_groups_section_wizard

    render_groups_section_wizard(available_clients, available_periods, orch)


def _render_enrichment_test_app(orch):
    from ui.enrichment_ui import render_enrichment_wizard

    render_enrichment_wizard(orch)


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


def test_admin_panel_smoke(monkeypatch):
    monkeypatch.setattr(
        AdminViewModel,
        "get_state",
        lambda self: AdminState(can_sync_local=False),
    )

    at = AppTest.from_function(_render_admin_test_app)
    at.run()

    assert any("Sincronização via Upload" in markdown.value for markdown in at.sidebar.markdown)
    assert any("Carregue ambas as planilhas" in caption.value for caption in at.sidebar.caption)


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

    generate_button = next(button for button in at.button if button.label == "Preparar Arquivo para Download")
    generate_button.click().run()

    assert any("faturas precisam de atenção" in info.value for info in at.info)
    assert any("Planilha pronta em" in toast.value for toast in at.toast)
    assert orch.generate_calls == 1
    assert not at.error


def test_enrichment_empty_state_smoke(monkeypatch):
    import ui.enrichment_ui as enrichment_ui

    monkeypatch.setattr(enrichment_ui.enrichment_service, "list_profiles", lambda: [])

    at = AppTest.from_function(_render_enrichment_test_app, args=(object(),))
    at.run()

    assert any("Nenhum perfil salvo encontrado" in caption.value for caption in at.caption)
    assert any("Selecione ou crie um perfil" in info.value for info in at.info)


def test_enrichment_load_profile_smoke(monkeypatch):
    import ui.enrichment_ui as enrichment_ui

    monkeypatch.setattr(enrichment_ui.enrichment_service, "list_profiles", lambda: ["Perfil A"])
    monkeypatch.setattr(
        enrichment_ui.enrichment_service,
        "load_mapping",
        lambda profile_name: pd.DataFrame(
            [{"No. UC": "123", "Razão Social": "Cliente A", "Número da Conta": "999"}]
        ),
    )
    monkeypatch.setattr(enrichment_ui.time, "sleep", lambda _: None)

    at = AppTest.from_function(_render_enrichment_test_app, args=(object(),))
    at.run()

    at.text_input[0].set_value("Perfil A")
    at.button[0].click().run()

    assert any("pronto para edição" in success.value for success in at.success)
    assert any("Salvar" in button.label for button in at.button)
