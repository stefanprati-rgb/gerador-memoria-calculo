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

            cols_to_read = []
            if uc_col: cols_to_read.append(uc_col)
            if venc_col: cols_to_read.append(venc_col)
            if status_col: cols_to_read.append(status_col)

            if uc_col and (venc_col or status_col):
                df_gestao = pd.read_excel(GESTAO_LOCAL, usecols=cols_to_read)

                rename_dict = {uc_col: "No. UC"}
                if venc_col: rename_dict[venc_col] = "Vencimento"
                if status_col: rename_dict[status_col] = "Status Pos-Faturamento_gestao"

                df_gestao.rename(columns=rename_dict, inplace=True)

                df_consolidado["No. UC"] = df_consolidado["No. UC"].astype(str).str.strip()
                df_gestao["No. UC"] = df_gestao["No. UC"].astype(str).str.strip()

                logger.info("Realizando merge (cruzamento) de %d registros...", len(df_gestao))
                df_consolidado = pd.merge(df_consolidado, df_gestao, on="No. UC", how="left")

                if "Status Pos-Faturamento_gestao" in df_consolidado.columns and "Status Pos-Faturamento" in df_consolidado.columns:
                    df_consolidado["Status Pos-Faturamento"] = df_consolidado["Status Pos-Faturamento_gestao"].combine_first(df_consolidado["Status Pos-Faturamento"])
                    df_consolidado.drop(columns=["Status Pos-Faturamento_gestao"], inplace=True)
                elif "Status Pos-Faturamento_gestao" in df_consolidado.columns:
                    df_consolidado.rename(columns={"Status Pos-Faturamento_gestao": "Status Pos-Faturamento"}, inplace=True)
            else:
                logger.warning("Colunas chaves não encontradas na Gestão: UC=%s, Vencimento=%s", uc_col, venc_col)
        except Exception as e:
            logger.warning("Falha ao ler ou cruzar base de Gestão (continuará apenas com Balanço). Erro: %s", e)
    else:
        logger.info("Base de Gestão não disponível. Seguindo sem Vencimento/Status extra.")

    # 5. Salvar o Parquet consolidado
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
