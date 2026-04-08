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

# --- Configuração de Cache Resiliente ---
_CACHE_DIR_ENV = os.getenv("SYNC_SERVICE_CACHE_DIR")
CACHE_DIR = _CACHE_DIR_ENV if _CACHE_DIR_ENV else os.path.join("data", "cache")
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
    "Excecao Fat.", "Vencimento", "Número da conta",
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
            # Colunas financeiras da Gestão para o Grupo 1
            base_calc_col = header_map.get("base para cálculo", header_map.get("base para calculo"))
            valor_cob_col = header_map.get("valor da cobrança r$", 
                                           header_map.get("valor da cobranca r$", 
                                           header_map.get("valor da cobrança", 
                                           header_map.get("valor da cobranca"))))
            
            cancel_col = header_map.get("data de cancelamento")
            ref_col = header_map.get("mês de referência", header_map.get("mes de referencia", header_map.get("referência", header_map.get("referencia"))))
            cancelada_col = header_map.get("cancelada")
            # Coluna "Número da conta" — detectar com/sem acento e espaços
            conta_col = header_map.get("número da conta", 
                                       header_map.get("numero da conta", 
                                       header_map.get("nº conta",
                                       header_map.get("conta"))))

            cols_to_read = []
            if uc_col: cols_to_read.append(uc_col)
            if venc_col: cols_to_read.append(venc_col)
            if status_col: cols_to_read.append(status_col)
            if base_calc_col: cols_to_read.append(base_calc_col)
            if valor_cob_col: cols_to_read.append(valor_cob_col)
            
            if cancel_col: cols_to_read.append(cancel_col)
            if ref_col: cols_to_read.append(ref_col)
            if cancelada_col: cols_to_read.append(cancelada_col)
            if conta_col: cols_to_read.append(conta_col)

            df_gestao = pd.read_excel(GESTAO_LOCAL, usecols=cols_to_read)

            # 1. Definir auxiliares de normalização
            def normalize_uc(val):
                if pd.isna(val): return ""
                s = str(val).strip()
                if s.endswith(".0"): s = s[:-2]
                s = ''.join(filter(str.isdigit, s))
                return s.lstrip('0')
            
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
                # Força dayfirst=True para evitar confusão entre 11/12 (Nov/Dez) e 12/11 (Dez/Nov)
                dt = pd.to_datetime(val, errors="coerce", dayfirst=True)
                if pd.notna(dt):
                    return dt.replace(day=1)
                return pd.NaT

            # 3. Normalizar chaves em ambas as bases para detecção de cancelados
            df_consolidado["No. UC_norm"] = df_consolidado["No. UC"].apply(normalize_uc)
            
            ref_merge_col = "Referencia_merge"
            if ref_col:
                df_gestao[ref_merge_col] = df_gestao[ref_col].apply(parse_ref)
                
                # Garantir que a Referencia do Balanço seja tratada como datetime corretamente,
                # respeitando o formato DD/MM/YYYY se for string.
                ref_series = df_consolidado["Referencia"]
                # Tenta converter explicitamente assumindo dia/mês/ano se for string text
                ref_dt = pd.to_datetime(ref_series, errors="coerce", dayfirst=True)
                df_consolidado[ref_merge_col] = ref_dt.dt.to_period('M').dt.to_timestamp()

            # REVERTIDO: Não removemos mais faturas do Balanço com base na Gestão (evitar "deduplicação assassina")
            # Deixamos que apareçam e o usuário decida ou o status indique o problema.
            pass

            rename_dict = {}
            if venc_col: rename_dict[venc_col] = "Vencimento"
            if status_col: rename_dict[status_col] = "Status Pos-Faturamento_gestao"
            if valor_cob_col: rename_dict[valor_cob_col] = "Valor_gestao"
            if base_calc_col: rename_dict[base_calc_col] = "Base_gestao"
            from logic.core.mapping import ACCOUNT_NUMBER_COL
            if conta_col: rename_dict[conta_col] = ACCOUNT_NUMBER_COL
            
            # Remover colunas originais que não usaremos mais ou renomearemos
            cols_to_drop = [uc_col]
            if ref_col: cols_to_drop.append(ref_col)
            if cancel_col: cols_to_drop.append(cancel_col)
            if cancelada_col: cols_to_drop.append(cancelada_col)
            
            df_gestao = df_gestao.drop(columns=[c for c in cols_to_drop if c in df_gestao.columns])
            df_gestao.rename(columns=rename_dict, inplace=True)

            # Limpeza de valores numéricos na Gestão (R$ 1.234,56 -> 1234.56)
            for col in ["Valor_gestao", "Base_gestao"]:
                if col in df_gestao.columns:
                    # Só limpar se for string. Se já for numeric (float/int), não mexer.
                    if pd.api.types.is_string_dtype(df_gestao[col]):
                        df_gestao[col] = df_gestao[col].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
                    df_gestao[col] = pd.to_numeric(df_gestao[col], errors="coerce")

            # 5. Realizar o Merge (Cruzamento)
            merge_keys = ["No. UC_norm"]
            if ref_merge_col in df_gestao.columns and ref_merge_col in df_consolidado.columns:
                merge_keys.append(ref_merge_col)
            
            # Garantir que não há NaT nas chaves de merge antes de deduplicar
            df_gestao = df_gestao.dropna(subset=merge_keys)

            # Ordenar por Vencimento decrescente antes de deduplicar
            # Assim keep="first" preserva sempre o vencimento mais recente
            # entre duplicatas do mesmo UC + Período
            if "Vencimento" in df_gestao.columns:
                df_gestao["_venc_sort"] = pd.to_datetime(
                    df_gestao["Vencimento"], dayfirst=True, errors="coerce"
                )
                df_gestao = df_gestao.sort_values("_venc_sort", ascending=False)
            
            # Reportar duplicatas ANTES do drop (para transparência)
            dupes_count = df_gestao.duplicated(subset=merge_keys).sum()
            if dupes_count > 0:
                logger.warning("Base de Gestão contém %d faturas duplicadas para a mesma UC+Período. Elas serão marcadas como 'Conta dupla'.", dupes_count)

            # Marcar duplicatas ANTES do drop para permitir detecção de 'Conta dupla'
            df_gestao["_is_duplicate_gestao"] = df_gestao.duplicated(subset=merge_keys, keep=False)
            df_gestao = df_gestao.drop_duplicates(subset=merge_keys, keep="first")
            
            if "_venc_sort" in df_gestao.columns:
                df_gestao = df_gestao.drop(columns=["_venc_sort"])
            
            logger.info("Realizando merge (cruzamento) usando chaves %s (%d registros únicos na Gestão)...", merge_keys, len(df_gestao))
            _original_len = len(df_consolidado)  # capture antes do merge
            
            # Segurança: Se a coluna de conta já existir na base de Balanço (vazia), dropar antes do merge para evitar _x/_y
            from logic.core.mapping import ACCOUNT_NUMBER_COL
            if ACCOUNT_NUMBER_COL in df_consolidado.columns:
                df_consolidado.drop(columns=[ACCOUNT_NUMBER_COL], inplace=True)
                
            df_consolidado = pd.merge(df_consolidado, df_gestao, on=merge_keys, how="left")

            # 6. Guarda de Segurança: Expansão de linhas (duplicatas na Gestão)
            # Se o merge gerar mais do que o dobro de linhas, abortamos por segurança contra sujeira massiva.
            if len(df_consolidado) > 2 * _original_len and _original_len > 0:
                raise ValueError(f"Merge abortado: expansão crítica de linhas detectada ({len(df_consolidado)} vs {_original_len})")

            # Validação pós-merge: Apenas informativa agora, pois 'Conta dupla' é uma possibilidade tratada
            n_sem_vencimento = df_consolidado["Vencimento"].isna().sum() if "Vencimento" in df_consolidado.columns else 0
            n_linhas_extras = len(df_consolidado) - _original_len

            logger.info(
                "Pós-merge: %d registros | %d sem Vencimento | %d linhas extras (duplicatas)",
                len(df_consolidado), n_sem_vencimento, n_linhas_extras
            )

            # 6. Removido Fallback por UC (evitar mistura de referências)
            # O merge agora é estritamente por UC + Período.

            # 7. Consolidação final de nomes de colunas
            if "Status Pos-Faturamento_gestao" in df_consolidado.columns and "Status Pos-Faturamento" in df_consolidado.columns:
                df_consolidado["Status Pos-Faturamento"] = df_consolidado["Status Pos-Faturamento_gestao"].combine_first(df_consolidado["Status Pos-Faturamento"])
                df_consolidado.drop(columns=["Status Pos-Faturamento_gestao"], inplace=True)
            elif "Status Pos-Faturamento_gestao" in df_consolidado.columns:
                df_consolidado.rename(columns={"Status Pos-Faturamento_gestao": "Status Pos-Faturamento"}, inplace=True)
            
            # 7.1 Limpeza específica da coluna de Conta (remover .0 e forçar string)
            from logic.core.mapping import ACCOUNT_NUMBER_COL
            if ACCOUNT_NUMBER_COL in df_consolidado.columns:
                df_consolidado[ACCOUNT_NUMBER_COL] = df_consolidado[ACCOUNT_NUMBER_COL].apply(
                    lambda x: str(int(float(x))) if pd.notna(x) and str(x).endswith('.0') else str(x) if pd.notna(x) else pd.NA
                )
                
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
    if _save_parquet_safe(df_consolidado, PARQUET_FILE):
        return True, report
    else:
        return False, report


def _save_parquet_safe(df: pd.DataFrame, filepath: str) -> bool:
    """Salva DataFrame em Parquet tentando pyarrow primeiro, fallback para fastparquet."""
    for engine in ["pyarrow", "fastparquet"]:
        try:
            df.to_parquet(filepath, engine=engine, index=False)
            logger.info("Parquet salvo com engine='%s': %s", engine, filepath)
            return True
        except ImportError:
            logger.debug("Engine '%s' não disponível, tentando próximo...", engine)
            continue
        except Exception as e:
            logger.warning("Falha ao salvar com engine='%s': %s", engine, e)
            continue
    logger.error("Nenhuma engine de parquet disponível para salvar %s", filepath)
    return False


def _read_parquet_safe(filepath: str) -> pd.DataFrame:
    """Lê Parquet tentando pyarrow primeiro, fallback para fastparquet."""
    for engine in ["pyarrow", "fastparquet"]:
        try:
            return pd.read_parquet(filepath, engine=engine)
        except ImportError:
            continue
        except Exception as e:
            logger.warning("Falha ao ler com engine='%s': %s", engine, e)
            continue
    raise FileNotFoundError(f"Não foi possível ler {filepath} com nenhuma engine disponível (pyarrow/fastparquet)")


def get_parquet_dataframe() -> pd.DataFrame:
    """Lê e retorna o DataFrame cacheado. Levanta FileNotFoundError se não existir."""
    if not os.path.exists(PARQUET_FILE):
        raise FileNotFoundError(f"Cache {PARQUET_FILE} não encontrado.")
    return _read_parquet_safe(PARQUET_FILE)


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
