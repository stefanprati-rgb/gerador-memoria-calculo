"""
Serviço responsável por sincronizar as bases de dados do Firebase Cloud Storage,
cruzar as informações (Merge) e gerar o cache local em Parquet.
"""
import os
import logging
import pandas as pd
from datetime import datetime
from logic.adapters.firebase_adapter import FirebaseAdapter
from logic.adapters.excel_adapter import BaseExcelReader
from config.settings import settings

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join("data", "cache")
PARQUET_FILE = os.path.join(CACHE_DIR, "base_consolidada.parquet")

BALANCO_REMOTE = "bases/Balanco_Energetico_Raizen.xlsm"
GESTAO_REMOTE = "bases/gd_gestao_cobranca.xlsx"

BALANCO_LOCAL = os.path.join(CACHE_DIR, "Balanco_Energetico.xlsm")
GESTAO_LOCAL = os.path.join(CACHE_DIR, "gd_gestao.xlsx")

def build_consolidated_cache(firebase_client: FirebaseAdapter) -> bool:
    """
    Baixa as planilhas do Firebase (se necessário), faz o merge e salva em Parquet.
    Retorna True se sucesso.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    logger.info("Verificando atualizações no Firebase...")
    
    # Em um cenário real super otimizado, faríamos check da data de modificação
    # Aqui vamos baixar as versões mais recentes sempre que chamado (pois o admin clicou no botão)
    
    success_balanco = firebase_client.download_file(BALANCO_REMOTE, BALANCO_LOCAL)
    success_gestao = firebase_client.download_file(GESTAO_REMOTE, GESTAO_LOCAL)
    
    if not success_balanco:
        logger.error("Falha ao obter Balanço Energético do Firebase.")
        return False
        
    logger.info("Iniciando leitura do Balanço Energético...")
    try:
        reader_balanco = BaseExcelReader(BALANCO_LOCAL, sheet_name=settings.base_sheet_name)
        df_balanco = reader_balanco.df
    except Exception as e:
        logger.error("Erro ao ler Balanço Energético local: %s", e)
        return False
        
    df_consolidado = df_balanco.copy()
    
    if success_gestao:
        logger.info("Lendo base de Gestão para enriquecimento (Vencimento e Status)...")
        try:
            # Tenta ler as colunas de cruzamento da base gd_gestao
            # Assumimos que a chave primária de cruzamento é 'Instalação' (UC) ou 'CNPJ/CPF'
            # Vamos usar Instalação -> No. UC
            cols_to_use = ["Instalação", "Vencimento", "Status"]
            
            # Read all headers first to avoid KeyError if they changed
            gestao_headers = pd.read_excel(GESTAO_LOCAL, nrows=0).columns.tolist()
            
            # Buscar nome exato ignorando case/strip
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
                
                # Renomear para bater com o Balanço
                rename_dict = {uc_col: "No. UC"}
                if venc_col: rename_dict[venc_col] = "Vencimento"
                if status_col: rename_dict[status_col] = "Status Pos-Faturamento_gestao"
                
                df_gestao.rename(columns=rename_dict, inplace=True)
                
                # Converter UC para str para o merge não falhar por tipo
                df_consolidado["No. UC"] = df_consolidado["No. UC"].astype(str).str.strip()
                df_gestao["No. UC"] = df_gestao["No. UC"].astype(str).str.strip()
                
                # Fazer o Merge
                logger.info("Realizando merge (cruzamento) de %d registros...", len(df_gestao))
                df_consolidado = pd.merge(df_consolidado, df_gestao, on="No. UC", how="left")
                
                # Resolver Status (preferir Gestão, mas manter Balanço se não tiver Gestão)
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

    # Salvar o Parquet consolidado
    try:
        df_consolidado.to_parquet(PARQUET_FILE, engine="fastparquet", index=False)
        logger.info("Cache consolidado salvo com sucesso: %s", PARQUET_FILE)
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
