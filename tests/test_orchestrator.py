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
    """Testes da geração da Fatura Pai (Agrupamento)."""

    def test_identifica_e_soma_fatura_pai(self, sample_base_xlsx, sample_template_xlsx):
        """Quando há UCs com 'Agrupamento', deve criar UMA Fatura Pai que soma os valores e colocar as UCs filhas embaixo."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        filtered = orch.reader.filter_data(["Cliente Gamma"], orch.get_available_periods())
        
        # Cliente Gamma tem 2 registros de Agrupamento
        assert len(filtered) == 2
        
        result = orch._apply_grouping(filtered)

        # Deve ter criado 1 linha extra (A Fatura Pai)
        assert len(result) == 3
        
        # A primeira linha deve ser a Fatura Pai
        parent_row = result.iloc[0]
        assert parent_row[PARENT_ROW_FLAG] == True
        assert parent_row["No. UC"] == "Fatura Agrupada"
        
        # A soma de Boleto Raizen deve ser a soma das duas filhas (200 + 180 = 380)
        assert parent_row["Boleto Raizen"] == pytest.approx(380.00)
        
        # As linhas filhas devem vir depois e não ter a flag
        assert result.iloc[1][PARENT_ROW_FLAG] == False
        assert result.iloc[2][PARENT_ROW_FLAG] == False

    def test_nao_marca_sem_flag(self, sample_base_xlsx, sample_template_xlsx):
        """Clientes sem Excecao Fat. = 'Agrupamento' não devem gerar Fatura Pai."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        filtered = orch.reader.filter_data(["Cliente Alpha"], orch.get_available_periods())

        result = orch._apply_grouping(filtered)

        # Nenhuma Fatura Pai gerada
        parent_rows = result[result[PARENT_ROW_FLAG] == True]
        assert len(parent_rows) == 0
        assert len(result) == len(filtered)  # O total de linhas permanece igual

    def test_uc_solitaria_com_agrupamento_marcada(self, sample_base_xlsx, sample_template_xlsx):
        """UC solitária com 'Agrupamento' NÃO deve gerar Fatura Pai (grupos exigem > 1 UC)."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        filtered = orch.reader.filter_data(["Cliente Delta"], orch.get_available_periods())

        result = orch._apply_grouping(filtered)

        parent_rows = result[result[PARENT_ROW_FLAG] == True]
        assert len(parent_rows) == 0  # Antes gerava 1, agora exige len > 1
        assert len(result) == 1 # Apenas a UC original

    def test_misto_agrupamento_e_normal(self, sample_base_xlsx, sample_template_xlsx):
        """Clientes com e sem agrupamento processados juntos. Grupos len=1 ignorados."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        all_clients = orch.get_available_clients()
        all_periods = orch.get_available_periods()
        filtered = orch.reader.filter_data(all_clients, all_periods)

        original_len = len(filtered) # 6
        result = orch._apply_grouping(filtered)

        # Criou Fatura Pai APENAS para Gamma (2 UCs). Delta tem 1 UC (ignorado).
        parent_rows = result[result[PARENT_ROW_FLAG] == True]
        assert len(parent_rows) == 1
        assert len(result) == original_len + 1

    def test_tarifa_raizen_negativa_vira_zero(self, sample_base_xlsx, sample_template_xlsx):
        """Valores negativos na Tarifa Raizen devem ser convertidos para 0.00."""
        import pandas as pd
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        
        # Criar um DF de teste com Tarifa Raizen negativa
        df_test = pd.DataFrame({
            "No. UC": ["UC1", "UC2"],
            "Referencia": ["01/2026", "01/2026"],
            "Razao Social": ["Test", "Test"],
            "Tarifa Raizen": [-10.0, 5.0],      # Soma = -5.0
            "Excecao Fat.": ["Agrupamento", "Agrupamento"],
            PARENT_ROW_FLAG: [False, False]
        })
        
        result = orch._apply_grouping(df_test)
        parent_row = result[result[PARENT_ROW_FLAG] == True].iloc[0]
        
        # A soma -5.0 deve ter sido convertida para 0.0
        assert parent_row["Tarifa Raizen"] == 0.0


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
