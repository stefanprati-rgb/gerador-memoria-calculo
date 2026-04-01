"""
Serviço de persistência para mapeamentos extras (enriquecimento de dados).
Migrado para Google Cloud Firestore via FirebaseAdapter.
Suporta migração automática de JSON local para a nuvem.
"""
import os
import json
import pandas as pd
import logging
from typing import List, Optional
from logic.core.mapping import ENRICHMENT_KEY

logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO FIREBASE ---
COLLECTION_NAME = "uc_mappings"
_adapter = None

def _get_adapter():
    """Inicialização preguiçosa (Lazy loading) do adaptador Firebase."""
    global _adapter
    if _adapter is None:
        try:
            from logic.adapters.firebase_adapter import FirebaseAdapter
            from config.settings import settings
            _adapter = FirebaseAdapter(settings.firebase_credentials_path, settings.firebase_storage_bucket)
            if not _adapter._app:
                logger.warning("Firebase não inicializado no Enrichment Service. Fallback para Local? (Não implementado por design Nuvem First)")
        except Exception as e:
            logger.error("Falha ao obter adaptador Firebase: %s", e)
    return _adapter

# --- LEGACY LOCAL PATH (PARA MIGRAÇÃO) ---
DATA_PATH = os.path.join(os.getcwd(), "data", "mappings")

def save_mapping(profile_name: str, df: pd.DataFrame) -> bool:
    """
    Salva um DataFrame de de-para no Firestore.
    O 'profile_name' é o ID do documento.
    """
    try:
        if df.empty:
            logger.warning("Tentativa de salvar mapping vazio para o perfil '%s'.", profile_name)
            return False
            
        adapter = _get_adapter()
        db = adapter._get_db()
        if not adapter or not db:
            logger.error("Firestore não disponível para salvar mapping.")
            return False
            
        if ENRICHMENT_KEY not in df.columns:
            logger.error("A coluna chave '%s' não encontrada no DataFrame.", ENRICHMENT_KEY)
            return False
            
        # Converter DataFrame para dicionário: {uc: {col: val}}
        mapping_dict = df.set_index(ENRICHMENT_KEY).to_dict(orient="index")
        
        # Salvar no Firestore
        doc_ref = adapter._db.collection(COLLECTION_NAME).document(profile_name)
        doc_ref.set(mapping_dict)
            
        logger.info("Mapeamento '%s' salvo com sucesso no Firestore.", profile_name)
        return True
    except Exception as e:
        logger.exception("Erro ao salvar mapeamento '%s' no Firestore: %s", profile_name, str(e))
        return False

def load_mapping(profile_name: str) -> Optional[pd.DataFrame]:
    """
    Carrega o mapeamento do Firestore. 
    Se não houver rede ou o Firestore falhar, faz fallback automático para o arquivo local se existir.
    """
    adapter = _get_adapter()
    firestore_failed = False
    
    # 1. Tentar carregar do Firestore
    try:
        db = adapter._get_db()
        if adapter and db:
            doc_ref = db.collection(COLLECTION_NAME).document(profile_name)
            doc = doc_ref.get()
            if doc.exists:
                return _dict_to_df(doc.to_dict())
            else:
                 logger.warning("Perfil '%s' não encontrado no Firestore.", profile_name)
        else:
             firestore_failed = True
    except Exception as e:
        logger.error("Erro ao carregar do Firestore (Perfil %s): %s", profile_name, e)
        firestore_failed = True
            
    # 2. Se falhar Firestore ou não existir doc, verificar Migração/Fallback Local
    local_df = _load_local_legacy(profile_name)
    
    if local_df is not None:
        # Se Firestore estava vivo mas o doc não existia, tenta subir para próximo uso
        if not firestore_failed:
             logger.info("Sincronizando perfil local '%s' com a nuvem...", profile_name)
             save_mapping(profile_name, local_df)
        
        logger.info("Usando versão local do perfil '%s' (Fallback ativado).", profile_name)
        return local_df
    
    return None

def list_profiles() -> List[str]:
    """
    Retorna uma lista contendo os IDs de todos os perfis configurados.
    Combina documentos do Firestore com arquivos JSON locais para garantir visibilidade total.
    """
    profiles = set()
    
    # 1. Buscar do Firestore
    try:
        adapter = _get_adapter()
        db = adapter._get_db()
        if adapter and db:
            docs = db.collection(COLLECTION_NAME).list_documents()
            for doc in docs:
                profiles.add(doc.id)
    except Exception as e:
        logger.error("Erro ao listar perfis no Firestore: %s", str(e))
    
    # 2. Buscar do Local (Fallback/Sincronia)
    try:
        if os.path.exists(DATA_PATH):
            for filename in os.listdir(DATA_PATH):
                if filename.endswith(".json"):
                    profiles.add(filename.replace(".json", ""))
    except Exception as e:
        logger.error("Erro ao listar perfis locais: %s", str(e))
        
    return sorted(list(profiles))

def delete_profile(profile_name: str) -> bool:
    """
    Exclui um perfil do Firestore e também libera o backup local se existir.
    """
    try:
        # 1. Excluir do Firestore
        adapter = _get_adapter()
        db = adapter._get_db()
        if adapter and db:
             doc_ref = db.collection(COLLECTION_NAME).document(profile_name)
             if doc_ref.get().exists:
                  doc_ref.delete()
                  logger.info("Perfil '%s' excluído do Firestore.", profile_name)
        
        # 2. Excluir do Local (Faxina)
        clean_name = profile_name.replace(".json", "").strip()
        file_path = os.path.join(DATA_PATH, f"{clean_name}.json")
        if os.path.exists(file_path):
             os.remove(file_path)
             logger.info("Faxina Local: Arquivo '%s' removido.", file_path)
             
        return True
    except Exception as e:
        logger.error("Erro ao excluir perfil '%s': %s", profile_name, str(e))
        return False

# --- HELPERS INTERNOS ---

def _dict_to_df(mapping_dict: dict) -> pd.DataFrame:
    """Converte o dicionário do Firestore/JSON de volta para DataFrame do pandas."""
    if not mapping_dict:
        return pd.DataFrame(columns=[ENRICHMENT_KEY])
    
    df = pd.DataFrame.from_dict(mapping_dict, orient="index").reset_index()
    df.rename(columns={"index": ENRICHMENT_KEY}, inplace=True)
    return df

def _load_local_legacy(profile_name: str) -> Optional[pd.DataFrame]:
    """Tenta carregar um arquivo JSON legado do disco local."""
    try:
        clean_name = profile_name.replace(".json", "").strip()
        file_path = os.path.join(DATA_PATH, f"{clean_name}.json")
        
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, "r", encoding="utf-8") as f:
            mapping_dict = json.load(f)
            
        return _dict_to_df(mapping_dict)
    except Exception:
        return None
