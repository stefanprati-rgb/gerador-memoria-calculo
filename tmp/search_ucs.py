import pandas as pd

ucs_to_find = [
    '4003682897',
    '4000493189',
    '4000493190',
    '4003622942',
    '4004088938',
    '4003444738'
]

file_path = 'gd_gestao_cobranca-1773061929_2026-03-09.xlsx'
df = pd.read_excel(file_path)

target_col = 'Instalação'
df[target_col] = df[target_col].astype(str).str.strip()

print("| Instalação | Mês de Ref | Vencimento | Status |")
print("| :--- | :--- | :--- | :--- |")

for uc in ucs_to_find:
    matches = df[df[target_col] == uc]
    if matches.empty:
        print(f"| {uc} | Not found | - | - |")
    else:
        for _, row in matches.iterrows():
            mes = row.get('Mês de Ref', '-')
            venc = row.get('Vencimento', '-')
            if pd.isna(venc):
                venc = row.get('Data de Vencimento', '-')
            status = row.get('Status', '-')
            print(f"| {uc} | {mes} | {venc} | {status} |")
