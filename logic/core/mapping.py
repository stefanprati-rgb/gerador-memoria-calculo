"""
Mapeamento de colunas entre a planilha base Balanço Energético e o template mc.xlsx.
Inclui constantes para detecção de header e lógica de agrupamento.
"""

# --- DETECÇÃO DINÂMICA DE HEADER ---
# Colunas-marcador usadas para localizar automaticamente a linha de cabeçalho
HEADER_MARKER_COLUMNS = ["No. UC", "CPF/CNPJ"]

# Quantidade máxima de linhas a varrer buscando o header
HEADER_SCAN_ROWS = 20

# --- AGRUPAMENTO DE FATURAS ---
# Coluna que indica se a UC participa de um agrupamento
GROUPING_FLAG_COL = "Excecao Fat."

# Valor que ativa o agrupamento
GROUPING_FLAG_VALUE = "Agrupamento"

# Colunas usadas como chave de agrupamento (CPF/CNPJ × Distribuidora)
GROUPING_KEYS = ["CPF/CNPJ", "Distribuidora"]

# Colunas financeiras que devem ser SOMADAS na linha "Fatura Pai"
SUM_COLUMNS = [
    "Cred. Consumido Raizen",
    "Boleto Raizen",
    "Tarifa Raizen",
    "Custo c/ GD",
    "Custo s/ GD",
    "Ganho total Padrão",
]

# Flag interna para marcar linhas "Fatura Pai" no DataFrame (não existe na base)
PARENT_ROW_FLAG = "_is_parent"

# --- MAPEAMENTO BASE → TEMPLATE ---
COLUMN_MAPPING = {
    # 'Coluna na base Balanço Energético': 'Coluna no template mc.xlsx'
    "Referencia": "Data  Ref",
    "No. UC": "UC",
    "CPF/CNPJ": "CNPJ",
    "Razao Social": "Razão Social",
    "Distribuidora": "Distribuidora",
    "Cred. Consumido Raizen": "Energia compensada pela Raízen (kWh)",
    "Desconto Contratado": "Regra aplicada",
    "Status Pos-Faturamento": "Status financeiro",
    "Boleto Raizen": "Boleto faturado (R$)",
    "Tarifa Raizen": "Tafira Distribuidora",
    "Custo c/ GD": "Custo com GD R$",
    "Custo s/ GD": "Custo sem GD R$",
    "Ganho total Padrão": "Economia (R$)",
}

# Colunas de enriquecimento (vêm do merge com gd_gestao, não existem no .xlsm puro)
ENRICHMENT_MAPPING = {
    "Vencimento": "Vencimento",
}

# Coluna usada para identificar clientes na interface (seleção por nome)
CLIENT_COLUMN = "Razao Social"

# Coluna usada para identificar períodos na interface
PERIOD_COLUMN = "Referencia"


def get_base_columns() -> list[str]:
    """Retorna as colunas esperadas na planilha base que faremos o de-para."""
    return list(COLUMN_MAPPING.keys())


def get_template_columns() -> list[str]:
    """Retorna as colunas destino na planilha de template."""
    return list(COLUMN_MAPPING.values())


def get_required_columns() -> list[str]:
    """Retorna TODAS as colunas necessárias para leitura otimizada (mapeamento + agrupamento)."""
    cols = set(COLUMN_MAPPING.keys())
    cols.add(GROUPING_FLAG_COL)
    cols.update(GROUPING_KEYS)
    return list(cols)
