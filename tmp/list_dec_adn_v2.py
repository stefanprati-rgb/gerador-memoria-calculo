import pandas as pd

cliente_to_find = 'GRUPO ADN S.A.'
file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'

df = pd.read_excel(file_path)
df['Nome_norm'] = df['Nome'].astype(str).str.strip().str.upper()
results = df[df['Nome_norm'].str.contains(cliente_to_find.upper(), na=False)]

# Focar apenas em ADN e Dezembro
dec_faturas = results[results['Mês de Referência'] == '12-2025']

print(f"Total de faturas de 12-2025 para {cliente_to_find}: {len(dec_faturas)}")
cols = ['Instalação', 'Mês de Referência', 'Vencimento', 'Status', 'Cancelada']

# Listar todas agrupadas por status/vencimento
for status in dec_faturas['Status'].unique():
    subset = dec_faturas[dec_faturas['Status'] == status]
    print(f"\nStatus: {status} ({len(subset)} faturas)")
    for idx, row in subset.iterrows():
        print(f"  UC: {row['Instalação']} | Vencimento: {row['Vencimento']} | Cancelada: {row['Cancelada']}")
