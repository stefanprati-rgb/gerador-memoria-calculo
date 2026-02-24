from src.adapters.excel_adapter import BaseExcelReader, TemplateExcelWriter
from src.core.mapping import COLUMN_MAPPING
import pandas as pd
from typing import Any, List, Optional

class Orchestrator:
    """Serviço central para orquestrar a geração de planilhas."""
    
    def __init__(self, base_file: Any, template_file: Any):
        self.reader = BaseExcelReader(base_file)
        self.template_file = template_file # Pode ser buffer do streamlit
        
    def get_available_clients(self) -> List[str]:
        return self.reader.get_clients()
        
    def get_available_periods(self) -> List[str]:
        return self.reader.get_periods()
        
    def generate(self, selected_clients: List[str], selected_period: str) -> Optional[bytes]:
        """
        Filtra a base e gera o arquivo Excel com os dados mapeados.
        """
        filtered_df = self.reader.filter_data(selected_clients, selected_period)
        
        if filtered_df.empty:
            return None
            
        writer = TemplateExcelWriter(self.template_file)
        excel_bytes = writer.generate_bytes(filtered_df, COLUMN_MAPPING)
        
        return excel_bytes
