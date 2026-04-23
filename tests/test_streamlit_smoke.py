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


def test_admin_panel_smoke(monkeypatch):
    monkeypatch.setattr(
        AdminViewModel,
        "get_state",
        lambda self: AdminState(can_sync_local=False),
    )

    at = AppTest.from_file("tests/apps/admin_smoke_app.py")
    at.run()

    assert any("Sincronização via Upload" in markdown.value for markdown in at.sidebar.markdown)
    assert any("Carregue ambas as planilhas" in caption.value for caption in at.sidebar.caption)


def test_wizard_step_3_generate_smoke(monkeypatch):
    import ui.groups_wizard_ui as wizard_ui

    monkeypatch.setattr(wizard_ui.enrichment_service, "get_all_enrichment_data", lambda: None)
    at = AppTest.from_file("tests/apps/wizard_smoke_app.py")
    at.session_state["groups"] = [
        GroupState(id=1, name="Projeto Teste", clients=["Cliente A"], periods=["01/2026"])
    ]
    at.session_state["group_counter"] = 1
    at.session_state["active_group_id"] = 1
    at.session_state["wizard_step"] = 3
    at.run()

    generate_button = next(button for button in at.button if button.label == "Preparar Arquivo para Download")
    generate_button.click().run()

    assert any("faturas estão sem vencimento identificado" in warning.value for warning in at.warning)
    assert any("Planilha pronta em" in toast.value for toast in at.toast)
    assert not at.error


def test_enrichment_empty_state_smoke(monkeypatch):
    import ui.enrichment_ui as enrichment_ui

    monkeypatch.setattr(enrichment_ui.enrichment_service, "list_profiles", lambda: [])

    at = AppTest.from_file("tests/apps/enrichment_smoke_app.py")
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

    at = AppTest.from_file("tests/apps/enrichment_smoke_app.py")
    at.run()

    at.text_input[0].set_value("Perfil A")
    at.button[0].click().run()

    assert any("pronto para edição" in success.value for success in at.success)
    assert any("Salvar" in button.label for button in at.button)
