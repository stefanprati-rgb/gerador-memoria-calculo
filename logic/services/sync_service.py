"""
Serviço responsável por receber as planilhas via upload,
cruzar as informações (Merge) e gerar o cache local em Parquet.
Opcionalmente, envia cópias para o Firebase Cloud Storage como backup.
"""
import os
import logging
import pandas as pd
from datetime import datetime
from logic.adapters.excel_adapter import BaseExcelReader
from config.settings import settings

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join("data", "cache")
PARQUET_FILE = os.path.join(CACHE_DIR, "base_consolidada.parquet")

BALANCO_REMOTE = "bases/Balanco_Energetico_Raizen.xlsm"
GESTAO_REMOTE = "bases/gd_gestao_cobranca.xlsx"

BALANCO_LOCAL = os.path.join(CACHE_DIR, "Balanco_Energetico.xlsm")
GESTAO_LOCAL = os.path.join(CACHE_DIR, "gd_gestao.xlsx")


def build_consolidated_cache_from_uploads(balanco_bytes: bytes, gestao_bytes: bytes | None = None, firebase_client=None) -> bool:
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

def build_consolidated_cache_from_local_network(network_path: str) -> bool:
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
        return False
        
    return _process_dataframes(BALANCO_LOCAL, None, None)

def _process_dataframes(balanco_path: str, gestao_bytes: bytes, gestao_path: str) -> bool:
    """Motor central que efetivamente cria o Merge e Parquet a partir dos paths ou bytes providenciados."""
    # 3. Ler Balanço Energético
    logger.info("Iniciando leitura do Balanço Energético...")
    try:
        reader_balanco = BaseExcelReader(BALANCO_LOCAL, sheet_name=settings.base_sheet_name)
        df_balanco = reader_balanco.df
    except Exception as e:
        logger.error("Erro ao ler Balanço Energético local: %s", e)
        return False

    df_consolidado = df_balanco.copy()

    # 4. Cruzamento com a Gestão de Cobrança (se disponível)
    if gestao_bytes and os.path.exists(GESTAO_LOCAL):
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

                # 1. Filtrar Cancelados
                # Primeira tentativa: Coluna "Cancelada" (Sim/Não)
                if cancelada_col and cancelada_col in df_gestao.columns:
                    antes = len(df_gestao)
                    cancelados = df_gestao[cancelada_col].astype(str).str.strip().str.upper()
                    # Manter apenas o que NÃO for "SIM" ou "S"
                    df_gestao = df_gestao[~cancelados.isin(["SIM", "S", "TRUE", "1"])]
                    logger.info("Filtro Cancelada (coluna): %d removidos.", antes - len(df_gestao))
                    df_gestao = df_gestao.drop(columns=[cancelada_col])
                # Segunda tentativa: Data de Cancelamento preenchida
                elif cancel_col and cancel_col in df_gestao.columns:
                    antes = len(df_gestao)
                    cancel_values = df_gestao[cancel_col].astype(str).str.strip()
                    mask_not_cancelled = pd.isna(df_gestao[cancel_col]) | (cancel_values == "") | (cancel_values == "-") | (cancel_values == "nan") | (cancel_values.str.lower() == "nat") | (cancel_values.str.lower() == "none")
                    df_gestao = df_gestao[mask_not_cancelled]
                    logger.info("Filtro Data de Cancelamento: %d removidos.", antes - len(df_gestao))
                    df_gestao = df_gestao.drop(columns=[cancel_col])

                # Renomear colunas
                rename_dict = {uc_col: "No. UC"}
                if venc_col: rename_dict[venc_col] = "Vencimento"
                if status_col: rename_dict[status_col] = "Status Pos-Faturamento_gestao"
                if ref_col: rename_dict[ref_col] = "Referencia_gestao"

                df_gestao.rename(columns=rename_dict, inplace=True)

                # 2. Normalizar No. UC
                def normalize_uc(val):
                    if pd.isna(val): return ""
                    s = str(val).strip()
                    if s.endswith(".0"): s = s[:-2]
                    # Remover pontuações, deixar só dígitos
                    s = ''.join(filter(str.isdigit, s))
                    return s

                df_consolidado["No. UC_norm"] = df_consolidado["No. UC"].apply(normalize_uc)
                df_gestao["No. UC_norm"] = df_gestao["No. UC"].apply(normalize_uc)
                
                # Para evitar colunas duplicadas (x_ e _y) no merge, dropamos a original da Gestão
                df_gestao = df_gestao.drop(columns=["No. UC"])

                # 3. Normalizar Referência da Gestão (ex: "11-2025" -> Timestamp("2025-11-01"))
                merge_keys = ["No. UC_norm"]
                if "Referencia_gestao" in df_gestao.columns and "Referencia" in df_consolidado.columns:
                    def parse_ref(val):
                        if pd.isna(val): return pd.NaT
                        s = str(val).strip()
                        try:
                            # Formato esperado: MM-YYYY ou MM/YYYY
                            parts = s.replace("/", "-").split("-")
                            if len(parts) == 2:
                                if len(parts[0]) == 4: # YYYY-MM
                                    return pd.Timestamp(year=int(parts[0]), month=int(parts[1]), day=1)
                                else: # MM-YYYY
                                    return pd.Timestamp(year=int(parts[1]), month=int(parts[0]), day=1)
                        except:
                            pass
                        # Fallback to pandas to_datetime
                        return pd.to_datetime(val, errors="coerce")
                        
                    df_gestao["Referencia_merge"] = df_gestao["Referencia_gestao"].apply(parse_ref)
                    # Normalizar o lado do Balanço pro primeiro dia do mês para garantir match
                    df_consolidado["Referencia_merge"] = pd.to_datetime(df_consolidado["Referencia"], errors="coerce").dt.to_period('M').dt.to_timestamp()
                    
                    merge_keys.append("Referencia_merge")
                    
                # 4. Deduplicar gestão preservando o período
                df_gestao = df_gestao.dropna(subset=merge_keys)
                df_gestao = df_gestao.drop_duplicates(subset=merge_keys, keep="last")

                logger.info("Realizando merge (cruzamento) usando chaves %s (%d registros Gestão)...", merge_keys, len(df_gestao))
                df_consolidado = pd.merge(df_consolidado, df_gestao, on=merge_keys, how="left")

                # Fallback: tentar merge apenas por UC para períodos que não deram match
                if "Referencia_merge" in merge_keys:
                    missing_venc = df_consolidado["Vencimento"].isna() if "Vencimento" in df_consolidado.columns else pd.Series(True, index=df_consolidado.index)
                    if missing_venc.any():
                        # Cria um mapping UC -> último vencimento disponível na gestão (ignorando período)
                        gestao_latest = df_gestao.drop_duplicates(subset=["No. UC_norm"], keep="last")
                        
                        logger.info("Fallback merge por UC para %d registros sem período correspondente.", missing_venc.sum())
                        if "Vencimento" in gestao_latest.columns:
                            vmap = gestao_latest.set_index("No. UC_norm")["Vencimento"]
                            df_consolidado.loc[missing_venc, "Vencimento"] = df_consolidado.loc[missing_venc, "No. UC_norm"].map(vmap)
                            
                        status_gestao_col = "Status Pos-Faturamento_gestao"
                        if status_gestao_col in gestao_latest.columns:
                            smap = gestao_latest.set_index("No. UC_norm")[status_gestao_col]
                            if status_gestao_col in df_consolidado.columns:
                                df_consolidado.loc[missing_venc, status_gestao_col] = df_consolidado.loc[missing_venc, "No. UC_norm"].map(smap)

                # Limpeza: consolidar as duas colunas de Status Pos-Faturamento
                if "Status Pos-Faturamento_gestao" in df_consolidado.columns and "Status Pos-Faturamento" in df_consolidado.columns:
                    df_consolidado["Status Pos-Faturamento"] = df_consolidado["Status Pos-Faturamento_gestao"].combine_first(df_consolidado["Status Pos-Faturamento"])
                    df_consolidado.drop(columns=["Status Pos-Faturamento_gestao"], inplace=True)
                elif "Status Pos-Faturamento_gestao" in df_consolidado.columns:
                    df_consolidado.rename(columns={"Status Pos-Faturamento_gestao": "Status Pos-Faturamento"}, inplace=True)
                    
                # Limpar colunas auxiliares de merge
                drop_aux = ["No. UC_norm", "Referencia_merge", "Referencia_gestao"]
                df_consolidado.drop(columns=[c for c in drop_aux if c in df_consolidado.columns], inplace=True)
            else:
                logger.warning("Colunas chaves não encontradas na Gestão: UC=%s, Vencimento=%s", uc_col, venc_col)
        except Exception as e:
            logger.warning("Falha ao ler ou cruzar base de Gestão (continuará apenas com Balanço). Erro: %s", e)
    else:
        logger.info("Base de Gestão não disponível. Seguindo sem Vencimento/Status extra.")

    # 5. Corrigir colunas com dtype misto para evitar falha no Parquet
    for col in df_consolidado.select_dtypes(include=["object"]).columns:
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
        return True
    except Exception as e:
        logger.error("Erro ao salvar Parquet: %s", e)
        return False


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
