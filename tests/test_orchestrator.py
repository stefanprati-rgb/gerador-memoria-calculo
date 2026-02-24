"""
Testes para o serviço de orquestração.
"""

import pytest
import zipfile
import io

from logic.services.orchestrator import Orchestrator


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

    def test_get_available_periods(self, sample_base_xlsx, sample_template_xlsx):
        """Deve retornar a lista de períodos da base."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        periods = orch.get_available_periods()
        
        assert len(periods) == 2

    def test_generate_retorna_bytes(self, sample_base_xlsx, sample_template_xlsx):
        """Deve retornar bytes quando há dados para gerar."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        result = orch.generate(["Cliente Alpha"], ["01/2026"])
        
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_retorna_none_sem_dados(self, sample_base_xlsx, sample_template_xlsx):
        """Deve retornar None quando não há dados após filtragem."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        result = orch.generate(["Cliente Fantasma"], ["01/2026"])
        
        assert result is None

    def test_generate_multiple_zip_valido(self, sample_base_xlsx, sample_template_xlsx):
        """Deve retornar um ZIP com os arquivos esperados."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        
        groups = [
            {"name": "Grupo_Alpha", "clients": ["Cliente Alpha"], "periods": ["01/2026"]},
            {"name": "Grupo_Beta", "clients": ["Cliente Beta"], "periods": ["01/2026"]},
        ]
        
        result = orch.generate_multiple(groups)
        
        assert result is not None
        
        # Verificar conteúdo do ZIP
        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            names = zf.namelist()
            assert "Grupo_Alpha.xlsx" in names
            assert "Grupo_Beta.xlsx" in names
            assert len(names) == 2

    def test_generate_multiple_ignora_grupo_vazio(self, sample_base_xlsx, sample_template_xlsx):
        """Grupos sem clientes ou períodos devem ser ignorados."""
        orch = Orchestrator(sample_base_xlsx, sample_template_xlsx)
        
        groups = [
            {"name": "Grupo_Valido", "clients": ["Cliente Alpha"], "periods": ["01/2026"]},
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
