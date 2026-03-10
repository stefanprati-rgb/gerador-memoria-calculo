import pandas as pd

cliente_to_find = 'GRUPO ADN S.A.'
file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'

print(f"Buscando faturas do cliente: {cliente_to_find}\n")
df = pd.read_excel(file_path)

# Normalizar nomes para busca
df['Nome_norm'] = df['Nome'].astype(str).str.strip().str.upper()
results = df[df['Nome_norm'].str.contains(cliente_to_find.upper(), na=False)]

# Colunas de interesse
cols = ['Instalação', 'Mês de Referência', 'Vencimento', 'Status', 'Cancelada']
cols = [c for c in cols if c in df.columns]

if not results.empty:
    for idx, row in results.iterrows():
        print(" | ".join([f"{c}: {row[c]}" for c in cols]))
else:
    print("Nenhum registro encontrado.")
