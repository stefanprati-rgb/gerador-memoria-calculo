import pandas as pd

cliente_to_find = 'GRUPO ADN S.A.'
file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'

df = pd.read_excel(file_path)

# Normalizar nomes
df['Nome'] = df['Nome'].astype(str).str.strip()
results = df[df['Nome'].str.contains(cliente_to_find, case=False, na=False)]

if not results.empty:
    all_cols = results.columns.tolist()
    # Listar TODAS as colunas para entender a estrutura
    print(f"Colunas disponíveis: {all_cols}")
    
    # Exibir por linha para não cortar
    for i, (idx, row) in enumerate(results.iterrows()):
        print(f"--- Registro {i+1} ---")
        for col in all_cols:
            if not pd.isna(row[col]):
                print(f"{col}: {row[col]}")
else:
    print("Nenhum registro encontrado.")
