from logic.adapters.excel_adapter import BaseExcelReader, TemplateExcelWriter
from logic.core.mapping import COLUMN_MAPPING
import pandas as pd
from typing import Any, List, Optional, Dict

import logging

logger = logging.getLogger(__name__)


class Orchestrator:
    """Serviço central para orquestrar a geração de planilhas."""
    
    def __init__(self, base_file: Any, template_file: Any):
        self.reader = BaseExcelReader(base_file)
        self.template_file = template_file
        logger.info("Orchestrator inicializado. Base: %s | Template: %s", base_file, template_file)
        
    def get_available_clients(self) -> List[str]:
        return self.reader.get_clients()
        
    def get_available_periods(self) -> List[str]:
        return self.reader.get_periods()
        
    def generate(self, selected_clients: List[str], selected_periods: List[str]) -> Optional[bytes]:
        """
        Filtra a base e gera o arquivo Excel com os dados mapeados.
        """
        logger.info("Gerando planilha para %d clientes, %d períodos.", len(selected_clients), len(selected_periods))
        
        filtered_df = self.reader.filter_data(selected_clients, selected_periods)
        
        if filtered_df.empty:
            logger.warning("Nenhum dado encontrado após aplicar os filtros.")
            return None
            
        writer = TemplateExcelWriter(self.template_file)
        excel_bytes = writer.generate_bytes(filtered_df, COLUMN_MAPPING)
        
        logger.info("Planilha gerada com sucesso (%d bytes).", len(excel_bytes))
        return excel_bytes

    def generate_multiple(self, groups: List[Dict[str, Any]]) -> Optional[bytes]:
        """
        Recebe uma lista de dicionários com chaves 'name', 'clients' (List[str]), e 'periods' (List[str]).
        Retorna um arquivo ZIP em bytes contendo todos os arquivos Excel gerados.
        Retorna None se nenhum arquivo puder ser gerado.
        """
        import zipfile
        import io
        
        logger.info("Gerando lote com %d grupos.", len(groups))
        
        zip_buffer = io.BytesIO()
        generated_count = 0
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for group in groups:
                group_name = group.get('name', 'Sem_Nome')
                clients = group.get('clients', [])
                periods = group.get('periods', [])
                
                if not clients or not periods:
                    logger.warning("Grupo '%s' ignorado: sem clientes ou períodos.", group_name)
                    continue
                    
                excel_bytes = self.generate(clients, periods)
                if excel_bytes:
                    filename = group_name if group_name.endswith(".xlsx") else f"{group_name}.xlsx"
                    zip_file.writestr(filename, excel_bytes)
                    generated_count += 1
                    
        if generated_count == 0:
            logger.warning("Nenhum arquivo gerado no lote.")
            return None
        
        logger.info("Lote finalizado: %d arquivos gerados.", generated_count)
        return zip_buffer.getvalue()
