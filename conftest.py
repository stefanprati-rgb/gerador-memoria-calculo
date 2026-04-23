import os
import tempfile
import uuid

def pytest_configure(config):
    """
    Injeta um diretório temporário único no workspace para os testes,
    evitando que o Pytest tente limpar uma pasta '.pytest_tmp' travada
    por execuções anteriores (WinError 5).
    """
    workspace_tmp_root = os.path.join(os.getcwd(), ".pytest_sessions_tmp")
    os.makedirs(workspace_tmp_root, exist_ok=True)

    unique_session_tmp = os.path.join(workspace_tmp_root, f"run_{uuid.uuid4().hex[:8]}")
    os.makedirs(unique_session_tmp, exist_ok=True)

    runtime_tmp = os.path.join(unique_session_tmp, "runtime_tmp")
    os.makedirs(runtime_tmp, exist_ok=True)

    # Força libs (incluindo Streamlit AppTest) a usar temp no workspace.
    os.environ["TMP"] = runtime_tmp
    os.environ["TEMP"] = runtime_tmp
    os.environ["TMPDIR"] = runtime_tmp
    tempfile.tempdir = runtime_tmp

    # Em alguns ambientes Windows/sandbox, o cleanup do TemporaryDirectory
    # pode falhar com WinError 5 mesmo após execução bem-sucedida.
    original_cleanup = tempfile.TemporaryDirectory.cleanup
    original_class_cleanup = tempfile.TemporaryDirectory._cleanup

    def _safe_cleanup(self):
        try:
            original_cleanup(self)
        except PermissionError:
            pass

    @classmethod
    def _safe_class_cleanup(cls, *args, **kwargs):
        try:
            return original_class_cleanup(*args, **kwargs)
        except PermissionError:
            return None

    tempfile.TemporaryDirectory.cleanup = _safe_cleanup
    tempfile.TemporaryDirectory._cleanup = _safe_class_cleanup
