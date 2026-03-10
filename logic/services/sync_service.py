"""
Serviço responsável por receber as planilhas via upload,
cruzar as informações (Merge) e gerar o cache local em Parquet.
Opcionalmente, envia cópias para o Firebase Cloud Storage como backup.
"""
import os
import logging
import pandas as pd
import json
from datetime import datetime
from logic.adapters.excel_adapter import BaseExcelReader
from config.settings import settings

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join("data", "cache")
PARQUET_FILE = os.path.join(CACHE_DIR, "base_consolidada.parquet")
PENDENCIAS_FILE = os.path.join(CACHE_DIR, "pendencias.json")

BALANCO_REMOTE = "bases/Balanco_Energetico_Raizen.xlsm"
GESTAO_REMOTE = "bases/gd_gestao_cobranca.xlsx"

BALANCO_LOCAL = os.path.join(CACHE_DIR, "Balanco_Energetico.xlsm")
GESTAO_LOCAL = os.path.join(CACHE_DIR, "gd_gestao.xlsx")

# Colunas que são intencionalmente texto — nunca converter para numérico
_TEXT_COLUMNS = {
    "Razao Social", "Distribuidora", "Desconto Contratado",
    "Status Pos-Faturamento", "No. UC", "CPF/CNPJ", "Referencia",
    "Excecao Fat.", "Vencimento",
}


def build_consolidated_cache_from_uploads(balanco_bytes: bytes, gestao_bytes: bytes | None = None, firebase_client=None) -> tuple[bool, dict | None]:
    """
    Recebe os bytes dos arquivos de upload, salva localmente, faz o merge e gera Parquet.
    Opcionalmente tenta fazer backup no Firebase Storage.
    Retorna True se sucesso.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    # 1. Salvar arquivos localmente a partir dos bytes do upload
    logger.info("Salvando arquivos de upload localmente...")
    try:
        with open(BALANCO_LOCAL, "wb") as f:
            f.write(balanco_bytes)
        logger.info("Balanço Energético salvo em: %s", BALANCO_LOCAL)
    except Exception as e:
        logger.error("Erro ao salvar Balanço localmente: %s", e)
        return False

    if gestao_bytes:
        try:
            with open(GESTAO_LOCAL, "wb") as f:
                f.write(gestao_bytes)
            logger.info("Gestão Cobrança salva em: %s", GESTAO_LOCAL)
        except Exception as e:
            logger.warning("Erro ao salvar Gestão localmente: %s", e)

    # 2. Backup opcional no Firebase Storage
    if firebase_client:
        try:
            firebase_client.upload_file(balanco_bytes, BALANCO_REMOTE)
            if gestao_bytes:
                firebase_client.upload_file(gestao_bytes, GESTAO_REMOTE)
            logger.info("Backup no Firebase realizado com sucesso.")
        except Exception as e:
            logger.warning("Backup no Firebase falhou (continuando sem nuvem): %s", e)

    return _process_dataframes(BALANCO_LOCAL, gestao_bytes, GESTAO_LOCAL)

def build_consolidated_cache_from_local_network(network_path: str) -> tuple[bool, dict | None]:
    """
    Lê a planilha central do Balanço Energético diretamente do caminho do usuário na rede local/OneDrive,
    dispensando a necessidade de upload de um arquivo de ~12MB cada vez.
    Neste escopo de Auto-Sync, só preenchemos as obrigatoriedades e bypassamos a Gestão manual por ora, 
    ou podemos futuramente mapear uma gestão na rede também.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    if not os.path.exists(network_path):
        logger.error(f"Arquivo de rede não encontrado no caminho: {network_path}")
        return False

    logger.info(f"Copiando arquivo de rede local ({network_path}) para o cache de trabalho...")
    try:
        # Cópia binária direta por segurança contra locks de rede
        with open(network_path, "rb") as src, open(BALANCO_LOCAL, "wb") as dst:
            dst.write(src.read())
        logger.info("Sucesso na importação da rede local!")
    except Exception as e:
        logger.error(f"Falha ao ler da rede local: {e}")
        return False, None
        
    return _process_dataframes(BALANCO_LOCAL, None, None)

def _process_dataframes(balanco_path: str, gestao_bytes: bytes | None, gestao_path: str | None) -> tuple[bool, dict | None]:
    """Motor central que efetivamente cria o Merge e Parquet a partir dos paths ou bytes providenciados."""
    # 3. Ler Balanço Energético
    logger.info("Iniciando leitura do Balanço Energético...")
    try:
        reader_balanco = BaseExcelReader(BALANCO_LOCAL, sheet_name=settings.base_sheet_name)
        df_balanco = reader_balanco.df
    except Exception as e:
        logger.error("Erro ao ler Balanço Energético local: %s", e)
        return False, None

    df_consolidado = df_balanco.copy()

    # 4. Cruzamento com a Gestão de Cobrança (se disponível)
    report = None
    if gestao_bytes and gestao_path and os.path.exists(gestao_path):
        logger.info("Lendo base de Gestão para enriquecimento (Vencimento e Status)...")
        try:
            gestao_headers = pd.read_excel(GESTAO_LOCAL, nrows=0).columns.tolist()
            header_map = {str(c).strip().lower(): str(c) for c in gestao_headers}

            uc_col = header_map.get("instalação", header_map.get("uc", header_map.get("no. uc")))
            venc_col = header_map.get("vencimento", header_map.get("data de vencimento"))
            status_col = header_map.get("status", header_map.get("status financeiro"))
            cancel_col = header_map.get("data de cancelamento")

            cols_to_read = []
            if uc_col: cols_to_read.append(uc_col)
            if venc_col: cols_to_read.append(venc_col)
            if status_col: cols_to_read.append(status_col)
            if cancel_col: cols_to_read.append(cancel_col)

            if uc_col and (venc_col or status_col):
                # Incluir Mês de Referência na leitura
                ref_col = header_map.get("mês de referência", header_map.get("mes de referencia", header_map.get("referência", header_map.get("referencia"))))
                cancelada_col = header_map.get("cancelada")
                
                if ref_col: cols_to_read.append(ref_col)
                if cancelada_col: cols_to_read.append(cancelada_col)

                df_gestao = pd.read_excel(GESTAO_LOCAL, usecols=cols_to_read)

                # 1. Definir auxiliares de normalização
                def normalize_uc(val):
                    if pd.isna(val): return ""
                    s = str(val).strip()
                    if s.endswith(".0"): s = s[:-2]
                    s = ''.join(filter(str.isdigit, s))
                    return s
                
                # 2. Normalizar e colher conjunto total de UCs na gestão para o relatório
                df_gestao["No. UC_norm"] = df_gestao[uc_col].apply(normalize_uc)
                all_gestao_ucs = set(df_gestao["No. UC_norm"].unique())

                def parse_ref(val):
                    if pd.isna(val): return pd.NaT
                    s = str(val).strip()
                    try:
                        parts = s.replace("/", "-").split("-")
                        if len(parts) == 2:
                            if len(parts[0]) == 4: # YYYY-MM
                                return pd.Timestamp(year=int(parts[0]), month=int(parts[1]), day=1)
                            else: # MM-YYYY
                                return pd.Timestamp(year=int(parts[1]), month=int(parts[0]), day=1)
                    except:
                        pass
                    return pd.to_datetime(val, errors="coerce")

                # 3. Normalizar chaves em ambas as bases para detecção de cancelados
                df_consolidado["No. UC_norm"] = df_consolidado["No. UC"].apply(normalize_uc)
                
                ref_merge_col = "Referencia_merge"
                if ref_col:
                    df_gestao[ref_merge_col] = df_gestao[ref_col].apply(parse_ref)
                    df_consolidado[ref_merge_col] = pd.to_datetime(df_consolidado["Referencia"], errors="coerce").dt.to_period('M').dt.to_timestamp()

                # 3. Identificar Cancelados (para remoção total do Balanço)
                mask_canceled = pd.Series(False, index=df_gestao.index)
                if cancelada_col and cancelada_col in df_gestao.columns:
                    mask_canceled = df_gestao[cancelada_col].astype(str).str.strip().str.upper().isin(["SIM", "S", "TRUE", "1"])
                elif cancel_col and cancel_col in df_gestao.columns:
                    cv = df_gestao[cancel_col].astype(str).str.strip().str.lower()
                    mask_canceled = df_gestao[cancel_col].notna() & (~cv.isin(["", "-", "nan", "nat", "none"]))

                # Remover faturas canceladas do Balanço Energético AGORA
                # Isso evita que elas apareçam no Excel e que o Fallback ressuscite elas com datas erradas
                if mask_canceled.any() and ref_merge_col in df_consolidado.columns:
                    # Identificar chaves (UC+Período) candidatas a cancelamento
                    df_canceled_cand = df_gestao[mask_canceled][["No. UC_norm", ref_merge_col]].dropna().drop_duplicates()
                    # Identificar chaves que possuem pelo menos um registro ATIVO
                    df_active_keys = df_gestao[~mask_canceled][["No. UC_norm", ref_merge_col]].dropna().drop_duplicates()
                    
                    if not df_canceled_cand.empty:
                        # Criar chaves compostas para comparação
                        cand_keys = df_canceled_cand["No. UC_norm"] + "_" + df_canceled_cand[ref_merge_col].astype(str)
                        active_keys = df_active_keys["No. UC_norm"] + "_" + df_active_keys[ref_merge_col].astype(str)
                        
                        # Só removemos do Balanço se a chave estiver cancelada E NÃO houver versão ativa
                        drop_keys = cand_keys[~cand_keys.isin(active_keys)]
                        
                        if not drop_keys.empty:
                            target_keys = df_consolidado["No. UC_norm"] + "_" + df_consolidado[ref_merge_col].astype(str)
                            antes = len(df_consolidado)
                            df_consolidado = df_consolidado[~target_keys.isin(drop_keys)].copy()
                            logger.info("Filtro Canceladas: %d registros removidos da base consolidada.", antes - len(df_consolidado))

                # 4. Limpar df_gestao (remover cancelados) e renomear para o Merge
                # Remover cancelados da gestão ANTES de deduplicar
                df_gestao = df_gestao[~mask_canceled].copy()
                logger.info(
                    "Gestão após remoção de cancelados: %d registros.", len(df_gestao)
                )
                
                rename_dict = {}
                if venc_col: rename_dict[venc_col] = "Vencimento"
                if status_col: rename_dict[status_col] = "Status Pos-Faturamento_gestao"
                
                # Remover colunas originais que não usaremos mais ou renomearemos
                cols_to_drop = [uc_col]
                if ref_col: cols_to_drop.append(ref_col)
                if cancel_col: cols_to_drop.append(cancel_col)
                if cancelada_col: cols_to_drop.append(cancelada_col)
                
                df_gestao = df_gestao.drop(columns=[c for c in cols_to_drop if c in df_gestao.columns])
                df_gestao.rename(columns=rename_dict, inplace=True)

                # 5. Realizar o Merge (Cruzamento)
                merge_keys = ["No. UC_norm"]
                if ref_merge_col in df_gestao.columns and ref_merge_col in df_consolidado.columns:
                    merge_keys.append(ref_merge_col)
                
                # Deduplicar gestão preservando o período
                df_gestao = df_gestao.dropna(subset=merge_keys)

                # Ordenar por Vencimento decrescente antes de deduplicar
                # Assim keep="first" preserva sempre o vencimento mais recente
                # entre duplicatas do mesmo UC + Período
                if "Vencimento" in df_gestao.columns:
                    df_gestao["_venc_sort"] = pd.to_datetime(
                        df_gestao["Vencimento"], dayfirst=True, errors="coerce"
                    )
                    df_gestao = df_gestao.sort_values("_venc_sort", ascending=False)
                    df_gestao = df_gestao.drop(columns=["_venc_sort"])

                df_gestao = df_gestao.drop_duplicates(subset=merge_keys, keep="first")
                logger.info(
                    "Gestão após deduplicação: %d registros únicos por UC+Período.",
                    len(df_gestao)
                )

                logger.info("Realizando merge (cruzamento) usando chaves %s (%d registros Gestão)...", merge_keys, len(df_gestao))
                _original_len = len(df_consolidado)  # capture antes do merge
                df_consolidado = pd.merge(df_consolidado, df_gestao, on=merge_keys, how="left")

                # Validação pós-merge
                n_sem_vencimento = df_consolidado["Vencimento"].isna().sum() if "Vencimento" in df_consolidado.columns else 0
                n_linhas_extras = len(df_consolidado) - _original_len

                logger.info(
                    "Pós-merge: %d registros | %d sem Vencimento | %d linhas vs original",
                    len(df_consolidado), n_sem_vencimento, n_linhas_extras
                )

                if n_linhas_extras > 0:
                    pct = n_linhas_extras / max(_original_len, 1) * 100
                    logger.warning(
                        "Merge produziu %d linhas extras (%.1f%% acima do original). "
                        "Possível duplicata na base de Gestão.",
                        n_linhas_extras, pct
                    )
                    if pct > 5.0:
                        raise ValueError(
                            f"Merge abortado: {n_linhas_extras} linhas extras "
                            f"({pct:.1f}% acima do original de {_original_len}). "
                            "Verifique duplicatas na base de Gestão por UC + Período."
                        )

                # 6. Removido Fallback por UC (evitar mistura de referências)
                # O merge agora é estritamente por UC + Período.

                # 7. Consolidação final de nomes de colunas
                if "Status Pos-Faturamento_gestao" in df_consolidado.columns and "Status Pos-Faturamento" in df_consolidado.columns:
                    df_consolidado["Status Pos-Faturamento"] = df_consolidado["Status Pos-Faturamento_gestao"].combine_first(df_consolidado["Status Pos-Faturamento"])
                    df_consolidado.drop(columns=["Status Pos-Faturamento_gestao"], inplace=True)
                elif "Status Pos-Faturamento_gestao" in df_consolidado.columns:
                    df_consolidado.rename(columns={"Status Pos-Faturamento_gestao": "Status Pos-Faturamento"}, inplace=True)
                    
                # Limpar colunas auxiliares de merge (mantendo No. UC_norm para o relatório se necessário)
                
                # 8. Detecção de Pendências
                mask_missing = df_consolidado["Vencimento"].isna()
                if mask_missing.any():
                    missing_df = df_consolidado[mask_missing].copy()
                    pendencias = []
                    
                    for _, row in missing_df.iterrows():
                        uc_norm = row["No. UC_norm"]
                        tipo = "UC_AUSENTE_NA_GESTAO" if uc_norm not in all_gestao_ucs else "PERIODO_NAO_LANCADO"
                        
                        pendencias.append({
                            "no_uc": str(row["No. UC"]),
                            "referencia": str(row["Referencia"]),
                            "razao_social": str(row["Razao Social"]),
                            "cpf_cnpj": str(row["CPF/CNPJ"]),
                            "tipo": tipo
                        })
                    
                    report = {
                        "gerado_em": datetime.now().isoformat(),
                        "total_ucs_sem_vencimento": len(pendencias),
                        "pendencias": pendencias
                    }
                    
                    try:
                        with open(PENDENCIAS_FILE, "w", encoding="utf-8") as f:
                            json.dump(report, f, indent=2, ensure_ascii=False)
                        logger.info("Relatório de pendências salvo com %d itens.", len(pendencias))
                    except Exception as e:
                        logger.warning("Erro ao salvar pendencias.json: %s", e)
                else:
                    report = {
                        "gerado_em": datetime.now().isoformat(),
                        "total_ucs_sem_vencimento": 0,
                        "pendencias": []
                    }
                    try:
                        with open(PENDENCIAS_FILE, "w", encoding="utf-8") as f:
                            json.dump(report, f, indent=2, ensure_ascii=False)
                    except: pass

                drop_aux = ["No. UC_norm", "Referencia_merge"]
                df_consolidado.drop(columns=[c for c in drop_aux if c in df_consolidado.columns], inplace=True)
            else:
                logger.warning("Colunas chaves não encontradas na Gestão: UC=%s, Vencimento=%s", uc_col, venc_col)
        except ValueError as e:
            # Re-raise erros de validação propositais
            logger.error(str(e))
            raise e
        except Exception as e:
            logger.warning("Falha ao ler ou cruzar base de Gestão (continuará apenas com Balanço). Erro: %s", e)
            import traceback
            logger.debug(traceback.format_exc())
            report = None
    else:
        logger.info("Base de Gestão não disponível. Seguindo sem Vencimento/Status extra.")

    # 5. Corrigir colunas com dtype misto para evitar falha no Parquet
    for col in df_consolidado.select_dtypes(include=["object"]).columns:
        if col in _TEXT_COLUMNS:
            df_consolidado[col] = df_consolidado[col].astype(str).replace("nan", pd.NA)
            continue
        try:
            converted = pd.to_numeric(df_consolidado[col], errors="coerce")
            # Se >= 80% dos valores foram convertidos com sucesso, aceitar como numérico
            if converted.notna().sum() >= 0.8 * df_consolidado[col].notna().sum():
                df_consolidado[col] = converted
                logger.debug("Coluna '%s' convertida de object para numérico.", col)
                continue
        except (ValueError, TypeError):
            pass
        # Colunas que continuam object: forçar string para evitar erro de encoding
        df_consolidado[col] = df_consolidado[col].astype(str).replace("nan", pd.NA)

    # 6. Salvar o Parquet consolidado
    try:
        df_consolidado.to_parquet(PARQUET_FILE, engine="fastparquet", index=False)
        logger.info("Cache consolidado salvo com sucesso: %s (%d registros)", PARQUET_FILE, len(df_consolidado))
        return True, report
    except Exception as e:
        logger.error("Erro ao salvar Parquet: %s", e)
        return False, report


def get_parquet_dataframe() -> pd.DataFrame:
    """Lê e retorna o DataFrame cacheado. Levanta FileNotFoundError se não existir."""
    if not os.path.exists(PARQUET_FILE):
        raise FileNotFoundError(f"Cache {PARQUET_FILE} não encontrado.")
    return pd.read_parquet(PARQUET_FILE, engine="fastparquet")


def get_cache_update_time() -> str:
    """Retorna data formatada da última atualização do cache local."""
    if os.path.exists(PARQUET_FILE):
        mtime = os.path.getmtime(PARQUET_FILE)
        return datetime.fromtimestamp(mtime).strftime("%d/%m/%Y às %H:%M")
    return "Nunca"


def get_pendencias() -> dict | None:
    """Retorna o relatório de pendências ou None se não existir."""
    if not os.path.exists(PENDENCIAS_FILE):
        return None
    try:
        with open(PENDENCIAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Erro ao ler pendencias.json: %s", e)
        return None
