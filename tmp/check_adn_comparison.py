import pandas as pd

file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'
df = pd.read_excel(file_path)
df = df[df['Nome'].str.contains('GRUPO ADN S.A.', na=False)]

print("ANÁLISE ADN - NOV vs DEZ")
for mes in ['11-2025', '12-2025']:
    subset = df[df['Mês de Referência'] == mes]
    print(f"\nMes: {mes} ({len(subset)} faturas)")
    print(subset[['Instalação', 'Vencimento', 'Status', 'Cancelada']].to_string(index=False))
