"""
Serviço de orquestração para geração de planilhas de Memória de Cálculo.
Suporta faturamento agrupado (Fatura Pai + UCs Filhas).
"""
from logic.adapters.excel_adapter import BaseExcelReader, TemplateExcelWriter
from logic.core.mapping import (
    COLUMN_MAPPING,
    ENRICHMENT_MAPPING,
    GROUPING_FLAG_COL,
    GROUPING_FLAG_VALUE,
    GROUPING_KEYS,
    SUM_COLUMNS,
    PARENT_ROW_FLAG,
    CLIENT_COLUMN,
)
import pandas as pd
from typing import Any, List, Optional, Dict

import logging

logger = logging.getLogger(__name__)


class Orchestrator:
    """Serviço central para orquestrar a geração de planilhas com suporte a agrupamento."""

    def __init__(self, base_file: Any, template_file: Any, sheet_name: str = "Balanco Operacional"):
        self.reader = BaseExcelReader(base_file, sheet_name=sheet_name)
        self.template_file = template_file
        logger.info("Orchestrator inicializado. Base: %s | Template: %s", base_file, template_file)

    def get_available_clients(self) -> List[str]:
        return self.reader.get_clients()

    def get_available_periods(self) -> List[str]:
        return self.reader.get_periods()

    def count_filtered(self, selected_clients: List[str], selected_periods: List[str]) -> int:
        """Retorna a contagem de registros filtrados sem gerar o Excel."""
        filtered_df = self.reader.filter_data(selected_clients, selected_periods)
        return len(filtered_df)

    def _apply_grouping(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica a lógica de agrupamento de faturas.
        
        A base já contém as Faturas Pai como linhas com Excecao Fat. = 'Agrupamento'.
        Essas linhas já possuem os valores financeiros consolidados (Boleto, Ganho, etc.).
        
        Esta função apenas MARCA essas linhas com _is_parent=True para que o
        TemplateExcelWriter aplique formatação diferenciada (negrito + fundo amarelo).
        
        Nenhuma linha extra é criada e nenhum valor é alterado.
        """
        if GROUPING_FLAG_COL not in df.columns:
            logger.info("Coluna '%s' não encontrada. Sem agrupamento.", GROUPING_FLAG_COL)
            df[PARENT_ROW_FLAG] = False
            return df

        # Marcar linhas de Fatura Pai (Agrupamento) para destaque visual
        mask_parent = df[GROUPING_FLAG_COL].astype(str).str.strip() == GROUPING_FLAG_VALUE
        df = df.copy()
        df[PARENT_ROW_FLAG] = mask_parent

        parent_count = mask_parent.sum()
        logger.info(
            "Agrupamento: %d faturas pai identificadas de %d registros totais.",
            parent_count, len(df),
        )

        return df

    def generate(self, selected_clients: List[str], selected_periods: List[str]) -> Optional[bytes]:
        """
        Filtra a base, aplica agrupamento e gera o arquivo Excel com os dados mapeados.
        """
        logger.info("Gerando planilha para %d clientes, %d períodos.", len(selected_clients), len(selected_periods))

        filtered_df = self.reader.filter_data(selected_clients, selected_periods)

        if filtered_df.empty:
            logger.warning("Nenhum dado encontrado após aplicar os filtros.")
            return None

        # Aplicar lógica de agrupamento
        processed_df = self._apply_grouping(filtered_df)

        writer = TemplateExcelWriter(self.template_file)
        # Mesclar mapeamento obrigatório + colunas de enriquecimento que existirem no DF
        full_mapping = dict(COLUMN_MAPPING)
        for col, dest in ENRICHMENT_MAPPING.items():
            if col in processed_df.columns:
                full_mapping[col] = dest
        excel_bytes = writer.generate_bytes(processed_df, full_mapping)

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
