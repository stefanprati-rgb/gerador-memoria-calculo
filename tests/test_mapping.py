"""
Testes para o mapeamento de colunas e constantes de agrupamento.
"""

from logic.core.mapping import (
    COLUMN_MAPPING,
    get_base_columns,
    get_template_columns,
    GROUPING_FLAG_COL,
    GROUPING_FLAG_VALUE,
    GROUPING_KEYS,
    SUM_COLUMNS,
    PARENT_ROW_FLAG,
    HEADER_MARKER_COLUMNS,
    CLIENT_COLUMN,
    PERIOD_COLUMN,
)


class TestColumnMapping:
    """Testes de sanidade para o mapeamento de colunas."""

    def test_mapping_nao_vazio(self):
        """Deve haver pelo menos 1 mapeamento configurado."""
        assert len(COLUMN_MAPPING) > 0

    def test_get_base_columns_retorna_lista(self):
        """Deve retornar lista com as chaves do mapeamento."""
        cols = get_base_columns()
        assert isinstance(cols, list)
        assert len(cols) == len(COLUMN_MAPPING)

    def test_get_template_columns_retorna_lista(self):
        """Deve retornar lista com os valores do mapeamento."""
        cols = get_template_columns()
        assert isinstance(cols, list)
        assert len(cols) == len(COLUMN_MAPPING)

    def test_colunas_base_esperadas(self):
        """Colunas essenciais da nova base devem estar no mapeamento."""
        base_cols = get_base_columns()
        assert "No. UC" in base_cols
        assert "CPF/CNPJ" in base_cols
        assert "Razao Social" in base_cols
        assert "Referencia" in base_cols
        assert "Distribuidora" in base_cols

    def test_colunas_template_esperadas(self):
        """Colunas essenciais do template devem estar no mapeamento."""
        template_cols = get_template_columns()
        assert "UC" in template_cols
        assert "CNPJ" in template_cols
        assert "Razão Social" in template_cols


class TestGroupingConstants:
    """Testes para as constantes de agrupamento."""

    def test_grouping_flag_col_definida(self):
        """A coluna de flag de agrupamento deve estar definida."""
        assert GROUPING_FLAG_COL == "Excecao Fat."

    def test_grouping_flag_value_definido(self):
        """O valor que ativa agrupamento deve ser 'Agrupamento'."""
        assert GROUPING_FLAG_VALUE == "Agrupamento"

    def test_grouping_keys_definidas(self):
        """As chaves de agrupamento devem ser CPF/CNPJ e Distribuidora."""
        assert "CPF/CNPJ" in GROUPING_KEYS
        assert "Distribuidora" in GROUPING_KEYS

    def test_sum_columns_definidas(self):
        """As colunas financeiras de soma devem estar definidas."""
        assert len(SUM_COLUMNS) > 0
        assert "Boleto Raizen" in SUM_COLUMNS
        assert "Custo c/ GD" in SUM_COLUMNS

    def test_parent_row_flag_definida(self):
        """A flag de linha pai deve estar definida."""
        assert PARENT_ROW_FLAG == "_is_parent"

    def test_header_markers_definidos(self):
        """As colunas-marcador para detecção de header devem estar definidas."""
        assert "No. UC" in HEADER_MARKER_COLUMNS
        assert "CPF/CNPJ" in HEADER_MARKER_COLUMNS

    def test_client_period_columns_definidas(self):
        """As colunas de cliente e período devem estar definidas."""
        assert CLIENT_COLUMN == "Razao Social"
        assert PERIOD_COLUMN == "Referencia"
