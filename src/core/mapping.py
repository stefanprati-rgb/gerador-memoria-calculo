"""
Mapeamento de colunas entre a planilha base gd_gestao_cobranca e a planilha de template mc.
"""

COLUMN_MAPPING = {
    # 'Coluna na base gd_gestao': 'Coluna no template mc'
    "Mês de Referência": "Data  Ref",
    "Instalação": "UC",
    "CNPJ/CPF": "CNPJ",
    "Nome": "Razão Social",
    "Distribuidora": "Distribuidora",
    "Crédito kWh": "Energia compensada pela Raízen (kWh)",
    "Tipo Contrato": "Regra aplicada",
    "Vencimento": "Vencimento ",
    "Status": "Status financeiro",
    "Valor da cobrança R$": "Boleto faturado (R$)",
    "Tarifa aplicada R$": "Tafira Distribuidora",
    "Custo com GD R$": "Custo com GD R$",
    "Custo sem GD R$": "Custo sem GD R$",
    "Economia R$": "Economia (R$)"
}

def get_base_columns() -> list[str]:
    """Retorna as colunas esperadas na planilha base que faremos o de-para."""
    return list(COLUMN_MAPPING.keys())

def get_template_columns() -> list[str]:
    """Retorna as colunas destino na planilha de template."""
    return list(COLUMN_MAPPING.values())
