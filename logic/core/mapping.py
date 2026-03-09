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
    # 'Coluna na base Balanço Energético': 'Coluna no destino'
    "Referencia": "Referencia",
    "No. UC": "No. UC",
    "CPF/CNPJ": "CPF/CNPJ",
    "Razao Social": "Razao Social",
    "Distribuidora": "Distribuidora",
    "Cred. Consumido Raizen": "Cred. Consumido Raizen",
    "Desconto Contratado": "Desconto Contratado",
    "Status Pos-Faturamento": "Status Pos-Faturamento",
    "Boleto Raizen": "Boleto Raizen",
    "Tarifa Raizen": "Tarifa Raizen",
    "Custo c/ GD": "Custo c/ GD",
    "Custo s/ GD": "Custo s/ GD",
    "Ganho total Padrão": "Ganho total Padrão",
}

# Colunas de enriquecimento (vêm do merge com gd_gestao, não existem no .xlsm puro)
ENRICHMENT_MAPPING = {
    "Vencimento": "Vencimento",
}

# Coluna usada para identificar clientes na interface (seleção por nome)
CLIENT_COLUMN = "Razao Social"

# Colunas que existem no mapping, mas cuja ausência na base original não impede o processamento
OPTIONAL_BASE_COLUMNS = [
    "Status Pos-Faturamento",
]

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
