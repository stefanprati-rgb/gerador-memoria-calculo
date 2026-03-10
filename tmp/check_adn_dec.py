import pandas as pd

cliente_to_find = 'GRUPO ADN S.A.'
file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'

df = pd.read_excel(file_path)

# Normalizar nomes para busca
df['Nome_norm'] = df['Nome'].astype(str).str.strip().str.upper()
results = df[df['Nome_norm'].str.contains(cliente_to_find.upper(), na=False)]

# Colunas de interesse
cols = ['Instalação', 'Mês de Referência', 'Vencimento', 'Status', 'Cancelada']

if not results.empty:
    print(f"Total de registros encontrados: {len(results)}")
    
    # Filtrar faturas de Dezembro 2025
    dec_faturas = results[results['Mês de Referência'] == '12-2025']
    if dec_faturas.empty:
        print("Nenhuma fatura encontrada para 12-2025 diretamente.")
        print("Valores únicos de Mês de Referência encontrados:")
        print(results['Mês de Referência'].unique())
    else:
        print("\nFaturas com Mês de Ref 12-2025 encontradas:")
        for idx, row in dec_faturas.iterrows():
            line = " | ".join([f"{c}: {row[c]}" for c in cols if c in row])
            print(f"Idx: {idx} | {line}")

    # Verificar se existem faturas com status Atrasado que não são canceladas
    atrasadas_nao_canceladas = results[(results['Status'] == 'Atrasado') & (results['Cancelada'] != 'Sim')]
    if not atrasadas_nao_canceladas.empty:
        print("\nFaturas ATRASADAS e NÃO CANCELADAS:")
        for idx, row in atrasadas_nao_canceladas.iterrows():
            line = " | ".join([f"{c}: {row[c]}" for c in cols if c in row])
            print(f"Idx: {idx} | {line}")
else:
    print("Nenhum registro encontrado.")
