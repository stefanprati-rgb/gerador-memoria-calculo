import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

from streamlit.testing.v1 import AppTest

sys.modules["firebase_admin"] = MagicMock()
sys.modules["firebase_admin.credentials"] = MagicMock()
sys.modules["firebase_admin.storage"] = MagicMock()
sys.modules["firebase_admin.firestore"] = MagicMock()

class FakeOrchestrator:
    def __init__(self, *args, **kwargs):
        self.reader = MagicMock()
        self.reader.df = [1, 2, 3]

    def get_available_periods(self):
        return ["01/2026", "02/2026"]

    def get_available_clients(self):
        return ["Cliente A", "Cliente B"]


def _build_local_cache_file() -> Path:
    runtime_dir = Path("tests") / ".runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    cache_file = runtime_dir / f"base_consolidada_{uuid.uuid4().hex}.parquet"
    cache_file.write_bytes(b"cache")
    return cache_file


def test_app_default_opens_wizard(monkeypatch):
    import config.settings as settings_module
    import logic.services.sync_service as sync_service
    import logic.services.orchestrator as orchestrator_module
    import ui.admin as admin_ui
    import ui.groups_wizard_ui as wizard_ui
    import ui.sidebar as sidebar_ui

    fake_cache = _build_local_cache_file()

    monkeypatch.setattr(sync_service, "PARQUET_FILE", str(fake_cache))
    monkeypatch.setattr(sync_service, "get_cache_update_time", lambda: "21/04/2026 às 23:00")
    monkeypatch.setattr(settings_module.settings, "template_file", str(Path("mc.xlsx").resolve()))
    monkeypatch.setattr(orchestrator_module, "Orchestrator", FakeOrchestrator)
    monkeypatch.setattr(admin_ui, "render_admin_panel", lambda: None)
    monkeypatch.setattr(sidebar_ui, "render_sidebar_metrics", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        wizard_ui,
        "render_groups_section_wizard",
        lambda available_clients, available_periods, orch: __import__("streamlit").write("WIZARD_MARKER"),
    )
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()

    assert any("WIZARD_MARKER" in markdown.value for markdown in at.markdown)
    assert at.sidebar.radio[0].value == "Gerador de Memória"


def test_app_switches_modules(monkeypatch):
    import config.settings as settings_module
    import logic.services.sync_service as sync_service
    import logic.services.orchestrator as orchestrator_module
    import ui.admin as admin_ui
    import ui.groups_wizard_ui as wizard_ui
    import ui.enrichment_ui as enrichment_ui
    import ui.sidebar as sidebar_ui

    fake_cache = _build_local_cache_file()

    monkeypatch.setattr(sync_service, "PARQUET_FILE", str(fake_cache))
    monkeypatch.setattr(sync_service, "get_cache_update_time", lambda: "21/04/2026 às 23:00")
    monkeypatch.setattr(settings_module.settings, "template_file", str(Path("mc.xlsx").resolve()))
    monkeypatch.setattr(orchestrator_module, "Orchestrator", FakeOrchestrator)
    monkeypatch.setattr(admin_ui, "render_admin_panel", lambda: None)
    monkeypatch.setattr(sidebar_ui, "render_sidebar_metrics", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        wizard_ui,
        "render_groups_section_wizard",
        lambda available_clients, available_periods, orch: __import__("streamlit").write("WIZARD_MARKER"),
    )
    monkeypatch.setattr(
        enrichment_ui,
        "render_enrichment_wizard",
        lambda orch: __import__("streamlit").write("ENRICHMENT_MARKER"),
    )

    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()

    assert any("WIZARD_MARKER" in markdown.value for markdown in at.markdown)

    at.sidebar.radio[0].set_value("Enriquecimento de Dados").run()

    assert any("ENRICHMENT_MARKER" in markdown.value for markdown in at.markdown)
