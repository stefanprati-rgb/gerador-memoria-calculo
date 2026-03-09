import openpyxl

wb = openpyxl.load_workbook("mc.xlsx")
ws = wb.active

headers = []
for c in range(1, 15):
    val = ws.cell(row=1, column=c).value
    if val:
        headers.append(val)

print("HEADERS REAIS NO MC.XLSX:")
for h in headers:
    print(f"[{h}]")

# Let's check which ones match
LEGACY = {
    "Data  Ref": "Referencia",
    "UC": "No. UC",
    "CNPJ": "CPF/CNPJ",
    "Razão Social": "Razao Social",
    "Energia compensada pela Raízen (kWh)": "Cred. Consumido Raizen",
    "Regra aplicada": "Desconto Contratado",
    "Status financeiro": "Status Pos-Faturamento",
    "Boleto faturado (R$)": "Boleto Raizen",
    "Tarifa Distribuidora": "Tarifa Raizen",
    "Custo com GD R$": "Custo c/ GD",
    "Custo sem GD R$": "Custo s/ GD",
    "Economia (R$)": "Ganho total Padrão",
}

print("\nMATCHES:")
for h in headers:
    stripped = str(h).strip()
    if stripped in LEGACY:
        print(f"[{stripped}] -> MATCHES!")
    else:
        print(f"[{stripped}] -> NO MATCH!")
