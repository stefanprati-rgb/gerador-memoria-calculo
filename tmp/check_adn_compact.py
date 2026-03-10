import pandas as pd

cliente_to_find = 'GRUPO ADN S.A.'
file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'

df = pd.read_excel(file_path)
df['Nome_norm'] = df['Nome'].astype(str).str.strip().str.upper()
results = df[df['Nome_norm'].str.contains(cliente_to_find.upper(), na=False)]

print(f"Relatório Compacto para {cliente_to_find}:")
for idx, row in results.iterrows():
    inst = row.get('Instalação', '-')
    mes = row.get('Mês de Referência', '-')
    venc = row.get('Vencimento', '-')
    stat = row.get('Status', '-')
    canc = row.get('Cancelada', '-')
    print(f"UC {inst} | Ref {mes} | Venc {venc} | Status {stat} | Cancel {canc}")
