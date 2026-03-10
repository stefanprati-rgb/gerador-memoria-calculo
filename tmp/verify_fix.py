import os
import pandas as pd
import logging
from logic.services.sync_service import _process_dataframes, PARQUET_FILE

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)

BALANCO_LOCAL = r"C:\Projetos\memoria_de_calculo\data\cache\Balanco_Energetico.xlsm"
GESTAO_LOCAL = r"C:\Projetos\memoria_de_calculo\gd_gestao_cobranca-1773061929_2026-03-09.xlsx"

# Ensure the local files exist for the test (copying if needed)
import shutil
os.makedirs(os.path.dirname(BALANCO_LOCAL), exist_ok=True)
if os.path.exists(GESTAO_LOCAL) and not os.path.exists(r"C:\Projetos\memoria_de_calculo\data\cache\gd_gestao.xlsx"):
    shutil.copy(GESTAO_LOCAL, r"C:\Projetos\memoria_de_calculo\data\cache\gd_gestao.xlsx")

print("Rodando processamento consolidado...")
# Passamos bytes fictícios para o gatilho, o script lê o arquivo local GESTAO_LOCAL
success = _process_dataframes(BALANCO_LOCAL, b"fake", r"C:\Projetos\memoria_de_calculo\data\cache\gd_gestao.xlsx")

if success:
    print("Processamento concluído com sucesso!")
    df = pd.read_parquet(PARQUET_FILE, engine="fastparquet")
    
    # Verificar UCs do GRUPO ADN S.A.
    cliente_adn = df[df['Razao Social'].str.contains('GRUPO ADN', na=False, case=False)]
    
    print(f"\nResultados para GRUPO ADN S.A. (Encontrados {len(cliente_adn)} registros):")
    cols = ['No. UC', 'Referencia', 'Vencimento', 'Status Pos-Faturamento']
    cols = [c for c in cols if c in cliente_adn.columns]
    
    # Filtrar faturas de Dezembro para ver se ainda estão "Atrasado"
    dec_adn = cliente_adn[pd.to_datetime(cliente_adn['Referencia']).dt.month == 12]
    print("\nFaturas de Dezembro/2025:")
    print(dec_adn[cols].to_string(index=False))
    
    # Verificar se alguma de Dezembro ainda está "Atrasado"
    atrasadas_dec = dec_adn[dec_adn['Status Pos-Faturamento'] == 'Atrasado']
    if not atrasadas_dec.empty:
        print("\nAVISO: Ainda existem faturas de Dezembro com status 'Atrasado'!")
    else:
        print("\nSUCESSO: Nenhuma fatura de Dezembro está com status 'Atrasado'.")
else:
    print("Falha no processamento.")
