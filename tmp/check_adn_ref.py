import pandas as pd

cliente_to_find = 'GRUPO ADN S.A.'
file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'

print(f"Buscando faturas do cliente: {cliente_to_find}\n")
df = pd.read_excel(file_path)

# Normalizar nomes para busca
df['Nome_norm'] = df['Nome'].astype(str).str.strip().str.upper()
results = df[df['Nome_norm'].str.contains(cliente_to_find.upper(), na=False)]

if results.empty:
    print("Nenhum registro encontrado.")
else:
    # Identificar colunas de referência e vencimento
    header_map = {str(c).strip().lower(): str(c) for c in df.columns}
    ref_col = header_map.get("mês de referência", header_map.get("mes de referencia", header_map.get("referência", "Mês de Referência")))
    venc_col = 'Vencimento' # Pelo que vimos no log anterior existe essa coluna
    status_col = 'Status'
    cancel_col = 'Cancelada'
    uc_col = 'Instalação'

    cols = [uc_col, ref_col, venc_col, status_col, cancel_col]
    cols = [c for c in cols if c in df.columns]

    print(results[cols].to_string(index=False))
    
    print("\n--- Verificação de Tipos da Coluna Mês de Referência ---")
    if ref_col in results.columns:
        print(f"Tipo da coluna {ref_col}: {results[ref_col].dtype}")
        print(f"Exemplos de valores únicos: {results[ref_col].unique()}")
