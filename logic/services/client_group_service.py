"""
Serviço para gerenciamento de grupos de clientes no Firestore.
Permite salvar listas de clientes e recuperá-los para processamento.
"""
import logging
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO FIREBASE ---
CLIENT_GROUPS_COLLECTION = "client_groups"
_adapter = None

def _get_adapter():
    """Inicialização preguiçosa (Lazy loading) do adaptador Firebase."""
    global _adapter
    if _adapter is None:
        try:
            from logic.adapters.firebase_adapter import FirebaseAdapter
            from config.settings import settings
            _adapter = FirebaseAdapter(settings.firebase_credentials_path, settings.firebase_storage_bucket)
        except Exception as e:
            logger.error("Falha ao obter adaptador Firebase no ClientGroupService: %s", e)
    return _adapter

def save_client_group(group_name: str, client_list: list) -> bool:
    """
    Salva uma lista de clientes no Firestore.
    O ID do documento é o group_name.
    """
    try:
        adapter = _get_adapter()
        db = adapter._get_db()
        if not adapter or not db:
            logger.error("Firestore não disponível para salvar grupo de clientes.")
            return False

        # Dados a serem salvos
        data = {
            "group_name": group_name,
            "clients": client_list,
            "updated_at": datetime.now()
        }

        # LGPD: Não logamos client_list por conter dados sensíveis
        logger.info("Salvando grupo de clientes '%s' no Firestore.", group_name)
        
        db.collection(CLIENT_GROUPS_COLLECTION).document(group_name).set(data)
        return True
    except Exception as e:
        logger.error("Erro ao salvar grupo de clientes '%s': %s", group_name, e)
        return False

def list_client_groups() -> List[str]:
    """
    Retorna uma lista com os nomes (IDs) de todos os grupos salvos no Firestore.
    """
    try:
        adapter = _get_adapter()
        db = adapter._get_db()
        if not adapter or not db:
            return []

        docs = db.collection(CLIENT_GROUPS_COLLECTION).list_documents()
        return [doc.id for doc in docs]
    except Exception as e:
        logger.error("Erro ao listar grupos de clientes: %s", e)
        return []

def get_clients_from_group(group_name: str) -> List[str]:
    """
    Busca o documento pelo nome e retorna a lista de strings do campo 'clients'.
    """
    try:
        adapter = _get_adapter()
        db = adapter._get_db()
        if not adapter or not db:
            return []

        doc_ref = db.collection(CLIENT_GROUPS_COLLECTION).document(group_name)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            return data.get("clients", [])
        
        logger.warning("Grupo de clientes '%s' não encontrado.", group_name)
        return []
    except Exception as e:
        logger.error("Erro ao buscar clientes do grupo '%s': %s", group_name, e)
        return []
