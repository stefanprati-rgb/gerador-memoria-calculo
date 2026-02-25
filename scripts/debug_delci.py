"""Debug: simula o fluxo do app para DELCI e verifica o _is_parent."""
import pandas as pd
from logic.adapters.excel_adapter import BaseExcelReader
from logic.core.mapping import PARENT_ROW_FLAG, GROUPING_FLAG_COL
from logic.services.orchestrator import Orchestrator

FILE = r"C:\Projetos\memoria_de_calculo\Balanco_Energetico_Raizen.xlsm"
TEMPLATE = "mc.xlsx"

orch = Orchestrator(FILE, TEMPLATE)

# 1. Verificar se Excecao Fat. está carregada
print("Colunas carregadas:", list(orch.reader.df.columns))
print(f"'{GROUPING_FLAG_COL}' presente:", GROUPING_FLAG_COL in orch.reader.df.columns)

# 2. Filtrar DELCI
delci = orch.reader.filter_data(["DELCI PEREIRA DA SILVA CIA LTDA"], orch.get_available_periods())
print(f"\nDELCI registros: {len(delci)}")

if GROUPING_FLAG_COL in delci.columns:
    print(f"Valores Excecao Fat.:")
    print(delci[GROUPING_FLAG_COL].value_counts(dropna=False))

# 3. Aplicar agrupamento
result = orch._apply_grouping(delci)
print(f"\nApós agrupamento: {len(result)} linhas")
print(f"_is_parent True: {result[PARENT_ROW_FLAG].sum()}")
print(f"_is_parent False: {(~result[PARENT_ROW_FLAG]).sum()}")

# 4. Mostrar amostra
if result[PARENT_ROW_FLAG].any():
    print("\n--- Linhas Parent ---")
    parents = result[result[PARENT_ROW_FLAG]]
    print(parents[["No. UC", "Razao Social", "Excecao Fat.", "Boleto Raizen"]].head())
