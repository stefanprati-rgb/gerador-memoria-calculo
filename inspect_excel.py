import pandas as pd
import json

file_path = r'C:\Projetos\memoria_de_calculo\Balanco_Energetico_Raizen.xlsm'
xl = pd.ExcelFile(file_path)

print(f"Abas: {xl.sheet_names}")

# Assumindo que a base é a primeira aba
df = pd.read_excel(file_path, sheet_name=0)

columns = df.columns.tolist()

res = {
    "total_rows": len(df),
    "columns": columns,
    "first_row": df.head(1).to_dict('records')[0] if len(df) > 0 else {}
}

with open("cols.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)

print("Verifique cols.json para as colunas. Listando as primeiras 20 colunas para agilidade:")
for c in columns[:20]:
    print(c)
