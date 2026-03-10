import pandas as pd

cliente_to_find = 'GRUPO ADN S.A.'
file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'

df = pd.read_excel(file_path)
df['Nome_norm'] = df['Nome'].astype(str).str.strip().str.upper()
results = df[df['Nome_norm'].str.contains(cliente_to_find.upper(), na=False)]

dec_faturas = results[results['Mês de Referência'] == '12-2025']

print(f"Total de faturas de 12-2025: {len(dec_faturas)}")
cols = ['Instalação', 'Mês de Referência', 'Vencimento', 'Status', 'Cancelada']

# Listar algumas individualmente
for i, (idx, row) in enumerate(dec_faturas.iterrows()):
    line = " | ".join([f"{c}: {row[c]}" for c in cols if c in row])
    print(f"{i+1}. {line}")
    if i >= 10: 
        print("... (truncado)")
        break
