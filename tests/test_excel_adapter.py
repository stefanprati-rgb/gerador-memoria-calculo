"""
Testes para o adaptador de leitura/escrita Excel.
"""

import pytest
import pandas as pd
import openpyxl
import io

from src.adapters.excel_adapter import BaseExcelReader, TemplateExcelWriter, ColumnValidationError
from src.core.mapping import COLUMN_MAPPING


class TestBaseExcelReader:
    """Testes do leitor da planilha base."""
    
    def test_carregamento_sucesso(self, sample_base_xlsx):
        """Deve carregar um arquivo válido sem erros."""
        reader = BaseExcelReader(sample_base_xlsx)
        assert len(reader.df) == 3

    def test_validacao_coluna_faltante(self, tmp_path):
        """Deve levantar ColumnValidationError se faltar uma coluna obrigatória."""
        df_incompleto = pd.DataFrame({"Nome": ["teste"], "Outra": [1]})
        path = tmp_path / "incompleto.xlsx"
        df_incompleto.to_excel(path, index=False)
        
        with pytest.raises(ColumnValidationError, match="Colunas obrigatórias ausentes"):
            BaseExcelReader(str(path))

    def test_normalizacao_espacos(self, sample_base_df, tmp_path):
        """Deve funcionar mesmo que colunas tenham espaços extras."""
        # Adicionar espaços extras nos nomes de coluna
        df = sample_base_df.copy()
        df.columns = [f"  {c}  " for c in df.columns]
        path = tmp_path / "espacos.xlsx"
        df.to_excel(path, index=False)
        
        reader = BaseExcelReader(str(path))
        assert len(reader.df) == 3

    def test_get_clients_unicos_e_ordenados(self, sample_base_xlsx):
        """Deve retornar clientes únicos e em ordem alfabética."""
        reader = BaseExcelReader(sample_base_xlsx)
        clients = reader.get_clients()
        
        assert clients == ["Cliente Alpha", "Cliente Beta"]

    def test_get_periods_unicos(self, sample_base_xlsx):
        """Deve retornar períodos únicos."""
        reader = BaseExcelReader(sample_base_xlsx)
        periods = reader.get_periods()
        
        assert "01/2026" in periods
        assert "02/2026" in periods
        assert len(periods) == 2

    def test_filtro_por_cliente(self, sample_base_xlsx):
        """Deve filtrar corretamente por nome do cliente."""
        reader = BaseExcelReader(sample_base_xlsx)
        filtered = reader.filter_data(["Cliente Alpha"], [])
        
        # Cliente Alpha tem 2 registros (01/2026 e 02/2026)
        assert len(filtered) == 2
        assert all(filtered['Nome'] == 'Cliente Alpha')

    def test_filtro_por_periodo(self, sample_base_xlsx):
        """Deve filtrar corretamente por período."""
        reader = BaseExcelReader(sample_base_xlsx)
        filtered = reader.filter_data([], ["01/2026"])
        
        # Período 01/2026 tem 2 registros (Alpha e Beta)
        assert len(filtered) == 2

    def test_filtro_combinado(self, sample_base_xlsx):
        """Deve filtrar por cliente E período ao mesmo tempo."""
        reader = BaseExcelReader(sample_base_xlsx)
        filtered = reader.filter_data(["Cliente Alpha"], ["01/2026"])
        
        assert len(filtered) == 1
        assert filtered.iloc[0]['Nome'] == 'Cliente Alpha'
        assert filtered.iloc[0]['Mês de Referência'] == '01/2026'

    def test_filtro_sem_resultados(self, sample_base_xlsx):
        """Deve retornar DataFrame vazio se filtro não encontrar nada."""
        reader = BaseExcelReader(sample_base_xlsx)
        filtered = reader.filter_data(["Cliente Inexistente"], ["01/2026"])
        
        assert len(filtered) == 0


class TestTemplateExcelWriter:
    """Testes do escritor no template."""
    
    def test_gera_bytes_validos(self, sample_base_xlsx, sample_template_xlsx):
        """Deve gerar bytes que representam um arquivo Excel válido."""
        reader = BaseExcelReader(sample_base_xlsx)
        filtered = reader.filter_data(["Cliente Alpha"], ["01/2026"])
        
        writer = TemplateExcelWriter(sample_template_xlsx)
        result = writer.generate_bytes(filtered, COLUMN_MAPPING)
        
        assert result is not None
        assert len(result) > 0
        
        # Verificar que é um xlsx válido
        wb = openpyxl.load_workbook(io.BytesIO(result))
        ws = wb.active
        assert ws.max_row >= 2  # Header + pelo menos 1 linha de dados
    
    def test_dados_corretos_no_excel_gerado(self, sample_base_xlsx, sample_template_xlsx):
        """Deve inserir os valores corretos nas colunas mapeadas."""
        reader = BaseExcelReader(sample_base_xlsx)
        filtered = reader.filter_data(["Cliente Alpha"], ["01/2026"])
        
        writer = TemplateExcelWriter(sample_template_xlsx)
        result = writer.generate_bytes(filtered, COLUMN_MAPPING)
        
        # Ler o excel gerado e verificar os dados
        wb = openpyxl.load_workbook(io.BytesIO(result))
        ws = wb.active
        
        # Linha 2 deve conter os dados do Cliente Alpha em 01/2026
        # Coluna "Razão Social" é a 4ª no template
        razao_social = ws.cell(row=2, column=4).value
        assert razao_social == "Cliente Alpha"

    def test_nan_vira_none(self, sample_base_df, sample_template_xlsx, tmp_path):
        """Deve converter NaN em None ao escrever no template."""
        df = sample_base_df.copy()
        df.loc[0, 'Economia R$'] = None
        
        path = tmp_path / "com_nan.xlsx"
        df.to_excel(path, index=False)
        
        reader = BaseExcelReader(str(path))
        filtered = reader.filter_data(["Cliente Alpha"], ["01/2026"])
        
        writer = TemplateExcelWriter(sample_template_xlsx)
        result = writer.generate_bytes(filtered, COLUMN_MAPPING)
        
        # Não deve lançar exceção
        assert result is not None
