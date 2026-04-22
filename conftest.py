import os
import uuid
import tempfile

def pytest_configure(config):
    """
    Injeta um diretório temporário único no workspace para os testes, 
    evitando que o Pytest tente limpar uma pasta '.pytest_tmp' travada 
    por execuções anteriores (WinError 5).
    """
    # Garante que a pasta pai existe
    base_workspace_tmp = os.path.join(os.getcwd(), ".pytest_sessions_tmp")
    os.makedirs(base_workspace_tmp, exist_ok=True)
    
    # Cria uma pasta única para esta sessão
    unique_session_tmp = os.path.join(base_workspace_tmp, f"run_{uuid.uuid4().hex[:8]}")
    os.makedirs(unique_session_tmp, exist_ok=True)
    
    # Força o pytest a usar essa pasta como root dos temporários
    config.option.basetemp = unique_session_tmp
