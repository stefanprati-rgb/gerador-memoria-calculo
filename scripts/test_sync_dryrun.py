"""Dry-run: testa sync_service sem Streamlit."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from logic.core.logging_config import setup_logging
setup_logging("INFO")
from logic.services.sync_service import build_consolidated_cache_from_uploads, PARQUET_FILE

CACHE_DIR = os.path.join("data", "cache")
with open(os.path.join(CACHE_DIR, "Balanco_Energetico.xlsm"), "rb") as f:
    balanco_bytes = f.read()
with open(os.path.join(CACHE_DIR, "gd_gestao.xlsx"), "rb") as f:
    gestao_bytes = f.read()

print(f"Balanco: {len(balanco_bytes):,} bytes | Gestao: {len(gestao_bytes):,} bytes")
print("Iniciando sync (sem Firebase)...")
result = build_consolidated_cache_from_uploads(balanco_bytes, gestao_bytes, firebase_client=None)

if result:
    print("SUCESSO!")
    import pandas as pd
    df = pd.read_parquet(PARQUET_FILE, engine="fastparquet")
    print(f"Parquet: {os.path.getsize(PARQUET_FILE):,} bytes | {len(df):,} registros | {len(df.columns)} colunas")
    object_cols = [c for c in df.columns if df[c].dtype == object]
    if object_cols:
        print(f"AVISO - colunas ainda object: {object_cols}")
    else:
        print("Todos os dtypes OK para Parquet.")
else:
    print("FALHA - verifique os logs acima.")
