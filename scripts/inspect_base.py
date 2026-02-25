"""
Script para inspecionar a nova base Balanco_Energetico_Raizen.xlsm.
Detecta header dinamicamente e analisa coluna Excecao Fat.
"""
import pandas as pd
import json

FILE = r"C:\Projetos\memoria_de_calculo\Balanco_Energetico_Raizen.xlsm"
SHEET = "Balanco Operacional"
MARKER_COLS = ["No. UC", "CPF/CNPJ"]

# 1. Detectar header dinamicamente
print("=== DETECÇÃO DINÂMICA DO HEADER ===")
raw = pd.read_excel(FILE, sheet_name=SHEET, nrows=20, header=None)
header_row = None
for i, row in raw.iterrows():
    vals = set(str(v).strip() for v in row.values if pd.notna(v))
    if all(m in vals for m in MARKER_COLS):
        header_row = i
        break

print(f"Header detectado na linha {header_row} (0-indexed no pandas)")
print(f"Isso equivale à linha {header_row + 1} no Excel")

if header_row is None:
    print("ERRO: Não foi possível detectar o header!")
    exit(1)

# 2. Ler dados com header correto
df = pd.read_excel(FILE, sheet_name=SHEET, header=header_row)
print(f"\nTotal de registros: {len(df)}")
print(f"Total de colunas: {len(df.columns)}")

# 3. Excecao Fat. — valores únicos
print("\n=== VALORES DE 'Excecao Fat.' ===")
if "Excecao Fat." in df.columns:
    vc = df["Excecao Fat."].value_counts(dropna=False)
    print(vc.to_string())
else:
    print("COLUNA NÃO ENCONTRADA!")

# 4. Amostra de agrupados
print("\n=== AMOSTRA DE DADOS COM EXCEÇÃO ===")
if "Excecao Fat." in df.columns:
    exc = df[df["Excecao Fat."].notna() & (df["Excecao Fat."] != "")]
    cols_amostra = ["No. UC", "CPF/CNPJ", "Razao Social", "Distribuidora", "Referencia", "Excecao Fat."]
    cols_amostra = [c for c in cols_amostra if c in df.columns]
    print(f"Registros com exceção preenchida: {len(exc)}")
    if len(exc) > 0:
        print(exc[cols_amostra].head(15).to_string())

# 5. Checar quantos CPF/CNPJ+Distribuidora têm múltiplas UCs
print("\n=== AGRUPAMENTO CPF/CNPJ × DISTRIBUIDORA ===")
if all(c in df.columns for c in ["CPF/CNPJ", "Distribuidora", "No. UC"]):
    grp = df.groupby(["CPF/CNPJ", "Distribuidora"])["No. UC"].nunique()
    multi = grp[grp > 1]
    print(f"Combinações com múltiplas UCs: {len(multi)}")
    if len(multi) > 0:
        print(multi.head(10).to_string())
