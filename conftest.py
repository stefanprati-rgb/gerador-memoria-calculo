import os
import uuid
import tempfile

def pytest_configure(config):
    """
    Injeta um diretório temporário único no workspace para os testes, 
    evitando que o Pytest tente limpar uma pasta '.pytest_tmp' travada 
    por execuções anteriores (WinError 5).
    """
    # Usa temp do sistema para reduzir lock/permissão no workspace.
    # Cada sessão usa uma pasta única.
    unique_session_tmp = tempfile.mkdtemp(prefix=f"pytest_run_{uuid.uuid4().hex[:8]}_")
    config.option.basetemp = unique_session_tmp
