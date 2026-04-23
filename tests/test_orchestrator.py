"""
Testes para o serviço de orquestração com identificação de agrupamento.
"""

import pytest
import zipfile
import io
import pandas as pd

from logic.services.orchestrator import Orchestrator
from logic.core.mapping import (
    PARENT_ROW_FLAG,
    GROUPING_MODE_CNPJ,
    GROUPING_MODE_NONE,
)


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

        # Deve ter criado 2 linhas extras: 1 Fatura Pai + 1 Separador no final do grupo
        assert len(result) == 4
        
        # A primeira linha deve ser a Fatura Pai
        parent_row = result.iloc[0]
        assert parent_row[PARENT_ROW_FLAG] == True
        assert parent_row["No. UC"] == "Consolidado (Default)"
        
        # A soma de Valor Enviado Emissão deve ser a soma das duas filhas (200 + 180 = 380)
        assert parent_row["Valor Enviado Emissão"] == pytest.approx(380.00)
        
        # As linhas filhas devem vir depois e não ter a flag
        assert result.iloc[1][PARENT_ROW_FLAG] == False
        assert result.iloc[2][PARENT_ROW_FLAG] == False
        
        # A última linha deve ser o separador
        from logic.core.mapping import SEPARATOR_ROW_FLAG
        assert result.iloc[3][SEPARATOR_ROW_FLAG] == True

    def test_nao_marca_sem_flag(self, sample_base_xlsx, sample_template_xlsx):
        """Clientes sem Excecao Fat. = 'Agrupamento' não devem gerar Fatura Pai, mas ganham separador."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        filtered = orch.reader.filter_data(["Cliente Alpha"], orch.get_available_periods()) # 2 registros

        result = orch._apply_grouping(filtered)

        # Nenhuma Fatura Pai gerada
        parent_rows = result[result[PARENT_ROW_FLAG] == True]
        assert len(parent_rows) == 0
        # O total de linhas agora é dados + separadores (2 grupos de 1 UC cada)
        assert len(result) == len(filtered) + 2

    def test_uc_solitaria_com_agrupamento_marcada(self, sample_base_xlsx, sample_template_xlsx):
        """UC solitária com 'Agrupamento' NÃO deve gerar Fatura Pai, mas ganha separador."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        filtered = orch.reader.filter_data(["Cliente Delta"], orch.get_available_periods())

        result = orch._apply_grouping(filtered)

        parent_rows = result[result[PARENT_ROW_FLAG] == True]
        assert len(parent_rows) == 0
        assert len(result) == 2 # 1 UC original + 1 Separador

    def test_misto_agrupamento_e_normal(self, sample_base_xlsx, sample_template_xlsx):
        """Clientes com e sem agrupamento processados juntos. Grupos len=1 ignorados para Pai, mas ganham separador."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        all_clients = orch.get_available_clients()
        all_periods = orch.get_available_periods()
        filtered = orch.reader.filter_data(all_clients, all_periods)

        original_len = len(filtered) # 6 registros
        result = orch._apply_grouping(filtered)

        # Criou Fatura Pai APENAS para Gamma (1 grupo). 
        # Total de grupos: Alpha(2), Beta(1), Gamma(1), Delta(1) = 5 grupos
        parent_rows = result[result[PARENT_ROW_FLAG] == True]
        assert len(parent_rows) == 1
        assert len(result) == original_len + 1 + 5 # Dados + 1 Pai + 5 Separadores = 12 total

    def test_agrupamento_por_cnpj_cria_fatura_pai(self, sample_base_xlsx, sample_template_xlsx):
        """O modo por CNPJ deve agrupar registros do mesmo período/documento mesmo sem depender da regra padrão."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        filtered = orch.reader.filter_data(["Cliente Gamma"], orch.get_available_periods())

        result = orch._apply_grouping(filtered, grouping_mode=GROUPING_MODE_CNPJ)

        parent_rows = result[result[PARENT_ROW_FLAG] == True]
        assert len(parent_rows) == 1
        assert parent_rows.iloc[0]["Valor Enviado Emissão"] == pytest.approx(380.00)

    def test_sem_agrupamento_preserva_linhas_originais(self, sample_base_xlsx, sample_template_xlsx):
        """O modo sem agrupamento deve manter apenas as linhas originais, sem pai nem separador."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        filtered = orch.reader.filter_data(["Cliente Gamma"], orch.get_available_periods())

        result = orch._apply_grouping(filtered, grouping_mode=GROUPING_MODE_NONE)

        assert len(result) == len(filtered)
        assert result[PARENT_ROW_FLAG].sum() == 0

    def test_ocultar_ucs_filhas_mantem_apenas_linha_pai(self, sample_base_xlsx, sample_template_xlsx):
        """Quando a opção de filhas está desativada, o grupo mostra apenas a linha consolidada e o separador."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        filtered = orch.reader.filter_data(["Cliente Gamma"], orch.get_available_periods())

        result = orch._apply_grouping(filtered, include_child_rows=False)

        assert len(result) == 2
        assert result.iloc[0][PARENT_ROW_FLAG] == True


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

    def test_generate_multiple_nome_generico_vira_nome_inteligente(self, sample_base_xlsx, sample_template_xlsx):
        """Quando o grupo é genérico (Grupo_N), o arquivo no ZIP deve usar base do cliente e período."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)

        groups = [
            {"name": "Grupo_1", "clients": ["Cliente Alpha"], "periods": ["01/2026", "02/2026"]},
        ]

        result = orch.generate_multiple(groups)
        assert result is not None

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            names = zf.namelist()
            assert "Cliente_Alpha_jan_fev_2026.xlsx" in names


class TestIncompleteData:
    """Testes para identificação de faturas sem correspondência na gestão."""

    def test_check_incomplete_rows_detecta_ausentes(self, sample_base_xlsx, sample_template_xlsx, monkeypatch):
        """Deve detectar registros sem Vencimento (NaN)."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        
        # Injetar Vencimento como NaN no reader mockado para simular falta de match
        import logic.adapters.excel_adapter as adapters
        def mock_filter_data(*args, **kwargs):
            import pandas as pd
            df = pd.DataFrame({
                "No. UC": ["4003444738"],
                "Referencia": ["01/2026"],
                "Razao Social": ["Cliente Teste"],
                "Vencimento": [pd.NA], # Simula ausência na gestão
                "Status Pos-Faturamento": [pd.NA]
            })
            return df
        
        monkeypatch.setattr(orch.reader, "filter_data", mock_filter_data)
        
        info = orch.check_incomplete_rows(["Qualquer"], ["01/2026"])
        
        assert info["registros_incompletos"] == 1
        assert len(info["ucs_afetadas"]) == 1
        assert info["ucs_afetadas"][0]["no_uc"] == "4003444738"

    def test_check_incomplete_rows_retorna_vazio_quando_completo(self, sample_base_xlsx, sample_template_xlsx, monkeypatch):
        """Deve retornar zero incompletos quando todos têm Vencimento."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        
        def mock_filter_data(*args, **kwargs):
            import pandas as pd
            return pd.DataFrame({
                "No. UC": ["4003444738"],
                "Referencia": ["01/2026"],
                "Razao Social": ["Cliente Teste"],
                "Vencimento": ["10/02/2026"], # Completo
                "Status Pos-Faturamento": ["Pago"]
            })
        
        monkeypatch.setattr(orch.reader, "filter_data", mock_filter_data)
        
        info = orch.check_incomplete_rows(["Qualquer"], ["01/2026"])
        
        assert info["registros_incompletos"] == 0
        assert len(info["ucs_afetadas"]) == 0


class TestPortalOnlyGeneration:
    """Testes do filtro portal-first aplicado na geração."""

    def test_generate_mantem_apenas_portal_e_deduplica_uc_referencia(self, sample_base_xlsx, sample_template_xlsx, monkeypatch):
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)

        source_df = pd.DataFrame({
            "Referencia": ["01/2026", "01/2026", "01/2026", "01/2026", "01/2026"],
            "No. UC": ["UC001", "UC001", "UC002", "UC003", "UC004"],
            "Razao Social": ["Cliente X", "Cliente X", "Cliente X", "Cliente X", "Cliente X"],
            "Distribuidora": ["CEMIG", "CEMIG", "CEMIG", "CEMIG", "CEMIG"],
            "Fonte dos Dados": ["Regra de Negócio", "Fatura", "Fatura", "Fatura", "Fatura"],
            "Número da conta": [pd.NA, "CONTA-1", "CONTA-2", "CONTA-3", "CONTA-4"],
            "Valor Enviado Emissão": [10.0, 20.0, 30.0, 40.0, 50.0],
            "Valor_gestao": [111.0, 111.0, 222.0, pd.NA, 0.0],
            "Tarifa Raizen": [1.0, 1.0, 1.0, 1.0, 1.0],
            "Custo c/ GD": [1.0, 1.0, 1.0, 1.0, 1.0],
            "Custo s/ GD": [2.0, 2.0, 2.0, 2.0, 2.0],
            "Ganho total Padrão": [1.0, 1.0, 1.0, 1.0, 1.0],
            "CPF/CNPJ": ["1", "1", "1", "1", "1"],
            "Cred. Consumido Raizen": [1.0, 1.0, 1.0, 1.0, 1.0],
            "Desconto Contratado": ["10%", "10%", "10%", "10%", "10%"],
            "Vencimento": ["01-02-2026", "01-02-2026", "01-02-2026", "01-02-2026", "01-02-2026"],
            "Status Pos-Faturamento": ["Pago", "Pago", "Pago", "Pago", "Pago"],
        })

        monkeypatch.setattr(orch.reader, "filter_data", lambda *args, **kwargs: source_df.copy())

        captured = {}

        class _FakeWriter:
            def __init__(self, *_args, **_kwargs):
                pass

            def generate_bytes(self, data_to_insert, *_args, **_kwargs):
                captured["df"] = data_to_insert.copy()
                return b"xlsx-bytes"

        monkeypatch.setattr("logic.services.orchestrator.TemplateExcelWriter", _FakeWriter)

        result = orch.generate(["Cliente X"], ["01/2026"], grouping_mode="none")

        assert result == b"xlsx-bytes"
        generated_df = captured["df"]
        # UC003 não existe no portal (Valor_gestao nulo) e UC004 tem valor 0, então saem.
        assert set(generated_df["No. UC"].dropna().astype(str)) == {"UC001", "UC002"}
        # UC001 era duplicada e deve ser consolidada em uma linha.
        assert (generated_df["No. UC"].astype(str) == "UC001").sum() == 1
        # Valor final vem do portal (Valor_gestao), não do valor técnico.
        uc001 = generated_df.loc[generated_df["No. UC"].astype(str) == "UC001"].iloc[0]
        assert uc001["Valor Enviado Emissão"] == pytest.approx(111.0)

    def test_generate_usa_uc_rateio_quando_for_a_chave_do_portal(self, sample_base_xlsx, sample_template_xlsx, monkeypatch):
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)

        source_df = pd.DataFrame({
            "Referencia": ["11/2025", "11/2025"],
            "No. UC": ["TEC-A", "TEC-B"],
            "UC p Rateio": ["PORTAL-001", "PORTAL-002"],
            "Razao Social": ["Cliente Y", "Cliente Y"],
            "Distribuidora": ["CPFL", "CPFL"],
            "Fonte dos Dados": ["Fatura", "Fatura"],
            "Número da conta": ["C1", "C2"],
            "Valor Enviado Emissão": [10.0, 20.0],
            "Valor_gestao": [123.45, 456.78],
            "Tarifa Raizen": [1.0, 1.0],
            "Custo c/ GD": [1.0, 1.0],
            "Custo s/ GD": [2.0, 2.0],
            "Ganho total Padrão": [1.0, 1.0],
            "CPF/CNPJ": ["1", "1"],
            "Cred. Consumido Raizen": [1.0, 1.0],
            "Desconto Contratado": ["10%", "10%"],
            "Vencimento": ["01-12-2025", "01-12-2025"],
            "Status Pos-Faturamento": ["Pago", "Pago"],
        })

        monkeypatch.setattr(orch.reader, "filter_data", lambda *args, **kwargs: source_df.copy())

        captured = {}

        class _FakeWriter:
            def __init__(self, *_args, **_kwargs):
                pass

            def generate_bytes(self, data_to_insert, *_args, **_kwargs):
                captured["df"] = data_to_insert.copy()
                return b"xlsx-bytes"

        monkeypatch.setattr("logic.services.orchestrator.TemplateExcelWriter", _FakeWriter)

        result = orch.generate(["Cliente Y"], ["11/2025"], grouping_mode="none")

        assert result == b"xlsx-bytes"
        generated_df = captured["df"]
        assert set(generated_df["No. UC"].dropna().astype(str)) == {"PORTAL-001", "PORTAL-002"}

    def test_generate_usa_alias_alfanumerico_quando_uc_base_for_rateio(self, sample_base_xlsx, sample_template_xlsx, monkeypatch):
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)

        source_df = pd.DataFrame({
            "Referencia": ["11/2025", "11/2025", "02/2026"],
            "No. UC": ["631753726", "642599431", "W7008678589"],
            "UC p Rateio": [pd.NA, pd.NA, "631753726"],
            "Razao Social": ["Cliente Z", "Cliente Z", "Cliente Z"],
            "Distribuidora": ["CPFL", "CPFL", "CPFL"],
            "Fonte dos Dados": ["Fatura", "Fatura", "Contrato"],
            "Número da conta": ["A1", "A2", pd.NA],
            "Valor Enviado Emissão": [1.0, 1.0, 0.0],
            "Valor_gestao": [2687.26, 2162.90, 0.0],
            "Tarifa Raizen": [1.0, 1.0, 1.0],
            "Custo c/ GD": [1.0, 1.0, 1.0],
            "Custo s/ GD": [2.0, 2.0, 2.0],
            "Ganho total Padrão": [1.0, 1.0, 1.0],
            "CPF/CNPJ": ["1", "1", "1"],
            "Cred. Consumido Raizen": [1.0, 1.0, 1.0],
            "Desconto Contratado": ["10%", "10%", "10%"],
            "Vencimento": ["01-12-2025", "01-12-2025", pd.NA],
            "Status Pos-Faturamento": ["Pago", "Pago", pd.NA],
        })

        monkeypatch.setattr(orch.reader, "filter_data", lambda *args, **kwargs: source_df.copy())

        captured = {}

        class _FakeWriter:
            def __init__(self, *_args, **_kwargs):
                pass

            def generate_bytes(self, data_to_insert, *_args, **_kwargs):
                captured["df"] = data_to_insert.copy()
                return b"xlsx-bytes"

        monkeypatch.setattr("logic.services.orchestrator.TemplateExcelWriter", _FakeWriter)

        result = orch.generate(["Cliente Z"], ["11/2025"], grouping_mode="none")

        assert result == b"xlsx-bytes"
        generated_df = captured["df"]
        assert "W7008678589" in set(generated_df["No. UC"].dropna().astype(str))
