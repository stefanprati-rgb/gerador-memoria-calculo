import pandas as pd

file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'
df = pd.read_excel(file_path)

# Filtrar apenas GRUPO ADN S.A.
df = df[df['Nome'].str.contains('GRUPO ADN S.A.', na=False)]

# Filtrar apenas 12-2025
dec_faturas = df[df['Mês de Referência'] == '12-2025']

print(f"Total faturas 12/2025 para ADN: {len(dec_faturas)}")
print("Status encontrados para 12/2025:")
print(dec_faturas['Status'].value_counts())

print("\nVencimentos para 12/2025:")
print(dec_faturas['Vencimento'].value_counts())

# Tentar encontrar pelo menos UMA que esteja 'Atrasado' em 12-2025
atrasadas_12 = dec_faturas[dec_faturas['Status'] == 'Atrasado']
if not atrasadas_12.empty:
    print("\nFaturas de 12/2025 que estão ATRASADAS:")
    for idx, row in atrasadas_12.iterrows():
        print(f"UC: {row['Instalação']} | Venc: {row['Vencimento']} | Cancel: {row['Cancelada']}")
else:
    print("\nNenhuma fatura de 12/2025 está com status 'Atrasado'.")
