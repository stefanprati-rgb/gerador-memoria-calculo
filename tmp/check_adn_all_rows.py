import pandas as pd

cliente_to_find = 'GRUPO ADN S.A.'
file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'

df = pd.read_excel(file_path)
df = df[df['Nome'].str.contains(cliente_to_find, na=False)]

print(f"ANÁLISE DE TODAS AS FATURAS - {cliente_to_find}")
print("-" * 60)

for idx, row in df.iterrows():
    inst = row['Instalação']
    mes = row['Mês de Referência']
    venc = row['Vencimento']
    stat = row['Status']
    canc = row['Cancelada']
    print(f"UC: {inst} | Ref: {mes} | Venc: {venc} | Status: {stat} | Cancel: {canc}")
