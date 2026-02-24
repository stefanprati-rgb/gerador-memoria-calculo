"""
Testes para o módulo de mapeamento de colunas.
"""

from logic.core.mapping import COLUMN_MAPPING, get_base_columns, get_template_columns


class TestMapping:
    """Testes para garantir integridade do mapeamento."""
    
    def test_mapping_nao_vazio(self):
        """O mapeamento deve ter pelo menos uma entrada."""
        assert len(COLUMN_MAPPING) > 0
    
    def test_get_base_columns_retorna_chaves(self):
        """get_base_columns deve retornar as chaves do mapeamento."""
        base_cols = get_base_columns()
        assert base_cols == list(COLUMN_MAPPING.keys())
    
    def test_get_template_columns_retorna_valores(self):
        """get_template_columns deve retornar os valores do mapeamento."""
        template_cols = get_template_columns()
        assert template_cols == list(COLUMN_MAPPING.values())
    
    def test_sem_espacos_extras_nas_chaves(self):
        """Nenhuma chave do mapeamento deve ter espaços extras no início/fim."""
        for key in COLUMN_MAPPING.keys():
            assert key == key.strip(), f"Chave '{key}' tem espaços extras"
    
    def test_sem_espacos_extras_nos_valores(self):
        """Nenhum valor do mapeamento deve ter espaços extras no início/fim."""
        for value in COLUMN_MAPPING.values():
            assert value == value.strip(), f"Valor '{value}' tem espaços extras"
