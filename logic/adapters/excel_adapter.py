import pandas as pd
from typing import List, Dict, Any
from logic.core.mapping import get_base_columns

import logging

logger = logging.getLogger(__name__)


class ColumnValidationError(Exception):
    """Erro levantado quando colunas obrigatórias não são encontradas na planilha base."""
    pass


class BaseExcelReader:
    """Adaptador para leitura da planilha gd_gestao_cobranca."""
    
    def __init__(self, file_path_or_buffer: Any):
        """Inicializa o leitor, carrega o DataFrame e valida as colunas. Suporta string(path) ou UploadedFile."""
        self.df = pd.read_excel(file_path_or_buffer)
        self._normalize_columns()
        self._validate_columns()
        logger.info("Base carregada com %d registros e %d colunas.", len(self.df), len(self.df.columns))

    def _normalize_columns(self):
        """Remove espaços extras dos nomes de colunas para evitar falhas por diferenças mínimas."""
        self.df.columns = self.df.columns.str.strip()
    
    def _validate_columns(self):
        """Valida se todas as colunas esperadas pelo mapeamento estão presentes na base."""
        expected = get_base_columns()
        missing = [c for c in expected if c not in self.df.columns]
        if missing:
            raise ColumnValidationError(
                f"Colunas obrigatórias ausentes na planilha base: {missing}. "
                f"Colunas encontradas: {list(self.df.columns)}"
            )
        
    def get_clients(self) -> List[str]:
        """Retorna lista de clientes (Nome) únicos na base, ordenados."""
        if 'Nome' not in self.df.columns:
            return []
        clients = self.df['Nome'].dropna().unique().tolist()
        return sorted([str(c) for c in clients])

    def get_periods(self) -> List[str]:
        """Retorna lista de períodos (Mês de Referência) únicos."""
        col = 'Mês de Referência'
        if col not in self.df.columns:
            return []
        periods = self.df[col].dropna().unique().tolist()
        return sorted([str(p) for p in periods])

    def filter_data(self, clients: List[str], periods: List[str]) -> pd.DataFrame:
        """Filtra o DataFrame pelos clientes e períodos especificados."""
        mask = pd.Series(True, index=self.df.index)
        
        if clients:
            mask = mask & (self.df['Nome'].isin(clients))
            
        if periods:
            mask = mask & (self.df['Mês de Referência'].isin(periods))
            
        filtered = self.df[mask].copy()
        logger.info("Filtro aplicado: %d clientes, %d períodos → %d registros.", len(clients), len(periods), len(filtered))
        return filtered


class TemplateExcelWriter:
    """Adaptador para escrever dados no template mc.xlsx."""
    
    def __init__(self, template_path_or_buffer: Any):
        self.template_source = template_path_or_buffer
        
    def generate_bytes(self, data_to_insert: pd.DataFrame, column_mapping: Dict[str, str]) -> bytes:
        """
        Lê o template, insere as linhas filtradas e retorna os bytes do Excel gerado.
        Normaliza os headers do template (strip) para garantir correspondência.
        """
        import io
        import openpyxl
        from copy import copy
        
        # Carregar o template
        wb = openpyxl.load_workbook(self.template_source)
        ws = wb.active
        
        # Encontrar os headers na linha 1, aplicando strip para normalizar
        header_row_idx = 1
        template_headers = {}
        for idx, cell in enumerate(ws[header_row_idx], 1):
            if cell.value:
                normalized = str(cell.value).strip()
                template_headers[normalized] = idx
        
        # Determinar a próxima linha vazia para inserir dados
        start_row = ws.max_row + 1
        
        # Se o template tem pouca coisa, começar na linha 2
        if start_row <= 2 and ws.cell(row=2, column=1).value is None:
            start_row = 2
            
        current_row = start_row
        
        for _, row in data_to_insert.iterrows():
            for base_col, template_col in column_mapping.items():
                # Normalizar o nome da coluna destino para match
                template_col_normalized = template_col.strip()
                
                if base_col in row and template_col_normalized in template_headers:
                    col_idx = template_headers[template_col_normalized]
                    val = row[base_col]
                    # Tratar NaNs
                    if pd.isna(val):
                        val = None
                    
                    new_cell = ws.cell(row=current_row, column=col_idx, value=val)
                    
                    # Copiar a formatação da linha 2 (referência do template) para as novas linhas
                    if current_row > 2:
                        ref_cell = ws.cell(row=2, column=col_idx)
                        if ref_cell.has_style:
                            new_cell.font = copy(ref_cell.font)
                            new_cell.border = copy(ref_cell.border)
                            new_cell.fill = copy(ref_cell.fill)
                            new_cell.number_format = copy(ref_cell.number_format)
                            new_cell.protection = copy(ref_cell.protection)
                            new_cell.alignment = copy(ref_cell.alignment)

            current_row += 1
        
        logger.info("Planilha gerada com %d linhas de dados.", current_row - start_row)
            
        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()
