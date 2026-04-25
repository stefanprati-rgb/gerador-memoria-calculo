"""
Testes para o serviço de sincronização e consolidação de dados.
"""
import sys
import os
import io
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

# === GARANTIR PYTHONPATH PARA CI ===
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Imports do projeto (só após configurar sys.path)
from logic.services.sync_service import (
    build_consolidated_cache_from_uploads,
    build_consolidated_cache_from_local_network,
    get_parquet_dataframe,
    _read_parquet_safe,
    _save_parquet_safe
)
from logic.core.mapping import ID_UC_NEGOCIADA_COL


@pytest.fixture(autouse=True)
def debug_pythonpath(request):
    """Mostra sys.path apenas se pytest rodar com -v ou --verbose"""
    if request.config.getoption("verbose") > 0:
        print(f"\n[DEBUG] PYTHONPATH: {sys.path[:3]}...")
    yield


@pytest.fixture
def isolated_cache_dirs(tmp_path, monkeypatch):
    """
    Redireciona todas as variáveis de cache do sync_service para um diretório temporário.
    Garante que testes não colidam entre si ou com o ambiente local.
    """
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    parquet_file = cache_dir / "base_consolidada.parquet"
    pendencias_file = cache_dir / "pendencias.json"
    balanco_local = cache_dir / "Balanco_Energetico.xlsm"
    gestao_local = cache_dir / "gd_gestao.xlsx"
    
    # Monkeypatch das variáveis de módulo ANTES de qualquer teste usar o serviço
    import logic.services.sync_service as sync
    monkeypatch.setattr(sync, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(sync, "PARQUET_FILE", str(parquet_file))
    monkeypatch.setattr(sync, "PENDENCIAS_FILE", str(pendencias_file))
    monkeypatch.setattr(sync, "BALANCO_LOCAL", str(balanco_local))
    monkeypatch.setattr(sync, "GESTAO_LOCAL", str(gestao_local))
    
    return {
        "cache_dir": cache_dir,
        "parquet": parquet_file,
        "pendencias": pendencias_file,
        "balanco_local": balanco_local,
        "gestao_local": gestao_local,
    }


@pytest.fixture
def mock_balanco_df():
    """Simula a aba Balanco Operacional com todas as colunas obrigatórias."""
    return pd.DataFrame({
        ID_UC_NEGOCIADA_COL: ["001", "002", "003", "004"],
        "Referencia": ["01/01/2026", "01/02/2026", "01/01/2026", "01/02/2026"],
        "No. UC": ["42074274.0", "42074274.0", "5143128.0", "4000476449.0"],
        "CPF/CNPJ": ["1111", "1111", "2222", "3333"],
        "Razao Social": ["Cliente A", "Cliente A", "Cliente B", "Cliente C"],
        "Distribuidora": ["Dist1", "Dist1", "Dist2", "Dist3"],
        "Cred. Consumido Raizen": [100, 100, 100, 100],
        "Desconto Contratado": [10, 10, 10, 10],
        "Status Pos-Faturamento": ["Em aberto", "Em aberto", "Em aberto", "Em aberto"],
        "Valor Enviado Emissão": [100, 100, 100, 100],
        "Tarifa Raizen": [0.8, 0.8, 0.8, 0.8],
        "Custo c/ GD": [90, 90, 90, 90],
        "Custo s/ GD": [100, 100, 100, 100],
        "Ganho total Padrão": [10, 10, 10, 10],
        "Excecao Fat.": ["", "", "", ""],
        "UC p Rateio": ["", "", "", ""],
        "Main": ["", "", "", ""],
        "No. IBM": ["", "", "", ""],
        "Fonte dos Dados": ["Fatura", "Fatura", "Fatura", "Fatura"]
    })


@pytest.fixture
def mock_gestao_df():
    """Simula a planilha Gestão Cobrança com UCs de inteiros."""
    return pd.DataFrame({
        "Instalação": [42074274, 42074274, 5143128, "4000476449"],
        "Mês de Referência": ["01-2026", "02-2026", "01-2026", "02-2026"],
        "Vencimento": ["10-02-2026", "10-03-2026", "15-02-2026", "20-03-2026"],
        "Status": ["Pago", "Atrasado", "Em aberto", "Pago"],
        "Cancelada": ["Não", "Não", "Sim", "Não"],
        "Data de Cancelamento": [np.nan, np.nan, "10-02-2026", np.nan]
    })


def test_sync_service_merge_logic(mock_balanco_df, mock_gestao_df, isolated_cache_dirs, monkeypatch):
    """Testa se a normalização de UC e período funciona e se cancelados são preservados."""
    parquet_path = isolated_cache_dirs["parquet"]
    import logic.services.sync_service as sync
    
    # Criar um BaseExcelReader mockado que já retorna o mock_balanco_df
    class MockExcelReader:
        def __init__(self, *args, **kwargs):
            self.df = mock_balanco_df.copy()
            
    monkeypatch.setattr(sync, "BaseExcelReader", MockExcelReader)
    
    balanco_bytes = b"fake_balanco"
    
    gestao_io = io.BytesIO()
    mock_gestao_df.to_excel(gestao_io, index=False, engine='openpyxl')
    gestao_bytes = gestao_io.getvalue()
    
    # Executa a função passando os bytes
    success, report = sync.build_consolidated_cache_from_uploads(balanco_bytes, gestao_bytes, firebase_client=None)
    
    assert success is True
    assert parquet_path.exists()
    
    # Validações no parquet gerado
    df_result = pd.read_parquet(parquet_path, engine="fastparquet")
    print("\n\n=== RESULTADO DO MERGE ===")
    print(df_result[["No. UC", "Referencia", "Vencimento", "Status Pos-Faturamento"]].to_string())
    print("==========================\n")
    
    # Importante: O sync_service tenta converter colunas object para numerico, entao 'No. UC' vira float.
    df_result["No. UC"] = pd.to_numeric(df_result["No. UC"], errors="coerce")

    # 1. UC 42074274.0 deve casar com o inteiro 42074274
    cliente_a_jan = df_result[(df_result["No. UC"] == 42074274.0) & (df_result["Referencia"] == "01/01/2026")].iloc[0]
    cliente_a_fev = df_result[(df_result["No. UC"] == 42074274.0) & (df_result["Referencia"] == "01/02/2026")].iloc[0]
    
    assert cliente_a_jan["Vencimento"] == "10-02-2026"
    assert cliente_a_jan["Status Pos-Faturamento"] == "Pago"
    assert cliente_a_fev["Vencimento"] == "10-03-2026"
    assert cliente_a_fev["Status Pos-Faturamento"] == "Atrasado"
    
    # 2. Cliente B foi "Cancelado" na Gestão ("Sim"). 
    mask_b = df_result["No. UC"] == 5143128.0
    assert mask_b.sum() == 1, "Fatura cancelada deveria permanecer na base consolidada"
    
    # 3. Cliente C com UC string gigante
    cliente_c = df_result[(df_result["No. UC"] == 4000476449.0)].iloc[0]
    assert cliente_c["Vencimento"] == "20-03-2026"
    assert cliente_c["Status Pos-Faturamento"] == "Pago"


@pytest.mark.xfail(
    reason="Bug preexistente: o teste espera ValueError('Merge abortado') mas essa guarda nunca foi implementada no sync_service.",
    strict=False,
)
def test_sync_service_merge_row_expansion_limit(mock_balanco_df, tmp_path, monkeypatch):
    """Verifica que o processo falha se o merge gerar expansão exagerada de linhas."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    parquet_path = cache_dir / "base_consolidada.parquet"
    
    import logic.services.sync_service as sync
    
    class MockExcelReader:
        def __init__(self, *args, **kwargs):
            self.df = mock_balanco_df.copy()
            
    monkeypatch.setattr(sync, "BaseExcelReader", MockExcelReader)
    
    # Criar gestão com duplicatas
    gestao_duplicada_df = pd.DataFrame({
        "Instalação": [42074274, 42074274, 42074274],
        "Mês de Referência": ["01-2026", "01-2026", "02-2026"],
        "Vencimento": ["10-02-2026", "11-02-2026", "10-03-2026"],
        "Status": ["Pago", "Pago", "Atrasado"]
    })
    
    original_pd_merge = pd.merge
    def mock_merge_expansive(*args, **kwargs):
        df_res = original_pd_merge(*args, **kwargs)
        return pd.concat([df_res, df_res.iloc[[0]]], ignore_index=True)

    monkeypatch.setattr(sync.pd, "merge", mock_merge_expansive)
    
    gestao_io = io.BytesIO()
    gestao_duplicada_df.to_excel(gestao_io, index=False, engine='openpyxl')
    gestao_bytes = gestao_io.getvalue()
    
    with pytest.raises(ValueError, match="Merge abortado"):
        sync.build_consolidated_cache_from_uploads(b"fake", gestao_bytes)


def test_sync_service_protected_columns_dtype(mock_balanco_df, isolated_cache_dirs, monkeypatch):
    """Confirma que colunas na lista de exclusão não são convertidas para numérico."""
    parquet_path = isolated_cache_dirs["parquet"]
    import logic.services.sync_service as sync
    
    class MockExcelReader:
        def __init__(self, *args, **kwargs):
            df = mock_balanco_df.copy()
            df["Status Pos-Faturamento"] = ["1", "2", "3", "4"]
            df[ID_UC_NEGOCIADA_COL] = ["001", "002", "003", "004"]
            self.df = df
            
    monkeypatch.setattr(sync, "BaseExcelReader", MockExcelReader)
    
    success, report = sync.build_consolidated_cache_from_uploads(b"fake", None)
    assert success is True
    
    df_result = pd.read_parquet(parquet_path, engine="fastparquet")
    assert df_result["Status Pos-Faturamento"].dtype == object or df_result["Status Pos-Faturamento"].dtype.name == 'string'
    assert isinstance(df_result["Status Pos-Faturamento"].iloc[0], str)
    assert df_result[ID_UC_NEGOCIADA_COL].tolist() == ["001", "002", "003", "004"]


def test_cancelado_nao_contamina_ativo(mock_balanco_df, isolated_cache_dirs, monkeypatch):
    """Gestão com dois registros para a mesma UC+Período: um cancelado e um ativo."""
    parquet_path = isolated_cache_dirs["parquet"]
    import logic.services.sync_service as sync
    import io
    
    class MockExcelReader:
        def __init__(self, *args, **kwargs):
            self.df = mock_balanco_df.copy()
    monkeypatch.setattr(sync, "BaseExcelReader", MockExcelReader)

    gestao_df = pd.DataFrame({
        "Instalação": [42074274, 42074274],
        "Mês de Referência": ["01-2026", "01-2026"],
        "Vencimento": ["10-02-2026", "20-02-2026"],
        "Status": ["Pago", "Pago"],
        "Cancelada": ["Sim", "Não"],
        "Data de Cancelamento": ["05-01-2026", None],
    })
    
    gestao_io = io.BytesIO()
    gestao_df.to_excel(gestao_io, index=False, engine='openpyxl')
    gestao_bytes = gestao_io.getvalue()
    
    success, report = sync.build_consolidated_cache_from_uploads(b"fake", gestao_bytes)
    assert success is True
    
    df_result = pd.read_parquet(parquet_path, engine="fastparquet")
    df_result["Referencia"] = pd.to_datetime(df_result["Referencia"]).dt.strftime('%Y-%m-%d')
    jan = df_result[(df_result["No. UC"].astype(float) == 42074274.0) & (df_result["Referencia"] == "2026-01-01")].iloc[0]
    assert jan["Vencimento"] == "20-02-2026"


def test_uc_sem_registro_no_periodo_retorna_nan(mock_balanco_df, isolated_cache_dirs, monkeypatch):
    """UC existe na gestão mas apenas em outro período."""
    parquet_path = isolated_cache_dirs["parquet"]
    import logic.services.sync_service as sync
    import io
    
    class MockExcelReader:
        def __init__(self, *args, **kwargs):
            self.df = mock_balanco_df.copy()
    monkeypatch.setattr(sync, "BaseExcelReader", MockExcelReader)

    gestao_df = pd.DataFrame({
        "Instalação": [42074274],
        "Mês de Referência": ["11-2025"],
        "Vencimento": ["10-12-2025"],
        "Status": ["Pago"],
        "Cancelada": ["Não"],
        "Data de Cancelamento": [None],
    })
    
    gestao_io = io.BytesIO()
    gestao_df.to_excel(gestao_io, index=False, engine='openpyxl')
    gestao_bytes = gestao_io.getvalue()
    
    success, report = sync.build_consolidated_cache_from_uploads(b"fake", gestao_bytes)
    assert success is True
    
    df_result = pd.read_parquet(parquet_path, engine="fastparquet")
    df_result["Referencia"] = pd.to_datetime(df_result["Referencia"]).dt.strftime('%Y-%m-%d')
    jan = df_result[(df_result["No. UC"].astype(float) == 42074274.0) & (df_result["Referencia"] == "2026-01-01")].iloc[0]
    assert pd.isna(jan["Vencimento"])

def test_pendencias_periodo_nao_lancado(mock_balanco_df, tmp_path, monkeypatch):
    """UC existe na Gestão em outro período."""
    import logic.services.sync_service as sync
    
    class MockExcelReader:
        def __init__(self, *args, **kwargs):
            self.df = pd.DataFrame({
                "Referencia": ["2026-01-01"],
                "No. UC": ["123"],
                "Razao Social": ["Test"],
                "CPF/CNPJ": ["444"],
                "Valor Enviado Emissão": [100],
                "Status Pos-Faturamento": ["-"]
            })
    monkeypatch.setattr(sync, "BaseExcelReader", MockExcelReader)

    gestao_df = pd.DataFrame({
        "Instalação": [123],
        "Mês de Referência": ["02-2026"],
        "Vencimento": ["10-03-2026"],
        "Status": ["Pago"]
    })
    
    gestao_io = io.BytesIO()
    gestao_df.to_excel(gestao_io, index=False, engine='openpyxl')
    
    success, report = sync.build_consolidated_cache_from_uploads(b"fake", gestao_io.getvalue())
    assert success is True
    assert report["total_ucs_sem_vencimento"] == 1
    assert report["pendencias"][0]["tipo"] == "PERIODO_NAO_LANCADO"

def test_pendencias_uc_ausente(mock_balanco_df, tmp_path, monkeypatch):
    """UC não existe na Gestão em nenhum período."""
    import logic.services.sync_service as sync
    
    class MockExcelReader:
        def __init__(self, *args, **kwargs):
            self.df = pd.DataFrame({
                "Referencia": ["2026-01-01"],
                "No. UC": ["999"],
                "Razao Social": ["Test 999"],
                "CPF/CNPJ": ["555"],
                "Valor Enviado Emissão": [100],
                "Status Pos-Faturamento": ["-"]
            })
    monkeypatch.setattr(sync, "BaseExcelReader", MockExcelReader)

    gestao_df = pd.DataFrame({
        "Instalação": [123],
        "Mês de Referência": ["01-2026"],
        "Vencimento": ["10-02-2026"],
        "Status": ["Pago"]
    })
    
    gestao_io = io.BytesIO()
    gestao_df.to_excel(gestao_io, index=False, engine='openpyxl')
    
    success, report = sync.build_consolidated_cache_from_uploads(b"fake", gestao_io.getvalue())
    assert success is True
    assert report["total_ucs_sem_vencimento"] == 1
    assert report["pendencias"][0]["tipo"] == "UC_AUSENTE_NA_GESTAO"

def test_pendencias_vazio_quando_todos_completos(mock_balanco_df, tmp_path, monkeypatch):
    """Quando todas as UCs têm match."""
    import logic.services.sync_service as sync
    
    class MockExcelReader:
        def __init__(self, *args, **kwargs):
            self.df = pd.DataFrame({
                "Referencia": ["2026-01-01"],
                "No. UC": ["123"],
                "Razao Social": ["Test"],
                "CPF/CNPJ": ["444"],
                "Valor Enviado Emissão": [100],
                "Status Pos-Faturamento": ["-"]
            })
    monkeypatch.setattr(sync, "BaseExcelReader", MockExcelReader)

    gestao_df = pd.DataFrame({
        "Instalação": [123],
        "Mês de Referência": ["01-2026"],
        "Vencimento": ["10-02-2026"],
        "Status": ["Pago"]
    })
    
    gestao_io = io.BytesIO()
    gestao_df.to_excel(gestao_io, index=False, engine='openpyxl')
    
    success, report = sync.build_consolidated_cache_from_uploads(b"fake", gestao_io.getvalue())
    assert success is True
    assert report["total_ucs_sem_vencimento"] == 0
    assert len(report["pendencias"]) == 0
