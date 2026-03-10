import pandas as pd

cliente_to_find = 'GRUPO ADN S.A.'
file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'

df = pd.read_excel(file_path)
df['Nome_norm'] = df['Nome'].astype(str).str.strip().str.upper()
results = df[df['Nome_norm'].str.contains(cliente_to_find.upper(), na=False)]

print(f"RESUMO DE FATURAS - {cliente_to_find}")
print("-" * 50)

# Agregação para o relatório final
for mes in sorted(results['Mês de Referência'].unique()):
    subset = results[results['Mês de Referência'] == mes]
    print(f"\nMES REF: {mes}")
    for idx, row in subset.iterrows():
        print(f"  UC {row['Instalação']} -> Venc: {row['Vencimento']} | Status: {row['Status']} | Cancel: {row['Cancelada']}")
