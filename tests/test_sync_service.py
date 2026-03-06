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
    
    # 2. Cliente B foi "Cancelado" na Gestão ("Sim"). Portanto, ele NÃO deve receber o Vencimento que lá existe.
    # Deverá receber nulo (convertido para string 'None' ou '').
    cliente_b = df_result[(df_result["No. UC"] == 5143128.0)].iloc[0]
    assert pd.isna(cliente_b["Vencimento"]) or str(cliente_b["Vencimento"]) in ["None", "nan", "NaN"]
    # E o status continua o do Balanço original
    assert cliente_b["Status Pos-Faturamento"] == "Em aberto"
    
    # 3. Cliente C tem Fev/2026 na base e usa uma string gigantesca. Deve casar perfeitamente.
    cliente_c = df_result[(df_result["No. UC"] == 4000476449.0)].iloc[0]
    assert cliente_c["Vencimento"] == "20-03-2026"
    assert cliente_c["Status Pos-Faturamento"] == "Pago" 
