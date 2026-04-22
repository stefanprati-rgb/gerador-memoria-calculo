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
    GROUPING_MODE_DEFAULT,
    GROUPING_MODE_DISTRIBUTOR,
    GROUPING_MODE_CNPJ,
    GROUPING_MODE_NONE,
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


def _normalize_uc_text(value: Any) -> Optional[str]:
    if pd.isna(value):
        return pd.NA

    s = str(value).strip()
    if s.lower() in {"", "nan", "none"}:
        return pd.NA

    # Remove sufixo decimal comum vindo de planilhas numéricas (ex.: 12345.0)
    if s.endswith(".0"):
        s = s[:-2]

    return s


def _contains_letter(value: Any) -> bool:
    if pd.isna(value):
        return False
    return any(ch.isalpha() for ch in str(value))


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

    def _apply_grouping(
        self,
        df: pd.DataFrame,
        grouping_mode: str = GROUPING_MODE_DEFAULT,
        include_child_rows: bool = True,
        group_by_distributor: bool = False,
    ) -> pd.DataFrame:
        """
        Aplica a lógica de agrupamento de faturas.
        """
        if grouping_mode == GROUPING_MODE_DEFAULT and group_by_distributor:
            grouping_mode = GROUPING_MODE_DISTRIBUTOR

        # Garantir flags básicas
        df = df.copy()
        df[PARENT_ROW_FLAG] = False
        df[CHILD_ROW_FLAG] = False
        df[SEPARATOR_ROW_FLAG] = False

        if grouping_mode == GROUPING_MODE_NONE:
            logger.info("Modo 'Sem agrupamento' ativado.")
            if not include_child_rows and HIERARCHY_PARENT_COL in df.columns:
                 is_main = df[HIERARCHY_PARENT_COL].astype(str).str.strip().str.upper() == HIERARCHY_PARENT_VALUE
                 df = df[is_main].copy()
            return df

        if "Referencia" not in df.columns or CLIENT_COLUMN not in df.columns:
            logger.warning("Faltam colunas essenciais de agrupamento. Seguindo flat.")
            return df

        # Criar colunas temporárias normalizadas para o groupby
        _temp_cols = []
        for col in ["Distribuidora", "Referencia", "CPF/CNPJ", CLIENT_COLUMN]:
            if col in df.columns:
                temp_name = f"_grp_{col}"
                df[temp_name] = df[col].astype(str).str.strip().str.upper().replace(["NAN", "NONE", ""], pd.NA)
                _temp_cols.append(temp_name)

        # Determinar chaves de base
        if grouping_mode == GROUPING_MODE_DISTRIBUTOR:
            keys = ["_grp_Referencia", "_grp_Distribuidora"] if "_grp_Distribuidora" in df.columns else ["_grp_Referencia", f"_grp_{CLIENT_COLUMN}"]
        elif grouping_mode == GROUPING_MODE_CNPJ:
            keys = ["_grp_Referencia", "_grp_CPF/CNPJ"] if "_grp_CPF/CNPJ" in df.columns else ["_grp_Referencia", f"_grp_{CLIENT_COLUMN}"]
        else:
            keys = ["_grp_Referencia", f"_grp_{CLIENT_COLUMN}"]
            if GROUPING_IBM_COL in df.columns and not df[GROUPING_IBM_COL].isna().all():
                df["group_key"] = df[GROUPING_IBM_COL].fillna(df[HIERARCHY_KEY_COL].fillna(df[ENRICHMENT_KEY]))
                keys.append("group_key")
            elif HIERARCHY_KEY_COL in df.columns:
                df[HIERARCHY_KEY_COL] = df[HIERARCHY_KEY_COL].fillna(df[ENRICHMENT_KEY])
                keys.append(HIERARCHY_KEY_COL)
            else:
                df["dynamic_key"] = df[ENRICHMENT_KEY].copy()
                if GROUPING_FLAG_COL in df.columns:
                    mask = df[GROUPING_FLAG_COL].astype(str).str.strip() == GROUPING_FLAG_VALUE
                    df.loc[mask, "dynamic_key"] = "AGRUPADO"
                keys.append("dynamic_key")

        # Sanitização de tipos para chaves de identificação (UCs, IBM e Contas)
        for col in [ENRICHMENT_KEY, HIERARCHY_KEY_COL, GROUPING_IBM_COL, ACCOUNT_NUMBER_COL]:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(r"\.0$", "", regex=True)
                    .str.strip()
                    .replace(["nan", "None", ""], pd.NA)
                )

        for k in keys:
            if k in df.columns:
                df[k] = df[k].fillna("N/A")

        grouped_dfs = []
        parent_count = 0

        for _, group_df in df.groupby(keys, sort=False):
            if grouping_mode == GROUPING_MODE_DEFAULT:
                mask_agrup = group_df[GROUPING_FLAG_COL].astype(str).str.strip() == GROUPING_FLAG_VALUE if GROUPING_FLAG_COL in group_df.columns else pd.Series(False, index=group_df.index)
                mask_main = group_df[HIERARCHY_PARENT_COL].astype(str).str.strip().str.upper() == HIERARCHY_PARENT_VALUE if HIERARCHY_PARENT_COL in group_df.columns else pd.Series(False, index=group_df.index)
                is_group = (mask_agrup.any() or mask_main.any()) and len(group_df) > 1
            else:
                is_group = len(group_df) > 1
            
            if is_group:
                parent_row = group_df.iloc[0].copy()
                parent_row[ENRICHMENT_KEY] = f"Consolidado ({grouping_mode.capitalize()})"
                parent_row[PARENT_ROW_FLAG] = True
                parent_row[CHILD_ROW_FLAG] = False
                
                for col in SUM_COLUMNS:
                    if col in group_df.columns:
                        series_clean = group_df[col].apply(lambda v: _parse_br_number(v, default=0.0))
                        parent_row[col] = pd.to_numeric(series_clean, errors="coerce").sum(min_count=1)
                
                grouped_dfs.append(pd.DataFrame([parent_row]))
                if include_child_rows:
                    child_df = group_df.copy()
                    child_df[CHILD_ROW_FLAG] = True
                    grouped_dfs.append(child_df)
                parent_count += 1
            else:
                normal_df = group_df.copy()
                normal_df[CHILD_ROW_FLAG] = False
                grouped_dfs.append(normal_df)
            
            grouped_dfs.append(pd.DataFrame([{SEPARATOR_ROW_FLAG: True, CHILD_ROW_FLAG: False, PARENT_ROW_FLAG: False}]))

        if grouped_dfs:
            df = pd.concat(grouped_dfs, ignore_index=True)

        df.drop(columns=[c for c in _temp_cols if c in df.columns], inplace=True, errors='ignore')
        df.drop(columns=["group_key", "dynamic_key"], inplace=True, errors='ignore')

        logger.info("Agrupamento concluído: %d faturas pai geradas.", parent_count)
        return df

    def _incomplete_mask(self, df: pd.DataFrame) -> pd.Series:
        if "Vencimento" not in df.columns:
            return pd.Series(False, index=df.index)
        return df["Vencimento"].isna() | (df["Vencimento"].astype(str).str.strip().str.lower().isin(["", "nan", "nat", "none"]))

    def _restrict_to_portal_invoices(self, df: pd.DataFrame, alias_lookup_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Mantém somente cobranças que existem na Gestão (portal), com no máximo
        uma linha por UC+Referência e valor positivo. Quando disponível, usa Valor_gestao como
        valor de faturamento final.
        """
        if df.empty or "Valor_gestao" not in df.columns:
            return df

        # Captura aliases de instalação antes dos filtros de valor da Gestão.
        raw = alias_lookup_df.copy() if alias_lookup_df is not None else df.copy()
        raw["_uc_base_raw"] = raw[ENRICHMENT_KEY].apply(_normalize_uc_text)
        if HIERARCHY_KEY_COL in raw.columns:
            raw["_uc_portal_raw"] = raw[HIERARCHY_KEY_COL].apply(_normalize_uc_text)
        else:
            raw["_uc_portal_raw"] = pd.NA
        alias_source = raw[raw["_uc_portal_raw"].notna() & raw[ENRICHMENT_KEY].apply(_contains_letter)]
        alias_map = (
            alias_source
            .dropna(subset=["_uc_portal_raw", ENRICHMENT_KEY])
            .drop_duplicates(subset=["_uc_portal_raw"], keep="first")
            .set_index("_uc_portal_raw")[ENRICHMENT_KEY]
            .to_dict()
        )

        work = df[df["Valor_gestao"].notna()].copy()
        work["Valor_gestao"] = pd.to_numeric(work["Valor_gestao"], errors="coerce")
        work = work[work["Valor_gestao"] > 0].copy()
        if work.empty:
            return work

        for col in [ENRICHMENT_KEY, "Referencia"]:
            if col not in work.columns:
                return work

        # A UC exibida no portal pode vir de "UC p Rateio" para alguns clientes.
        work["_uc_base"] = work[ENRICHMENT_KEY].apply(_normalize_uc_text)
        if HIERARCHY_KEY_COL in work.columns:
            work["_uc_portal"] = work[HIERARCHY_KEY_COL].apply(_normalize_uc_text)
        else:
            work["_uc_portal"] = pd.NA

        # Alguns clientes usam alias alfanumérico no portal (ex.: "W700..."/"E702...")
        # enquanto a base técnica usa o identificador numérico de rateio.
        work["_uc_alias"] = work["_uc_base"].map(alias_map)

        work["_uc_final"] = work["_uc_portal"].combine_first(work["_uc_alias"]).combine_first(work["_uc_base"])

        work = work.dropna(subset=["_uc_final", "Referencia"])
        if work.empty:
            return work

        key_cols = ["_uc_final", "Referencia"]

        # Prioriza linhas com origem "Fatura" e com número de conta preenchido.
        source_col = work.get(CLASSIFICATION_SOURCE_COL, pd.Series("", index=work.index)).astype(str).str.strip().str.lower()
        work["_portal_pref_fatura"] = source_col == "fatura"
        if ACCOUNT_NUMBER_COL in work.columns:
            work["_portal_pref_conta"] = work[ACCOUNT_NUMBER_COL].notna() & (work[ACCOUNT_NUMBER_COL].astype(str).str.strip() != "")
        else:
            work["_portal_pref_conta"] = False
        work["_portal_pref_valor"] = work.get("Valor Enviado Emissão", pd.Series(0.0, index=work.index)).apply(_parse_br_number, default=0.0).fillna(0.0)

        work = work.sort_values(
            by=["_portal_pref_fatura", "_portal_pref_conta", "_portal_pref_valor"],
            ascending=[False, False, False],
        )
        work = work.drop_duplicates(subset=key_cols, keep="first")

        # A UC de saída deve refletir a mesma identificação usada no portal.
        work[ENRICHMENT_KEY] = work["_uc_final"]

        # Valor da cobrança no portal tem precedência sobre o valor técnico do balanço.
        work["Valor Enviado Emissão"] = pd.to_numeric(work["Valor_gestao"], errors="coerce").fillna(0.0)

        work = work.drop(
            columns=[
                "_portal_pref_fatura",
                "_portal_pref_conta",
                "_portal_pref_valor",
                "_uc_base",
                "_uc_portal",
                "_uc_alias",
                "_uc_final",
            ],
            errors="ignore",
        )
        logger.info("Filtro portal-first aplicado: %d registros mantidos.", len(work))
        return work

    def _apply_classification(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if CLASSIFICATION_SOURCE_COL not in df.columns:
            df[CLASSIFICATION_COL] = CLASSIFICATION_LABEL_REGRA
            return df

        def _classify(val):
            if pd.isna(val): return CLASSIFICATION_LABEL_REGRA
            return CLASSIFICATION_LABEL_FATURA if str(val).strip() in CLASSIFICATION_FATURA_VALUES else CLASSIFICATION_LABEL_REGRA

        df[CLASSIFICATION_COL] = df[CLASSIFICATION_SOURCE_COL].apply(_classify)

        parent_mask = df.get(PARENT_ROW_FLAG, pd.Series(False, index=df.index)).astype(bool)
        if parent_mask.any() and CLASSIFICATION_COL in df.columns:
            parent_indices = df.index[parent_mask].tolist()
            for pi in parent_indices:
                loc = df.index.get_loc(pi)
                after = df.iloc[loc + 1:]
                stop_mask = after.get(PARENT_ROW_FLAG, pd.Series(False, index=after.index)).astype(bool) | after.get(SEPARATOR_ROW_FLAG, pd.Series(False, index=after.index)).astype(bool)
                stop_positions = stop_mask[stop_mask].index
                end_loc = df.index.get_loc(stop_positions[0]) if len(stop_positions) > 0 else len(df)
                child_labels = df.iloc[loc + 1:end_loc][CLASSIFICATION_COL]
                if not child_labels.empty:
                    counts = child_labels.value_counts()
                    majority_label = counts.index[0] if counts.iloc[0] > counts.sum() / 2 else CLASSIFICATION_LABEL_REGRA
                    df.at[pi, CLASSIFICATION_COL] = majority_label
        return df

    def generate(self, selected_clients: List[str], selected_periods: List[str], incomplete_filter: str = "all", group_by_distributor: bool = False, enrichment_df: pd.DataFrame = None, somente_pendencias: bool = False, tipo_apresentacao: str = "Tabela Única", incluir_resumo: bool = False, separar_auditoria: bool = False, grouping_mode: str = GROUPING_MODE_DEFAULT, include_child_rows: bool = True, sort_by: str = "Economia Gerada (Desc)") -> Optional[bytes]:
        if grouping_mode == GROUPING_MODE_DEFAULT and group_by_distributor:
            grouping_mode = GROUPING_MODE_DISTRIBUTOR

        logger.info("Gerando planilha. Modo: %s | Filhas: %s | Ordenação: %s", grouping_mode, include_child_rows, sort_by)
        filtered_df = self.reader.filter_data(selected_clients, selected_periods)
        alias_scope_df = self.reader.filter_data(selected_clients, [])
        filtered_df = self._restrict_to_portal_invoices(filtered_df, alias_lookup_df=alias_scope_df)

        actual_enrichment_cols = []
        if enrichment_df is not None and not enrichment_df.empty:
            clean_enrichment = enrichment_df.drop_duplicates(subset=[ENRICHMENT_KEY], keep='last')
            existing_cols = set(filtered_df.columns) - {ENRICHMENT_KEY}
            cols_to_drop = [c for c in clean_enrichment.columns if c in existing_cols]
            if cols_to_drop: clean_enrichment = clean_enrichment.drop(columns=cols_to_drop)
            actual_enrichment_cols = [c for c in clean_enrichment.columns if c != ENRICHMENT_KEY and c not in COLUMN_MAPPING]
            filtered_df = pd.merge(filtered_df, clean_enrichment, on=ENRICHMENT_KEY, how='left')

        if filtered_df.empty: return None
        if incomplete_filter == "complete_only":
            filtered_df = filtered_df.loc[~self._incomplete_mask(filtered_df)].copy()
        elif incomplete_filter == "incomplete_only":
            filtered_df = filtered_df.loc[self._incomplete_mask(filtered_df)].copy()
        if filtered_df.empty: return None

        # Ordenação Customizada
        sort_col = None
        ascending = True
        if sort_by == "Economia Gerada (Desc)":
            sort_col = "Ganho total Padrão"
            ascending = False
        elif sort_by == "Razão Social":
            sort_col = CLIENT_COLUMN
        elif sort_by == "Instalação (UC)":
            sort_col = ENRICHMENT_KEY
        
        if sort_col and sort_col in filtered_df.columns:
            if sort_by == "Economia Gerada (Desc)":
                filtered_df["_temp_sort"] = filtered_df[sort_col].apply(_parse_br_number, default=0.0)
                filtered_df = filtered_df.sort_values(by="_temp_sort", ascending=ascending).drop(columns=["_temp_sort"])
            else:
                filtered_df = filtered_df.sort_values(by=sort_col, ascending=ascending)

        processed_df = self._apply_grouping(filtered_df, grouping_mode=grouping_mode, include_child_rows=include_child_rows)
        processed_df = self._apply_classification(processed_df)
        
        legacy_keys = list(COLUMN_MAPPING.keys())
        for col in legacy_keys:
            if col not in processed_df.columns: processed_df[col] = pd.NA
        
        extra_cols = [c for c in actual_enrichment_cols if c in processed_df.columns]
        final_columns = legacy_keys + extra_cols
        processed_df = processed_df.reindex(columns=final_columns + [PARENT_ROW_FLAG, CHILD_ROW_FLAG, SEPARATOR_ROW_FLAG])
        
        from collections import OrderedDict
        full_mapping = OrderedDict()
        for k in legacy_keys: full_mapping[k] = COLUMN_MAPPING[k]
        for k in extra_cols: full_mapping[k] = k

        processed_df = enforce_payment_rules(processed_df)
        if somente_pendencias and "Status Pos-Faturamento" in processed_df.columns:
            is_pago = processed_df["Status Pos-Faturamento"].astype(str).str.strip().str.lower() == "pago"
            processed_df = processed_df.loc[~is_pago].copy()

        writer = TemplateExcelWriter(self.template_file)
        return writer.generate_bytes(processed_df, full_mapping, tipo_apresentacao=tipo_apresentacao, incluir_resumo=incluir_resumo, separar_auditoria=separar_auditoria)

    def generate_multiple(self, groups: List[Dict[str, Any]], incomplete_filter: str = "all", group_by_distributor: bool = False, enrichment_df: pd.DataFrame = None, somente_pendencias: bool = False, tipo_apresentacao: str = "Tabela Única", incluir_resumo: bool = False, separar_auditoria: bool = False, grouping_mode: str = GROUPING_MODE_DEFAULT, include_child_rows: bool = True, sort_by: str = "Economia Gerada (Desc)") -> Optional[bytes]:
        import zipfile
        import io
        zip_buffer = io.BytesIO()
        generated_count = 0
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for group in groups:
                excel_bytes = self.generate(group.get('clients', []), group.get('periods', []), incomplete_filter=incomplete_filter, grouping_mode=grouping_mode, include_child_rows=include_child_rows, enrichment_df=enrichment_df, somente_pendencias=somente_pendencias, tipo_apresentacao=tipo_apresentacao, incluir_resumo=incluir_resumo, separar_auditoria=separar_auditoria, sort_by=sort_by)
                if excel_bytes:
                    name = group.get('name', 'Sem_Nome')
                    zip_file.writestr(name if name.endswith(".xlsx") else f"{name}.xlsx", excel_bytes)
                    generated_count += 1
        return zip_buffer.getvalue() if generated_count > 0 else None

    def get_all_ucs_with_names(self) -> pd.DataFrame:
        if self.reader.df.empty: return pd.DataFrame(columns=[ENRICHMENT_KEY, CLIENT_COLUMN])
        cols = [ENRICHMENT_KEY, CLIENT_COLUMN]
        return self.reader.df[cols].drop_duplicates().sort_values(by=CLIENT_COLUMN)
