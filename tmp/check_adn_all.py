import pandas as pd

cliente_to_find = 'GRUPO ADN S.A.'
file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'

df = pd.read_excel(file_path)
df['Nome_norm'] = df['Nome'].astype(str).str.strip().str.upper()
results = df[df['Nome_norm'].str.contains(cliente_to_find.upper(), na=False)]

# Mostrar todas as faturas (Dezembro e Outras) para entender a mistura
print(f"Relatório de Faturas para {cliente_to_find}:")
print("-" * 80)
cols = ['Instalação', 'Mês de Referência', 'Vencimento', 'Status', 'Cancelada']

# Filtrar apenas as colunas que existem
available_cols = [c for c in cols if c in results.columns]

for idx, row in results.iterrows():
    data = [f"{c}: {row[c]}" for c in available_cols]
    print(" | ".join(data))
print("-" * 80)
