"""
Fixtures compartilhadas para os testes do projeto Memória de Cálculo.
"""

import pytest
import pandas as pd
import openpyxl
import io
import os


@pytest.fixture
def sample_base_df():
    """DataFrame simulando a planilha gd_gestao_cobranca com dados mínimos."""
    return pd.DataFrame({
        "Mês de Referência": ["01/2026", "01/2026", "02/2026"],
        "Instalação": ["UC001", "UC002", "UC001"],
        "CNPJ/CPF": ["11.111.111/0001-01", "22.222.222/0001-02", "11.111.111/0001-01"],
        "Nome": ["Cliente Alpha", "Cliente Beta", "Cliente Alpha"],
        "Distribuidora": ["CEMIG", "CPFL", "CEMIG"],
        "Crédito kWh": [1500.5, 2300.0, 1600.75],
        "Tipo Contrato": ["Desconto", "Desconto", "Desconto"],
        "Vencimento": ["2026-01-15", "2026-01-20", "2026-02-15"],
        "Status": ["Pago", "Pendente", "Pendente"],
        "Valor da cobrança R$": [350.00, 520.50, 370.25],
        "Tarifa aplicada R$": [0.85, 0.92, 0.85],
        "Custo com GD R$": [1275.43, 2116.00, 1360.64],
        "Custo sem GD R$": [1625.43, 2636.50, 1730.89],
        "Economia R$": [350.00, 520.50, 370.25],
    })


@pytest.fixture
def sample_base_xlsx(sample_base_df, tmp_path):
    """Arquivo .xlsx temporário com os dados da base simulada."""
    path = tmp_path / "base_test.xlsx"
    sample_base_df.to_excel(path, index=False)
    return str(path)


@pytest.fixture
def sample_template_xlsx(tmp_path):
    """Arquivo template mc.xlsx mínimo para testes."""
    path = tmp_path / "mc_test.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # Headers do template (com espaços extras como no real para testar normalização)
    headers = [
        "Data  Ref", "UC", "CNPJ", "Razão Social", "Distribuidora",
        "Energia compensada pela Raízen (kWh)", "Regra aplicada",
        "Vencimento ", "Status financeiro", "Boleto faturado (R$)",
        "Tafira Distribuidora", "Custo com GD R$", "Custo sem GD R$",
        "Economia (R$)"
    ]
    
    for col_idx, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_idx, value=header)
    
    wb.save(path)
    return str(path)
