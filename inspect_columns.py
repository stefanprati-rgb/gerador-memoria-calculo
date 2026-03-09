import pandas as pd
from logic.services.sync_service import PARQUET_FILE
import sys

try:
    df = pd.read_parquet(PARQUET_FILE, engine="fastparquet")
    print("Colunas reais no Parquet (Balanço Energético processado):")
    for c in df.columns:
        print(f"'{c}'")
except Exception as e:
    print(f"Erro ao ler parquet: {e}")
