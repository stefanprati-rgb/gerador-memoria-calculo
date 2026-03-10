import pytest
import pandas as pd
import numpy as np
import os
import sys
import io

# Add root directory to python path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.services.sync_service import build_consolidated_cache_from_uploads

@pytest.fixture
def mock_balanco_df():
    """Simula a aba Balanco Operacional com UCs sujas."""
    return pd.DataFrame({
        "Referencia": ["2026-01-01", "2026-02-01", "2026-01-01", "2026-02-01"],
        "No. UC": ["42074274.0", "42074274.0", "5143128.0", "4000476449.0"],
        "CPF/CNPJ": ["1111", "1111", "2222", "3333"],
        "Razao Social": ["Cliente A", "Cliente A", "Cliente B", "Cliente C"],
        "Distribuidora": ["Dist1", "Dist1", "Dist2", "Dist3"],
        "Cred. Consumido Raizen": [100, 100, 100, 100],
        "Desconto Contratado": [10, 10, 10, 10],
        # Valores originais puros que deverão ser enriquecidos
        "Status Pos-Faturamento": ["Em aberto", "Em aberto", "Em aberto", "Em aberto"]
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

def test_sync_service_merge_logic(mock_balanco_df, mock_gestao_df, tmp_path, monkeypatch):
    """Testa se a normalização de UC e período funciona e se cancelados são ignorados."""
    # Redefine os caminhos temporários
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    parquet_path = cache_dir / "base_consolidada.parquet"
    
    # Monkeypatching as constantes no sync_service
    import logic.services.sync_service as sync
    monkeypatch.setattr(sync, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(sync, "PARQUET_FILE", str(parquet_path))
    monkeypatch.setattr(sync, "BALANCO_LOCAL", str(cache_dir / "Balanco_Energetico.xlsm"))
    monkeypatch.setattr(sync, "GESTAO_LOCAL", str(cache_dir / "gd_gestao.xlsx"))
    
    # Para o teste não ler o disco, precisamos mockar as leituras do Pandas ou ExcelAdapter
    # Primeiro salvamos os mocks no temp dir para ele poder ler normalmente!
    
    # Criar um BaseExcelReader mockado que já retorna o mock_balanco_df
    class MockExcelReader:
        def __init__(self, *args, **kwargs):
            self.df = mock_balanco_df.copy()
            
    monkeypatch.setattr(sync, "BaseExcelReader", MockExcelReader)
    
    # Para o gestao, a leitura do excel é direta com pandas (não usa adapter).
    # Precisamos gerar bytes de um excel real para passar na função!
    balanco_bytes = b"fake_balanco"  # adapter ignorará porque mockamos a classe
    
    gestao_io = io.BytesIO()
    mock_gestao_df.to_excel(gestao_io, index=False, engine='openpyxl')
    gestao_bytes = gestao_io.getvalue()
    
    # Executa a função passando os bytes (que serão salvos nos paths que mockamos e lidos depois)
    success = sync.build_consolidated_cache_from_uploads(balanco_bytes, gestao_bytes, firebase_client=None)
    
    assert success is True
    assert parquet_path.exists()
    
    # Validações no parquet gerado
    df_result = pd.read_parquet(parquet_path, engine="fastparquet")
    print("\n\n=== RESULTADO DO MERGE ===")
    print(df_result[["No. UC", "Referencia", "Vencimento", "Status Pos-Faturamento"]].to_string())
    print("==========================\n")
    
    # Converter a coluna para string YYYY-MM-DD para o filtro do teste funcionar
    df_result["Referencia"] = pd.to_datetime(df_result["Referencia"]).dt.strftime('%Y-%m-%d')
    
    # Importante: O sync_service tenta converter colunas object para numerico, entao 'No. UC' vira float.
    df_result["No. UC"] = pd.to_numeric(df_result["No. UC"], errors="coerce")
    
    print("\n--- DEBUG MASKS ---")
    print(df_result.dtypes)
    print("UC Match:", df_result["No. UC"] == 42074274.0)
    print("Ref Match Fev:", df_result["Referencia"] == "2026-02-01")
    mask_fev = (df_result["No. UC"] == 42074274.0) & (df_result["Referencia"] == "2026-02-01")
    print("Combined Fev Match:", mask_fev)
    print("Rows for Fev:\n", df_result[mask_fev])
    print("-------------------\n")

    # 1. UC 42074274.0 deve casar com o inteiro 42074274
    # E o merge por perodo deve garantir:
    #   Jan/2026 -> Vence 10-02-2026, Pago
    #   Fev/2026 -> Vence 10-03-2026, Atrasado
    cliente_a_jan = df_result[(df_result["No. UC"] == 42074274.0) & (df_result["Referencia"] == "2026-01-01")].iloc[0]
    cliente_a_fev = df_result[mask_fev].iloc[0]
    
    assert cliente_a_jan["Vencimento"] == "10-02-2026"
    assert cliente_a_jan["Status Pos-Faturamento"] == "Pago"
    
    assert cliente_a_fev["Vencimento"] == "10-03-2026"
    assert cliente_a_fev["Status Pos-Faturamento"] == "Atrasado"
    
    # 2. Cliente B foi "Cancelado" na Gestão ("Sim"). 
    # De acordo com a regra de negócio atual, faturas canceladas são REMOVIDAS da base consolidada.
    mask_b = df_result["No. UC"] == 5143128.0
    assert mask_b.sum() == 0, "Fatura cancelada deveria ter sido removida da base consolidada"
    
    # 3. Cliente C tem Fev/2026 na base e usa uma string gigantesca. Deve casar perfeitamente.
    cliente_c = df_result[(df_result["No. UC"] == 4000476449.0)].iloc[0]
    assert cliente_c["Vencimento"] == "20-03-2026"
    assert cliente_c["Status Pos-Faturamento"] == "Pago"


def test_sync_service_merge_row_expansion_limit(mock_balanco_df, tmp_path, monkeypatch):
    """Verifica que o processo falha se o merge gerar expansão exagerada de linhas (duplicatas na gestão)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    parquet_path = cache_dir / "base_consolidada.parquet"
    
    import logic.services.sync_service as sync
    monkeypatch.setattr(sync, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(sync, "PARQUET_FILE", str(parquet_path))
    monkeypatch.setattr(sync, "BALANCO_LOCAL", str(cache_dir / "Balanco_Energetico.xlsm"))
    monkeypatch.setattr(sync, "GESTAO_LOCAL", str(cache_dir / "gd_gestao.xlsx"))
    
    class MockExcelReader:
        def __init__(self, *args, **kwargs):
            self.df = mock_balanco_df.copy()
            
    monkeypatch.setattr(sync, "BaseExcelReader", MockExcelReader)
    
    # Criar gestão com duplicatas para uma mesma UC e Período (causará explosão de linhas no merge)
    # mock_balanco_df tem 4 linhas. Se adicionarmos 1 registro duplicado, teremos 5 linhas (25% de expansão)
    gestao_duplicada_df = pd.DataFrame({
        "Instalação": [42074274, 42074274, 42074274], # Duplicado para a mesma UC
        "Mês de Referência": ["01-2026", "01-2026", "02-2026"], # Duas entradas para Jan-2026
        "Vencimento": ["10-02-2026", "11-02-2026", "10-03-2026"],
        "Status": ["Pago", "Pago", "Atrasado"]
    })
    
    # Note: O sync_service faz drop_duplicates(keep='last') na gestão antes do merge.
    # Para forçar a expansão, precisamos que as chaves de merge sejam diferentes OU bugar o drop_duplicates.
    # Mas o código atual FAZ drop_duplicates antes do merge!
    # "Deduplicar gestão preservando o período"
    # df_gestao = df_gestao.drop_duplicates(subset=merge_keys, keep="last")
    
    # Se o drop_duplicates está lá, o merge nunca deve gerar linhas extras a menos que MERGE_KEYS falhe.
    # Ah! O problema descrito na tarefa diz: "Um merge que produz mais linhas que a base original (por duplicatas na Gestão) passa silenciosamente"
    # Se o drop_duplicates já existe, talvez ele não seja suficiente ou as chaves estejam incompletas.
    
    # Vamos olhar o código do sync_service novamente.
    # merge_keys = ["No. UC_norm"]
    # if ref_merge_col in df_gestao.columns and ref_merge_col in df_consolidado.columns:
    #     merge_keys.append(ref_merge_col)
    
    # Se eu quiser testar a VALIDAÇÃO, eu preciso forçar a expansão.
    # Se eu remover o drop_duplicates no teste (via monkeypatch ou similar) eu posso testar a validação.
    # Mas a tarefa Pede para adicionar a validação PORQUE o merge pode produzir mais linhas.
    
    # Se eu criar uma gestão que DESAFIA o drop_duplicates atual?
    # O drop_duplicates usa merge_keys, que inclui Referencia_merge se disponível.
    
    # Vamos forçar a falha da validação mockando o pd.merge no módulo sync para retornar um DF maior.
    original_pd_merge = pd.merge
    def mock_merge_expansive(*args, **kwargs):
        df_res = original_pd_merge(*args, **kwargs)
        # Adicionar uma linha extra artificialmente para disparar a validação
        return pd.concat([df_res, df_res.iloc[[0]]], ignore_index=True)

    monkeypatch.setattr(sync.pd, "merge", mock_merge_expansive)
    
    gestao_io = io.BytesIO()
    gestao_duplicada_df.to_excel(gestao_io, index=False, engine='openpyxl')
    gestao_bytes = gestao_io.getvalue()
    
    with pytest.raises(ValueError, match="Merge abortado"):
        sync.build_consolidated_cache_from_uploads(b"fake", gestao_bytes)


def test_sync_service_protected_columns_dtype(mock_balanco_df, tmp_path, monkeypatch):
    """Confirma que colunas na lista de exclusão não são convertidas para numérico."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    parquet_path = cache_dir / "base_consolidada.parquet"
    
    import logic.services.sync_service as sync
    monkeypatch.setattr(sync, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(sync, "PARQUET_FILE", str(parquet_path))
    monkeypatch.setattr(sync, "BALANCO_LOCAL", str(cache_dir / "Balanco_Energetico.xlsm"))
    
    class MockExcelReader:
        def __init__(self, *args, **kwargs):
            # No mock_balanco_df, Status Pos-Faturamento é "Em aberto" (texto puro)
            # Vamos criar um cenário onde uma coluna protegida tem cara de número
            df = mock_balanco_df.copy()
            df["Status Pos-Faturamento"] = ["1", "2", "3", "4"] # Parece numérico
            self.df = df
            
    monkeypatch.setattr(sync, "BaseExcelReader", MockExcelReader)
    
    # Executa sem gestão
    success = sync.build_consolidated_cache_from_uploads(b"fake", None)
    assert success is True
    
    df_result = pd.read_parquet(parquet_path, engine="fastparquet")
    
    # Status Pos-Faturamento deve ser object (string), não int/float
    assert df_result["Status Pos-Faturamento"].dtype == object or df_result["Status Pos-Faturamento"].dtype.name == 'string'
    assert isinstance(df_result["Status Pos-Faturamento"].iloc[0], str)


def test_cancelado_nao_contamina_ativo(mock_balanco_df, tmp_path, monkeypatch):
    """
    Gestão com dois registros para a mesma UC+Período:
    um cancelado e um ativo. O ativo deve vencer.
    """
    import logic.services.sync_service as sync
    import io
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    parquet_path = cache_dir / "base_consolidada.parquet"
    
    monkeypatch.setattr(sync, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(sync, "PARQUET_FILE", str(parquet_path))
    monkeypatch.setattr(sync, "BALANCO_LOCAL", str(cache_dir / "Balanco_Energetico.xlsm"))
    monkeypatch.setattr(sync, "GESTAO_LOCAL", str(cache_dir / "gd_gestao.xlsx"))
    
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
    
    success = sync.build_consolidated_cache_from_uploads(b"fake", gestao_bytes)
    assert success is True
    
    df_result = pd.read_parquet(parquet_path, engine="fastparquet")
    df_result["Referencia"] = pd.to_datetime(df_result["Referencia"]).dt.strftime('%Y-%m-%d')
    jan = df_result[(df_result["No. UC"].astype(float) == 42074274.0) & (df_result["Referencia"] == "2026-01-01")].iloc[0]
    
    # Deve ter o vencimento do registro NÃO cancelado
    assert jan["Vencimento"] == "20-02-2026"


def test_uc_sem_registro_no_periodo_retorna_nan(mock_balanco_df, tmp_path, monkeypatch):
    """
    UC existe na gestão mas apenas em outro período.
    Não deve receber vencimento de período diferente.
    """
    import logic.services.sync_service as sync
    import io
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    parquet_path = cache_dir / "base_consolidada.parquet"
    
    monkeypatch.setattr(sync, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(sync, "PARQUET_FILE", str(parquet_path))
    monkeypatch.setattr(sync, "BALANCO_LOCAL", str(cache_dir / "Balanco_Energetico.xlsm"))
    monkeypatch.setattr(sync, "GESTAO_LOCAL", str(cache_dir / "gd_gestao.xlsx"))
    
    class MockExcelReader:
        def __init__(self, *args, **kwargs):
            self.df = mock_balanco_df.copy()
    monkeypatch.setattr(sync, "BaseExcelReader", MockExcelReader)

    gestao_df = pd.DataFrame({
        "Instalação": [42074274],
        "Mês de Referência": ["11-2025"],   # período diferente do Balanço (01-2026)
        "Vencimento": ["10-12-2025"],
        "Status": ["Pago"],
        "Cancelada": ["Não"],
        "Data de Cancelamento": [None],
    })
    
    gestao_io = io.BytesIO()
    gestao_df.to_excel(gestao_io, index=False, engine='openpyxl')
    gestao_bytes = gestao_io.getvalue()
    
    success = sync.build_consolidated_cache_from_uploads(b"fake", gestao_bytes)
    assert success is True
    
    df_result = pd.read_parquet(parquet_path, engine="fastparquet")
    df_result["Referencia"] = pd.to_datetime(df_result["Referencia"]).dt.strftime('%Y-%m-%d')
    jan = df_result[(df_result["No. UC"].astype(float) == 42074274.0) & (df_result["Referencia"] == "2026-01-01")].iloc[0]
    
    # Não deve receber vencimento de outro período
    assert pd.isna(jan["Vencimento"])
