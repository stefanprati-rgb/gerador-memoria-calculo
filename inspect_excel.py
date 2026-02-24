import pandas as pd
import json

def inspect():
    gd_path = 'gd_gestao_cobranca-1771957245_2026-02-24.xlsx'
    mc_path = 'mc.xlsx'

    df_gd = pd.read_excel(gd_path)
    print("=== gd_gestao_cobranca ===")
    print("Columns:", list(df_gd.columns))
    print("Data type of columns:")
    for col in df_gd.columns[:10]: # Print first 10 for sample
        print(f"  {col}: {df_gd[col].dtype} - Sample: {df_gd[col].iloc[0]}")
    
    print("\n=== mc.xlsx ===")
    xls = pd.ExcelFile(mc_path)
    print("Sheets:", xls.sheet_names)
    
    for sheet in xls.sheet_names:
        df_mc = pd.read_excel(xls, sheet_name=sheet)
        print(f"\nSheet: {sheet}")
        print("Columns (if any):", list(df_mc.columns))
        print("First 3 rows:")
        print(df_mc.head(3).to_dict('records'))

if __name__ == '__main__':
    inspect()
