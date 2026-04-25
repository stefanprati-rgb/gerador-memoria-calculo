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

# Modos explícitos de agrupamento suportados pela aplicação
GROUPING_MODE_DEFAULT = "default"
GROUPING_MODE_DISTRIBUTOR = "distributor"
GROUPING_MODE_CNPJ = "cnpj"
GROUPING_MODE_NONE = "none"

# Coluna comercial usada pela Raízen para agrupar faturas de grandes clientes (ex: DELCI)
GROUPING_IBM_COL = "No. IBM"

# Colunas de Hierarquia (Balanço Energético)
HIERARCHY_KEY_COL = "UC p Rateio"
HIERARCHY_PARENT_COL = "Main"
HIERARCHY_PARENT_VALUE = "Y"

# Chave usada para enriquecimento/vínculo de dados externos
ENRICHMENT_KEY = "No. UC"

# Código único da unidade negociada vindo da base Balanço Energético.
ID_UC_NEGOCIADA_COL = "id_uc_negociada"

# Coluna técnica: instalação original vinda da Gestão de Cobrança.
PORTAL_UC_COL = "_portal_uc"

# Coluna para número da conta (Gestão de Cobrança)
ACCOUNT_NUMBER_COL = "Número da conta"

# Colunas financeiras que devem ser SOMADAS na linha "Fatura Pai"
SUM_COLUMNS = [
    "Cred. Consumido Raizen",
    "Valor Enviado Emissão",
    "Tarifa Raizen",
    "Custo c/ GD",
    "Custo s/ GD",
    "Ganho total Padrão",
]

# Flag interna para marcar linhas "Fatura Pai" no DataFrame (não existe na base)
PARENT_ROW_FLAG = "_is_parent"

# Flag interna para marcar linhas filhas em agrupamentos
CHILD_ROW_FLAG = "_is_child"

# Flag interna para marcar linhas separadoras em branco (não existe na base)
SEPARATOR_ROW_FLAG = "_is_separator"

# Flag interna para marcar linhas com inconsistências financeiras grotescas
# --- CLASSIFICAÇÃO DE ORIGEM ---
# Coluna da base que indica a origem do dado (Fatura, Contrato, Demonstrativo etc.)
CLASSIFICATION_SOURCE_COL = "Fonte dos Dados"

# Valor(es) que classificam como "Fatura" (leitura real / PDF)
CLASSIFICATION_FATURA_VALUES = {"Fatura"}

# Rótulos aplicados na coluna de saída
CLASSIFICATION_LABEL_FATURA = "Fatura"
CLASSIFICATION_LABEL_REGRA = "Regra de Negócio"

# Nome da coluna de saída no relatório
CLASSIFICATION_COL = "Classificação"

# --- MAPEAMENTO BASE → TEMPLATE ---
COLUMN_MAPPING = {
    # 'Coluna na base Balanço Energético': 'Coluna no destino'
    ID_UC_NEGOCIADA_COL: "Código Único da Unidade",
    "Referencia": "Mês de Referência",
    "No. UC": "Instalação (UC)",
    ACCOUNT_NUMBER_COL: "Nº Conta",
    "CPF/CNPJ": "CPF/CNPJ",
    "Razao Social": "Cliente (Razão Social)",
    "Distribuidora": "Distribuidora",
    "Cred. Consumido Raizen": "Energia Compensada (kWh)",
    "Desconto Contratado": "% Desconto Acordado",
    "Vencimento": "Data de Vencimento",
    "Status Pos-Faturamento": "Situação do Pagamento",
    "Valor Enviado Emissão": "Fatura Raízen (R$)",
    "Tarifa Raizen": "Tarifa Aplicada (R$)",
    "Custo c/ GD": "Custo c/ Desconto GD",
    "Custo s/ GD": "Custo s/ Desconto GD",
    "Ganho total Padrão": "Economia Gerada (R$)",
    # Coluna calculada — não vem diretamente da base, é derivada de CLASSIFICATION_SOURCE_COL
    CLASSIFICATION_COL: "Tipo de Faturamento",
}

# Coluna usada para identificar clientes na interface (seleção por nome)
CLIENT_COLUMN = "Razao Social"

# Colunas que existem no mapping, mas cuja ausência na base original não impede o processamento
OPTIONAL_BASE_COLUMNS = [
    "Status Pos-Faturamento",
    "Vencimento",
    ACCOUNT_NUMBER_COL,
    CLASSIFICATION_COL,  # Coluna derivada — calculada pelo orchestrator, jamais presente no Excel fonte
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
    # A coluna de classificação é derivada, não lida da base — remover do usecols
    cols.discard(CLASSIFICATION_COL)
    cols.add(GROUPING_FLAG_COL)
    cols.update(GROUPING_KEYS)
    # Incluir colunas de hierarquia (Balanço Energético) para o agrupamento correto
    cols.add(HIERARCHY_KEY_COL)
    cols.add(HIERARCHY_PARENT_COL)
    # Incluir coluna comercial IBM
    cols.add(GROUPING_IBM_COL)
    # Incluir coluna de origem para classificação
    cols.add(CLASSIFICATION_SOURCE_COL)
    return list(cols)
