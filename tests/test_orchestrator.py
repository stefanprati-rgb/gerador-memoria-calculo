"""
Testes para o serviço de orquestração com identificação de agrupamento.
"""

import pytest
import zipfile
import io

from logic.services.orchestrator import Orchestrator
from logic.core.mapping import PARENT_ROW_FLAG


class TestOrchestrator:
    """Testes do orquestrador de geração de planilhas."""

    def test_inicializacao(self, sample_base_xlsx, sample_template_xlsx):
        """Deve inicializar sem erros com arquivos válidos."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        assert orch is not None

    def test_get_available_clients(self, sample_base_xlsx, sample_template_xlsx):
        """Deve retornar a lista de clientes da base."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        clients = orch.get_available_clients()

        assert "Cliente Alpha" in clients
        assert "Cliente Beta" in clients
        assert "Cliente Gamma" in clients

    def test_get_available_periods(self, sample_base_xlsx, sample_template_xlsx):
        """Deve retornar a lista de períodos da base."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        periods = orch.get_available_periods()

        assert len(periods) == 2

    def test_count_filtered(self, sample_base_xlsx, sample_template_xlsx):
        """Deve retornar contagem correta dos registros filtrados."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        count = orch.count_filtered(["Cliente Alpha"], orch.get_available_periods())

        assert count == 2

    def test_generate_retorna_bytes(self, sample_base_xlsx, sample_template_xlsx):
        """Deve retornar bytes quando há dados para gerar."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        result = orch.generate(["Cliente Alpha"], orch.get_available_periods())

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_retorna_none_sem_dados(self, sample_base_xlsx, sample_template_xlsx):
        """Deve retornar None quando não há dados após filtragem."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        result = orch.generate(["Cliente Fantasma"], orch.get_available_periods())

        assert result is None


class TestAgrupamento:
    """Testes da identificação de Faturas Pai existentes na base."""

    def test_identifica_fatura_pai(self, sample_base_xlsx, sample_template_xlsx):
        """Linhas com Excecao Fat. = 'Agrupamento' devem ser marcadas como parent."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        filtered = orch.reader.filter_data(["Cliente Gamma"], orch.get_available_periods())

        result = orch._apply_grouping(filtered)

        # Gamma tem 2 UCs com Agrupamento — ambas marcadas como parent
        parent_rows = result[result[PARENT_ROW_FLAG] == True]
        assert len(parent_rows) == 2

    def test_valores_preservados_sem_soma(self, sample_base_xlsx, sample_template_xlsx):
        """Os valores financeiros NÃO devem ser somados — a base já traz o correto."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        filtered = orch.reader.filter_data(["Cliente Gamma"], orch.get_available_periods())

        result = orch._apply_grouping(filtered)

        # Nenhuma linha extra criada — mesmo número de registros
        assert len(result) == len(filtered)

        # Valores originais preservados
        parent_rows = result[result[PARENT_ROW_FLAG] == True]
        assert parent_rows.iloc[0]["Boleto Raizen"] == pytest.approx(200.00)
        assert parent_rows.iloc[1]["Boleto Raizen"] == pytest.approx(180.00)

    def test_nao_marca_sem_flag(self, sample_base_xlsx, sample_template_xlsx):
        """Clientes sem Excecao Fat. = 'Agrupamento' não devem ter parent=True."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        filtered = orch.reader.filter_data(["Cliente Alpha"], orch.get_available_periods())

        result = orch._apply_grouping(filtered)

        parent_rows = result[result[PARENT_ROW_FLAG] == True]
        assert len(parent_rows) == 0
        assert len(result) == 2

    def test_uc_solitaria_com_agrupamento_marcada(self, sample_base_xlsx, sample_template_xlsx):
        """UC solitária com 'Agrupamento' deve ser marcada como parent (a base já traz o valor certo)."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        filtered = orch.reader.filter_data(["Cliente Delta"], orch.get_available_periods())

        result = orch._apply_grouping(filtered)

        # Delta tem flag Agrupamento — deve ser marcada como parent
        parent_rows = result[result[PARENT_ROW_FLAG] == True]
        assert len(parent_rows) == 1
        assert len(result) == 1

    def test_misto_agrupamento_e_normal(self, sample_base_xlsx, sample_template_xlsx):
        """Quando temos clientes com e sem agrupamento, ambos presentes sem linhas extras."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        all_clients = orch.get_available_clients()
        all_periods = orch.get_available_periods()
        filtered = orch.reader.filter_data(all_clients, all_periods)

        result = orch._apply_grouping(filtered)

        # Nenhuma linha criada — total permanece igual
        assert len(result) == len(filtered)
        # 3 registros com Agrupamento (Gamma:2 + Delta:1)
        parent_rows = result[result[PARENT_ROW_FLAG] == True]
        assert len(parent_rows) == 3


class TestGenerateMultiple:
    """Testes de geração de múltiplos grupos (lote)."""

    def test_generate_multiple_zip_valido(self, sample_base_xlsx, sample_template_xlsx):
        """Deve retornar um ZIP com os arquivos esperados."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        periods = orch.get_available_periods()

        groups = [
            {"name": "Grupo_Alpha", "clients": ["Cliente Alpha"], "periods": periods},
            {"name": "Grupo_Beta", "clients": ["Cliente Beta"], "periods": periods},
        ]

        result = orch.generate_multiple(groups)

        assert result is not None

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            names = zf.namelist()
            assert "Grupo_Alpha.xlsx" in names
            assert "Grupo_Beta.xlsx" in names
            assert len(names) == 2

    def test_generate_multiple_ignora_grupo_vazio(self, sample_base_xlsx, sample_template_xlsx):
        """Grupos sem clientes ou períodos devem ser ignorados."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        periods = orch.get_available_periods()

        groups = [
            {"name": "Grupo_Valido", "clients": ["Cliente Alpha"], "periods": periods},
            {"name": "Grupo_Vazio", "clients": [], "periods": []},
        ]

        result = orch.generate_multiple(groups)

        assert result is not None
        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            assert len(zf.namelist()) == 1

    def test_generate_multiple_retorna_none_todos_vazios(self, sample_base_xlsx, sample_template_xlsx):
        """Se todos os grupos forem vazios, deve retornar None."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)

        groups = [
            {"name": "Grupo1", "clients": ["Fantasma"], "periods": ["99/9999"]},
        ]

        result = orch.generate_multiple(groups)
        assert result is None
