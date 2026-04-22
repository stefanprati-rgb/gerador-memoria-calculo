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
    HIERARCHY_KEY_COL,
    HIERARCHY_PARENT_COL,
    HIERARCHY_PARENT_VALUE,
    GROUPING_IBM_COL,
    PARENT_ROW_FLAG,
    CLIENT_COLUMN,
    CLASSIFICATION_SOURCE_COL,
    CLASSIFICATION_FATURA_VALUES,
    CLASSIFICATION_LABEL_FATURA,
    CLASSIFICATION_LABEL_REGRA,
    CLASSIFICATION_COL,
    ENRICHMENT_KEY,
    ACCOUNT_NUMBER_COL,
    SEPARATOR_ROW_FLAG,
    CHILD_ROW_FLAG,
)
from logic.core.cleaning import enforce_payment_rules
import pandas as pd
from typing import Any, List, Optional, Dict

import logging

logger = logging.getLogger(__name__)

def _parse_br_number(value: Any, default: float | None = None) -> float | None:
    if pd.isna(value):
        return default
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if s in {"", "-", "--", " - "}:
        return default

    if "," in s:
        s = s.replace(".", "").replace(",", ".")

    try:
        return float(s)
    except ValueError:
        return default


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
                "no_uc": str(row[ENRICHMENT_KEY]),
                "referencia": str(row["Referencia"]),
                "razao_social": str(row["Razao Social"])
            })
            
        return {
            "total_registros": len(df),
            "registros_incompletos": len(incomplete_df),
            "ucs_afetadas": ucs_afetadas
        }

    def _apply_grouping(self, df: pd.DataFrame, group_by_distributor: bool = False) -> pd.DataFrame:
        """
        Aplica a lógica de agrupamento de faturas.
        
        Quando há UCs com Excecao Fat. = 'Agrupamento', cria UMA LINHA PAI que consolida 
        (soma) as informações financeiras. A linha pai é colocada acima das linhas das UCs filhas.
        
        Args:
            group_by_distributor: Se True, garante que o agrupamento considere a Distribuidora.
        """
        if GROUPING_FLAG_COL not in df.columns:
            logger.info("Coluna '%s' não encontrada. Sem agrupamento.", GROUPING_FLAG_COL)
            df[PARENT_ROW_FLAG] = False
            return df

        # Garantir que a flag existe inicialmente como False nas filhas
        df = df.copy()
        df[PARENT_ROW_FLAG] = False
        df[SEPARATOR_ROW_FLAG] = False
        
        if "Referencia" not in df.columns or CLIENT_COLUMN not in df.columns:
            logger.warning("Faltam colunas de agrupamento. Seguindo sem agregar faturas.")
            return df

        # Criar colunas temporárias normalizadas APENAS para o groupby
        _temp_cols = []
        for col in ["Distribuidora", "Referencia", CLIENT_COLUMN]:
            if col in df.columns:
                temp_name = f"_grp_{col}"
                df[temp_name] = df[col].astype(str).str.strip().str.upper().replace(["NAN", "NONE", ""], pd.NA)
                _temp_cols.append(temp_name)

        # Inicializar acumuladores para o processamento de grupos
        grouped_dfs = []
        parent_count = 0

        # Determinar a base das chaves de agrupamento usando as colunas temporárias
        if group_by_distributor:
            logger.info("Agrupamento por Distribuidora ativado: base ['_grp_Referencia', '_grp_Distribuidora'].")
            if "_grp_Distribuidora" in df.columns:
                keys = ["_grp_Referencia", "_grp_Distribuidora"]
            else:
                logger.warning("Agrupamento por Distribuidora solicitado mas coluna não encontrada. Usando _grp_Cliente.")
                keys = ["_grp_Referencia", f"_grp_{CLIENT_COLUMN}"]
        else:
            # Comportamento padrão: Agrupar considerando Referência e Razão Social (normalizados)
            keys = ["_grp_Referencia", f"_grp_{CLIENT_COLUMN}"]
        
        # Sanitização de tipos para chaves de identificação (UCs, IBM e Contas)
        # Nesses casos a conversão para string é necessária para consistência do de-para
        for col in [ENRICHMENT_KEY, HIERARCHY_KEY_COL, GROUPING_IBM_COL, ACCOUNT_NUMBER_COL]:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(r"\.0$", "", regex=True)
                    .str.strip()
                    .replace(["nan", "None", ""], pd.NA)
                )

        # Determinar chaves adicionais de hierarquia (IBM -> Hierarchy -> No. UC)
        if not group_by_distributor:
            if GROUPING_IBM_COL in df.columns and not df[GROUPING_IBM_COL].isna().all():
                df["group_key"] = df[GROUPING_IBM_COL].fillna(df[HIERARCHY_KEY_COL].fillna(df[ENRICHMENT_KEY]))
                keys.append("group_key")
            elif HIERARCHY_KEY_COL in df.columns:
                df[HIERARCHY_KEY_COL] = df[HIERARCHY_KEY_COL].fillna(df[ENRICHMENT_KEY])
                keys.append(HIERARCHY_KEY_COL)
            else:
                logger.info("Aplicando chave dinâmica para respeitar Excecao Fat.")
                df["dynamic_key"] = df[ENRICHMENT_KEY].copy()
                if GROUPING_FLAG_COL in df.columns:
                    mask = df[GROUPING_FLAG_COL].astype(str).str.strip() == GROUPING_FLAG_VALUE
                    df.loc[mask, "dynamic_key"] = "AGRUPADO"
                keys.append("dynamic_key")
        
        # Preencher NA nas chaves temporariamente para o groupby não dropar
        for k in keys:
            if k in df.columns:
                df[k] = df[k].fillna("N/A")

        for group_keys, group_df in df.groupby(keys, sort=False):
            # Verificar se ESSE GRUPO MERECE uma Fatura Pai:
            # - Tem alguma UC com Excecao Fat. = "Agrupamento"?
            # - OU tem alguma UC que é explicitamente Main?
            # - Tem mais de uma UC no grupo?
            mask_agrup = group_df[GROUPING_FLAG_COL].astype(str).str.strip() == GROUPING_FLAG_VALUE
            mask_main = pd.Series(False, index=group_df.index)
            if HIERARCHY_PARENT_COL in group_df.columns:
                mask_main = group_df[HIERARCHY_PARENT_COL].astype(str).str.strip().str.upper() == HIERARCHY_PARENT_VALUE
            
            is_group = (mask_agrup.any() or mask_main.any() or group_by_distributor) and len(group_df) > 1
            
            if is_group:
                # CRIAR A FATURA PAI
                parent_row = group_df.iloc[0].copy()
                
                # Modificar identificação
                parent_row[ENRICHMENT_KEY] = "Fatura Agrupada"
                parent_row[PARENT_ROW_FLAG] = True
                
                parent_row[CHILD_ROW_FLAG] = False
                
                # Somar as colunas financeiras (min_count=1 garante que se tudo for NaN, fica NaN)
                for col in SUM_COLUMNS:
                    if col in group_df.columns:
                        series_clean = group_df[col].apply(lambda v: _parse_br_number(v, default=0.0))
                        parent_row[col] = pd.to_numeric(series_clean, errors="coerce").sum(min_count=1)
                
                # Juntar a linha pai e as linhas filhas do grupo (Preserva a integridade: Pai + Filhas)
                grouped_dfs.append(pd.DataFrame([parent_row]))
                child_df = group_df.copy()
                child_df[CHILD_ROW_FLAG] = True
                grouped_dfs.append(child_df)
                parent_count += 1
            else:
                normal_df = group_df.copy()
                normal_df[CHILD_ROW_FLAG] = False
                grouped_dfs.append(normal_df)
            
            # Adicionar Linha Separadora (Fantasma) em branco após o grupo
            # Criamos uma linha com todas as colunas vazias, exceto o flag SEPARATOR_ROW_FLAG
            separator_row = pd.DataFrame([{SEPARATOR_ROW_FLAG: True}])
            grouped_dfs.append(separator_row)

        if grouped_dfs:
            df = pd.concat(grouped_dfs, ignore_index=True)

        # DROPAR COLUNAS TEMPORÁRIAS E CHAVES DINÂMICAS
        df.drop(columns=[c for c in _temp_cols if c in df.columns], inplace=True, errors='ignore')
        df.drop(columns=["group_key", "dynamic_key"], inplace=True, errors='ignore')

        logger.info("Agrupamento: %d faturas pai geradas. Total de linhas agora: %d.", parent_count, len(df))
        return df


    def _incomplete_mask(self, df: pd.DataFrame) -> pd.Series:
        """Retorna máscara booleana: True para linhas com Vencimento ausente."""
        if "Vencimento" not in df.columns:
            return pd.Series(False, index=df.index)
        return df["Vencimento"].isna() | (df["Vencimento"].astype(str).str.strip().str.lower().isin(["", "nan", "nat", "none"]))

    def _apply_classification(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Deriva a coluna de classificação com base em CLASSIFICATION_SOURCE_COL ('Fonte dos Dados').

        Regras:
          - 'Fatura' → CLASSIFICATION_LABEL_FATURA  (leitura real / PDF)
          - Qualquer outro valor → CLASSIFICATION_LABEL_REGRA  (estimativa/contrato/demonstrativo)
          - Linha 'Fatura Pai' (agrupada) → rótulo mais frequente entre as filhas do grupo;
            desempate a favor de CLASSIFICATION_LABEL_REGRA.
          - Coluna ausente na base → preenche com CLASSIFICATION_LABEL_REGRA.
        """
        df = df.copy()

        if CLASSIFICATION_SOURCE_COL not in df.columns:
            logger.warning(
                "Coluna '%s' não encontrada na base. Classificação preenchida como '%s' para todas as linhas.",
                CLASSIFICATION_SOURCE_COL, CLASSIFICATION_LABEL_REGRA,
            )
            df[CLASSIFICATION_COL] = CLASSIFICATION_LABEL_REGRA
            return df

        def _classify(val):
            if pd.isna(val):
                return CLASSIFICATION_LABEL_REGRA
            return CLASSIFICATION_LABEL_FATURA if str(val).strip() in CLASSIFICATION_FATURA_VALUES else CLASSIFICATION_LABEL_REGRA

        df[CLASSIFICATION_COL] = df[CLASSIFICATION_SOURCE_COL].apply(_classify)

        # Corrigir linhas Pai: usar o rótulo mais comum entre as filhas do mesmo grupo
        parent_mask = df.get(PARENT_ROW_FLAG, pd.Series(False, index=df.index)).astype(bool)
        if parent_mask.any() and CLASSIFICATION_COL in df.columns:
            # Para cada linha pai, pegar o índice imediatamente posterior (as filhas virão depois)
            # Como as filhas ficam logo após o pai no DataFrame, usamos um range simples.
            parent_indices = df.index[parent_mask].tolist()
            for pi in parent_indices:
                loc = df.index.get_loc(pi)
                after = df.iloc[loc + 1:]
                
                stop_mask = (
                    after.get(PARENT_ROW_FLAG, pd.Series(False, index=after.index)).astype(bool)
                    | after.get(SEPARATOR_ROW_FLAG, pd.Series(False, index=after.index)).astype(bool)
                )
                
                stop_positions = stop_mask[stop_mask].index
                end_loc = df.index.get_loc(stop_positions[0]) if len(stop_positions) > 0 else len(df)
                
                child_labels = df.iloc[loc + 1:end_loc][CLASSIFICATION_COL]
                if not child_labels.empty:
                    counts = child_labels.value_counts()
                    majority_label = counts.index[0] if counts.iloc[0] > counts.sum() / 2 else CLASSIFICATION_LABEL_REGRA
                    df.at[pi, CLASSIFICATION_COL] = majority_label

        logger.info(
            "Classificação aplicada: %d 'Fatura' / %d 'Regra de Negócio'.",
            (df[CLASSIFICATION_COL] == CLASSIFICATION_LABEL_FATURA).sum(),
            (df[CLASSIFICATION_COL] == CLASSIFICATION_LABEL_REGRA).sum(),
        )
        return df

    def generate(self, selected_clients: List[str], selected_periods: List[str], incomplete_filter: str = "all", group_by_distributor: bool = False, enrichment_df: pd.DataFrame = None, somente_pendencias: bool = False, tipo_apresentacao: str = "Tabela Única", incluir_resumo: bool = False, separar_auditoria: bool = False) -> Optional[bytes]:
        """
        Filtra a base, aplica agrupamento e gera o arquivo Excel com os dados mapeados.
        
        Args:
            incomplete_filter: 'all' (tudo), 'complete_only' (sem incompletos), 'incomplete_only' (só incompletos).
            group_by_distributor: Se True, aplica a regra de agrupamento por Distribuidora.
            enrichment_df: DataFrame extra para enriquecer os dados base via merge por 'No. UC'.
        """
        logger.info("Gerando planilha para %d clientes, %d períodos. Filtro: %s | Agrupar por Distribuidora: %s | Enriquecimento: %s", 
                    len(selected_clients), len(selected_periods), incomplete_filter, group_by_distributor, enrichment_df is not None)

        filtered_df = self.reader.filter_data(selected_clients, selected_periods)

        actual_enrichment_cols = []
        if enrichment_df is not None and not enrichment_df.empty:
            # Segurança: Evitar que UCs duplicadas no mapeamento multipliquem as linhas na planilha final
            clean_enrichment = enrichment_df.drop_duplicates(subset=[ENRICHMENT_KEY], keep='last')
            
            # Proteger contra colunas duplicadas: dropar do enriquecimento colunas já presentes na base
            # (exceto a chave de merge) para evitar _x/_y que quebram o agrupamento
            existing_cols = set(filtered_df.columns) - {ENRICHMENT_KEY}
            cols_to_drop = [c for c in clean_enrichment.columns if c in existing_cols]
            if cols_to_drop:
                logger.info("Removendo %d colunas duplicadas do enriquecimento: %s", len(cols_to_drop), cols_to_drop)
                clean_enrichment = clean_enrichment.drop(columns=cols_to_drop)
            
            actual_enrichment_cols = [c for c in clean_enrichment.columns if c != ENRICHMENT_KEY and c not in COLUMN_MAPPING]
            logger.info("Aplicando enriquecimento (left merge) em %d registros.", len(filtered_df))
            filtered_df = pd.merge(filtered_df, clean_enrichment, on=ENRICHMENT_KEY, how='left')
            logger.info("Enriquecimento de dados aplicado (%d novas colunas).", len(clean_enrichment.columns) - 1)

        if filtered_df.empty:
            logger.warning("Nenhum dado encontrado após aplicar os filtros.")
            return None

        # Filtrar por completude se solicitado
        if incomplete_filter == "complete_only":
            mask = self._incomplete_mask(filtered_df)
            filtered_df = filtered_df.loc[~mask].copy()
            logger.info("Filtro 'complete_only': %d linhas removidas por incompletude.", mask.sum())
        elif incomplete_filter == "incomplete_only":
            mask = self._incomplete_mask(filtered_df)
            filtered_df = filtered_df.loc[mask].copy()
            logger.info("Filtro 'incomplete_only': %d linhas incompletas mantidas.", mask.sum())

        if filtered_df.empty:
            logger.warning("Nenhum dado restante após filtro de completude.")
            return None

        # Ordenar ANTES do agrupamento por Economia Gerada descendente ("Ganho total Padrão")
        # Isso garante que a ordenação global preserve os blocos de agrupamento (Pai+Filhas ficam juntos).
        if "Ganho total Padrão" in filtered_df.columns:
            filtered_df["_temp_sort"] = filtered_df["Ganho total Padrão"].apply(_parse_br_number, default=0.0)
            filtered_df = filtered_df.sort_values(by="_temp_sort", ascending=False)
            filtered_df = filtered_df.drop(columns=["_temp_sort"])
            logger.info("Ordenação global por 'Economia Gerada' aplicada (antes do agrupamento).")


        # Fluxo de Layout Único (14 Colunas + Classificação)
        processed_df = self._apply_grouping(filtered_df, group_by_distributor=group_by_distributor)
        processed_df = self._apply_classification(processed_df)
        
        # 1. Garantir que todas as colunas do mapping existam (defensivo)
        from logic.core.mapping import ACCOUNT_NUMBER_COL
        legacy_keys = list(COLUMN_MAPPING.keys())
        for col in legacy_keys:
            if col not in processed_df.columns:
                if col == ACCOUNT_NUMBER_COL:
                    logger.warning("Coluna '%s' não encontrada na base consolidada. Verifique se o Sincronismo com a Gestão foi realizado.", col)
                processed_df[col] = pd.NA
        
        # 2. Identificar colunas extras vindas estritamente do enrichment_df
        extra_cols = [c for c in actual_enrichment_cols if c in processed_df.columns]
        
        # 3. Reordenar e incluir colunas extras no final do DataFrame
        final_columns = legacy_keys + extra_cols
        processed_df = processed_df.reindex(columns=final_columns + [PARENT_ROW_FLAG, SEPARATOR_ROW_FLAG])
        
        # 4. Construir o mapping completo (Orderly) preservando a ordem do Excel
        from collections import OrderedDict
        full_mapping = OrderedDict()
        for k in legacy_keys:
            full_mapping[k] = COLUMN_MAPPING[k]
        
        # Estender com as colunas novas do enriquecimento
        for k in extra_cols:
            full_mapping[k] = k

        # 5. Aplicar Regras Rigorosas de Pagamento (Saneamento de Dados)
        processed_df = enforce_payment_rules(processed_df)

        # 6. Quick Wins: Filtro de Pendências
        if somente_pendencias and "Status Pos-Faturamento" in processed_df.columns:
            # Filtra linhas onde o status seja "Pago"
            is_pago = processed_df["Status Pos-Faturamento"].astype(str).str.strip().str.lower() == "pago"
            processed_df = processed_df.loc[~is_pago].copy()
            logger.info("Filtro de pendências ativado: Removidas faturas com status 'Pago'. Linhas restantes: %d", len(processed_df))

        writer = TemplateExcelWriter(self.template_file)
        excel_bytes = writer.generate_bytes(processed_df, full_mapping, tipo_apresentacao=tipo_apresentacao, incluir_resumo=incluir_resumo, separar_auditoria=separar_auditoria)

        logger.info("Planilha gerada com sucesso (%d bytes).", len(excel_bytes))
        return excel_bytes

    def generate_multiple(self, groups: List[Dict[str, Any]], incomplete_filter: str = "all", group_by_distributor: bool = False, enrichment_df: pd.DataFrame = None, somente_pendencias: bool = False, tipo_apresentacao: str = "Tabela Única", incluir_resumo: bool = False, separar_auditoria: bool = False) -> Optional[bytes]:
        """
        Recebe uma lista de dicionários com chaves 'name', 'clients' (List[str]), e 'periods' (List[str]).
        Retorna um arquivo ZIP em bytes contendo todos os arquivos Excel gerados com suporte a enriquecimento.
        """
        import zipfile
        import io

        logger.info("Gerando lote com %d grupos. Filtro: %s | Agrupar por Distribuidora: %s", len(groups), incomplete_filter, group_by_distributor)

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

                excel_bytes = self.generate(
                    clients, 
                    periods, 
                    incomplete_filter=incomplete_filter, 
                    group_by_distributor=group_by_distributor,
                    enrichment_df=enrichment_df,
                    somente_pendencias=somente_pendencias,
                    tipo_apresentacao=tipo_apresentacao,
                    incluir_resumo=incluir_resumo,
                    separar_auditoria=separar_auditoria
                )
                if excel_bytes:
                    filename = group_name if group_name.endswith(".xlsx") else f"{group_name}.xlsx"
                    zip_file.writestr(filename, excel_bytes)
                    generated_count += 1

        if generated_count == 0:
            logger.warning("Nenhum arquivo gerado no lote.")
            return None

        logger.info("Lote finalizado: %d arquivos gerados.", generated_count)
        return zip_buffer.getvalue()

    def get_all_ucs_with_names(self) -> pd.DataFrame:
        """
        Retorna todas as UCs únicas e suas respectivas Razões Sociais da base carregada.
        Usado para configuração de enriquecimento de dados.
        """
        if self.reader.df.empty:
            return pd.DataFrame(columns=[ENRICHMENT_KEY, CLIENT_COLUMN])
            
        # Pegar apenas as colunas necessárias e remover duplicatas
        cols = [ENRICHMENT_KEY, CLIENT_COLUMN]
        for col in cols:
             if col not in self.reader.df.columns:
                  logger.warning("get_all_ucs_with_names: Coluna '%s' não encontrada.", col)
                  return pd.DataFrame(columns=cols)
                  
        return (
            self.reader.df[cols]
            .drop_duplicates()
            .sort_values(by=CLIENT_COLUMN)
        )
