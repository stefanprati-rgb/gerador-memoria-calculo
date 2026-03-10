import pandas as pd

cliente_to_find = 'GRUPO ADN S.A.'
file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'

print(f"Lendo {file_path} para o cliente {cliente_to_find}...")
df = pd.read_excel(file_path)

# Encontrar a coluna de cliente
possible_cliente_cols = ['Nome', 'Cliente', 'Razão Social']
target_col = None
for col in possible_cliente_cols:
    if col in df.columns:
        target_col = col
        break

if not target_col:
    print(f"Não foi possível encontrar uma coluna de cliente. Colunas: {df.columns.tolist()}")
    exit(1)

# Filtrar pelo cliente (case insensitive e strip)
df[target_col] = df[target_col].astype(str).str.strip()
results = df[df[target_col].str.contains(cliente_to_find, case=False, na=False)]

if results.empty:
    print(f"Nenhum registro encontrado para '{cliente_to_find}'.")
    # Tentar listar alguns nomes para ajudar
    print("Alguns nomes na base:", df[target_col].unique()[:10])
else:
    print(f"Encontrados {len(results)} registros.")
    # Colunas interessantes
    cols = ['Instalação', target_col, 'Mês de Ref', 'Vencimento', 'Data de Vencimento', 'Status']
    cols = [c for c in cols if c in df.columns]
    
    print(results[cols].to_string(index=False))
