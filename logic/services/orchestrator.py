"""
Serviço de orquestração para geração de planilhas de Memória de Cálculo.
Suporta faturamento agrupado (Fatura Pai + UCs Filhas).
"""
from logic.adapters.excel_adapter import BaseExcelReader, TemplateExcelWriter
from logic.core.mapping import (
    COLUMN_MAPPING,
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

    def check_incomplete_rows(self, selected_clients: List[str], selected_periods: List[str]) -> Dict[str, Any]:
        """
        Identifica registros que não possuem Vencimento (não encontrados na Gestão).
        Retorna dicionário com estatísticas e lista de UCs afetadas.
        """
        df = self.reader.filter_data(selected_clients, selected_periods)
        if df.empty:
            return {"total_registros": 0, "registros_incompletos": 0, "ucs_afetadas": []}
            
        # Vencimento é a coluna chave para identificar falta de match com a gestão
        if "Vencimento" not in df.columns:
            # Se não houve enriquecimento da gestão, assumimos que não há o que marcar como incompleto
            # (ou tratamos como tudo potencialmente incompleto, mas 0 é mais seguro para a UI)
            return {"total_registros": len(df), "registros_incompletos": 0, "ucs_afetadas": []}
            
        mask_incomplete = self._incomplete_mask(df)
        incomplete_df = df[mask_incomplete]
        
        ucs_afetadas = []
        for _, row in incomplete_df.iterrows():
            ucs_afetadas.append({
                "no_uc": str(row["No. UC"]),
                "referencia": str(row["Referencia"]),
                "razao_social": str(row["Razao Social"])
            })
            
        return {
            "total_registros": len(df),
            "registros_incompletos": len(incomplete_df),
            "ucs_afetadas": ucs_afetadas
        }

    def _apply_grouping(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica a lógica de agrupamento de faturas.
        
        Quando há UCs com Excecao Fat. = 'Agrupamento', cria UMA LINHA PAI que consolida 
        (soma) as informações financeiras. A linha pai é colocada acima das linhas das UCs filhas.
        """
        if GROUPING_FLAG_COL not in df.columns:
            logger.info("Coluna '%s' não encontrada. Sem agrupamento.", GROUPING_FLAG_COL)
            df[PARENT_ROW_FLAG] = False
            return df

        # Garantir que a flag existe inicialmente como False nas filhas
        df = df.copy()
        df[PARENT_ROW_FLAG] = False

        if "Referencia" not in df.columns or CLIENT_COLUMN not in df.columns:
            logger.warning("Faltam colunas de agrupamento. Seguindo sem agregar faturas.")
            return df

        grouped_dfs = []
        parent_count = 0
        
        # Agrupar por Cliente, Período e Distribuidora
        keys = [CLIENT_COLUMN, "Referencia"]
        if "CPF/CNPJ" in df.columns: keys.append("CPF/CNPJ")
        if "Distribuidora" in df.columns: keys.append("Distribuidora")
        
        # Preencher NA nas chaves temporariamente para o groupby não dropar
        for k in keys:
            if k in df.columns:
                df[k] = df[k].fillna("N/A")

        for group_keys, group_df in df.groupby(keys, sort=False):
            # Verificar se ESSE GRUPO MERECE uma Fatura Pai:
            # - Tem alguma UC com "Agrupamento"?
            # - Tem mais de uma UC no grupo? (grupos de 1 não são agrupamentos reais)
            mask_parent = group_df[GROUPING_FLAG_COL].astype(str).str.strip() == GROUPING_FLAG_VALUE
            
            if mask_parent.any() and len(group_df) > 1:
                # CRIAR A FATURA PAI
                parent_row = group_df.iloc[0].copy()
                
                # Modificar identificação
                parent_row["No. UC"] = "Fatura Agrupada"
                parent_row[PARENT_ROW_FLAG] = True
                
                # Somar as colunas financeiras (min_count=1 garante que se tudo for NaN, fica NaN)
                for col in SUM_COLUMNS:
                    if col in group_df.columns:
                        parent_row[col] = pd.to_numeric(group_df[col], errors="coerce").sum(min_count=1)
                
                # Juntar a linha pai e as linhas filhas do grupo
                grouped_dfs.append(pd.DataFrame([parent_row]))
                grouped_dfs.append(group_df)
                parent_count += 1
            else:
                grouped_dfs.append(group_df)

        if grouped_dfs:
            df = pd.concat(grouped_dfs, ignore_index=True)

        logger.info("Agrupamento: %d faturas pai geradas. Total de linhas agora: %d.", parent_count, len(df))
        return df

    def _incomplete_mask(self, df: pd.DataFrame) -> pd.Series:
        """Retorna máscara booleana: True para linhas com Vencimento ausente."""
        if "Vencimento" not in df.columns:
            return pd.Series(False, index=df.index)
        return df["Vencimento"].isna() | (df["Vencimento"].astype(str).str.strip().str.lower().isin(["", "nan", "nat", "none"]))

    def generate(self, selected_clients: List[str], selected_periods: List[str], incomplete_filter: str = "all") -> Optional[bytes]:
        """
        Filtra a base, aplica agrupamento e gera o arquivo Excel com os dados mapeados.
        
        Args:
            incomplete_filter: 'all' (tudo), 'complete_only' (sem incompletos), 'incomplete_only' (só incompletos).
        """
        logger.info("Gerando planilha para %d clientes, %d períodos. Filtro: %s", len(selected_clients), len(selected_periods), incomplete_filter)

        filtered_df = self.reader.filter_data(selected_clients, selected_periods)

        if filtered_df.empty:
            logger.warning("Nenhum dado encontrado após aplicar os filtros.")
            return None

        # Filtrar por completude se solicitado
        if incomplete_filter == "complete_only":
            mask = self._incomplete_mask(filtered_df)
            filtered_df = filtered_df[~mask]
            logger.info("Filtro 'complete_only': %d linhas removidas por incompletude.", mask.sum())
        elif incomplete_filter == "incomplete_only":
            mask = self._incomplete_mask(filtered_df)
            filtered_df = filtered_df[mask]
            logger.info("Filtro 'incomplete_only': %d linhas incompletas mantidas.", mask.sum())

        if filtered_df.empty:
            logger.warning("Nenhum dado restante após filtro de completude.")
            return None

        # Fluxo de Layout Único (14 Colunas)
        processed_df = self._apply_grouping(filtered_df)
        
        # 1. Garantir que todas as colunas do mapping existam (defensivo)
        legacy_keys = list(COLUMN_MAPPING.keys())
        for col in legacy_keys:
            if col not in processed_df.columns:
                processed_df[col] = pd.NA
        
        # 2. Reordenar e restringir estritamente para as 14 colunas do mapping + flag interna
        # Isso garante que nenhuma coluna de enriquecimento ou controle vaze para o Excel final
        legacy_columns = list(COLUMN_MAPPING.keys())
        processed_df = processed_df.reindex(columns=legacy_columns + [PARENT_ROW_FLAG])
        
        # 3. O Mapping deve seguir EXATAMENTE a ordem de chaves do COLUMN_MAPPING (14 colunas)
        from collections import OrderedDict
        full_mapping = OrderedDict()
        for k in legacy_columns:
            full_mapping[k] = COLUMN_MAPPING[k]

        writer = TemplateExcelWriter(self.template_file)
        excel_bytes = writer.generate_bytes(processed_df, full_mapping)

        logger.info("Planilha gerada com sucesso (%d bytes).", len(excel_bytes))
        return excel_bytes

    def generate_multiple(self, groups: List[Dict[str, Any]], incomplete_filter: str = "all") -> Optional[bytes]:
        """
        Recebe uma lista de dicionários com chaves 'name', 'clients' (List[str]), e 'periods' (List[str]).
        Retorna um arquivo ZIP em bytes contendo todos os arquivos Excel gerados.
        Retorna None se nenhum arquivo puder ser gerado.
        """
        import zipfile
        import io

        logger.info("Gerando lote com %d grupos. Filtro: %s", len(groups), incomplete_filter)

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

                excel_bytes = self.generate(clients, periods, incomplete_filter=incomplete_filter)
                if excel_bytes:
                    filename = group_name if group_name.endswith(".xlsx") else f"{group_name}.xlsx"
                    zip_file.writestr(filename, excel_bytes)
                    generated_count += 1

        if generated_count == 0:
            logger.warning("Nenhum arquivo gerado no lote.")
            return None

        logger.info("Lote finalizado: %d arquivos gerados.", generated_count)
        return zip_buffer.getvalue()
