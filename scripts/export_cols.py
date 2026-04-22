import pandas as pd
import json
import numpy as np

# fix encoding for json serialization
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if pd.isna(obj):
            return None
        return super(NpEncoder, self).default(obj)

def export_cols():
    gd_path = 'gd_gestao_cobranca-1771957245_2026-02-24.xlsx'
    mc_path = 'mc.xlsx'

    df_gd = pd.read_excel(gd_path)
    
    out = {
        "gd_gestao_cobranca": {
            "columns": list(df_gd.columns),
            "sample": df_gd.head(1).to_dict('records')
        },
        "mc": {}
    }
    
    xls = pd.ExcelFile(mc_path)
    for sheet in xls.sheet_names:
        df_mc = pd.read_excel(xls, sheet_name=sheet)
        out["mc"][sheet] = {
            "columns": list(df_mc.columns) if not df_mc.empty else [],
            "sample": df_mc.head(2).to_dict('records')
        }
        
    with open('cols.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, cls=NpEncoder, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    export_cols()
