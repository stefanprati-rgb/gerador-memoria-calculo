"""Investiga registros com Agrupamento E valores financeiros preenchidos."""
import pandas as pd

FILE = r"C:\Projetos\memoria_de_calculo\Balanco_Energetico_Raizen.xlsm"

df = pd.read_excel(FILE, sheet_name="Balanco Operacional", header=5,
                   usecols=["Referencia", "No. UC", "CPF/CNPJ", "Razao Social", 
                            "Distribuidora", "Excecao Fat.", "Boleto Raizen",
                            "Ganho total Padrão", "Faturar", "UC p Rateio", "Main"])
df.columns = df.columns.str.strip()

# 1. Registros COM Agrupamento
agr = df[df["Excecao Fat."].astype(str).str.strip() == "Agrupamento"]
print(f"Total com Excecao Fat. = Agrupamento: {len(agr)}")
print(f"  - Com Boleto preenchido: {agr['Boleto Raizen'].notna().sum()}")
print(f"  - Com Main=Y: {(agr['Main'].astype(str) == 'Y').sum()}")
print(f"  - Com Faturar=Y: {(agr['Faturar'].astype(str) == 'Y').sum()}")

# 2. Buscar DELCI por CPF/CNPJ em vez de nome
delci_cpf = df[df["Razao Social"].astype(str).str.contains("DELCI", case=False, na=False)]["CPF/CNPJ"].iloc[0]
print(f"\nDELCI CPF/CNPJ: {delci_cpf}")
delci_tudo = df[df["CPF/CNPJ"] == delci_cpf]
ref = delci_tudo["Referencia"].dropna().iloc[0]
delci_ref = delci_tudo[delci_tudo["Referencia"] == ref]

with open("delci_output2.txt", "w", encoding="utf-8") as f:
    f.write(f"CPF/CNPJ: {delci_cpf} | Ref: {ref} | Total: {len(delci_ref)}\n\n")
    f.write(f"{'UC':<12} {'RazaoSocial':<30} {'Excecao':<15} {'Main':<6} {'Faturar':<8} {'Boleto':>12} {'Ganho':>12}\n")
    f.write("-" * 110 + "\n")
    for _, r in delci_ref.iterrows():
        exc = str(r['Excecao Fat.']) if pd.notna(r['Excecao Fat.']) else '-'
        main = str(r['Main']) if pd.notna(r['Main']) else '-'
        fat = str(r['Faturar']) if pd.notna(r['Faturar']) else '-'
        bol = f"{r['Boleto Raizen']:.2f}" if pd.notna(r['Boleto Raizen']) else '-'
        gan = f"{r['Ganho total Padrão']:.2f}" if pd.notna(r['Ganho total Padrão']) else '-'
        rs = str(r['Razao Social'])[:28] if pd.notna(r['Razao Social']) else '-'
        f.write(f"{r['No. UC']:<12} {rs:<30} {exc:<15} {main:<6} {fat:<8} {bol:>12} {gan:>12}\n")

# 3. Amostra de Agrupamento com boleto
agr_bol = agr[agr["Boleto Raizen"].notna()]
if len(agr_bol) > 0:
    with open("agrupamento_amostra.txt", "w", encoding="utf-8") as f:
        f.write(f"Agrupamentos com Boleto preenchido: {len(agr_bol)}\n\n")
        for _, r in agr_bol.head(5).iterrows():
            cpf = r["CPF/CNPJ"]
            ref2 = r["Referencia"]
            grupo = df[(df["CPF/CNPJ"] == cpf) & (df["Referencia"] == ref2)]
            f.write(f"\n--- CPF: {cpf} | Ref: {ref2} | Total linhas: {len(grupo)} ---\n")
            f.write(f"{'UC':<12} {'RazaoSocial':<30} {'Excecao':<15} {'Main':<6} {'Faturar':<8} {'Boleto':>12}\n")
            for _, g in grupo.iterrows():
                exc = str(g['Excecao Fat.']) if pd.notna(g['Excecao Fat.']) else '-'
                main = str(g['Main']) if pd.notna(g['Main']) else '-'
                fat = str(g['Faturar']) if pd.notna(g['Faturar']) else '-'
                bol = f"{g['Boleto Raizen']:.2f}" if pd.notna(g['Boleto Raizen']) else '-'
                rs = str(g['Razao Social'])[:28] if pd.notna(g['Razao Social']) else '-'
                f.write(f"{g['No. UC']:<12} {rs:<30} {exc:<15} {main:<6} {fat:<8} {bol:>12}\n")

print("Salvo em delci_output2.txt e agrupamento_amostra.txt")
