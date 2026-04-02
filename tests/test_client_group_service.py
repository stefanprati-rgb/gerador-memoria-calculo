import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import sys
import os

# Ensure the project root is in sys.path for testing
sys.path.append(os.getcwd())

def test_save_client_group_calls_firestore_correctly():
    """Verifica se save_client_group chama o Firestore com os dados corretos."""
    with patch("logic.services.client_group_service._get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_db = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        mock_adapter._get_db.return_value = mock_db
        
        from logic.services.client_group_service import save_client_group
        
        group_name = "Test Group"
        client_list = ["Client A", "Client B"]
        
        save_client_group(group_name, client_list)
        
        mock_db.collection.assert_called_with("client_groups")
        mock_db.collection().document.assert_called_with(group_name)
        
        # Verifica os dados enviados para o Firestore
        args, _ = mock_db.collection().document().set.call_args
        data = args[0]
        assert data["group_name"] == group_name
        assert data["clients"] == client_list
        assert isinstance(data["updated_at"], datetime)

def test_list_client_groups_returns_names():
    """Verifica se list_client_groups retorna a lista de nomes dos grupos."""
    with patch("logic.services.client_group_service._get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_db = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        mock_adapter._get_db.return_value = mock_db
        
        # Mocking list_documents()
        mock_doc1 = MagicMock()
        mock_doc1.id = "Group A"
        mock_doc2 = MagicMock()
        mock_doc2.id = "Group B"
        mock_db.collection().list_documents.return_value = [mock_doc1, mock_doc2]
        
        from logic.services.client_group_service import list_client_groups
        
        groups = list_client_groups()
        assert groups == ["Group A", "Group B"]

def test_get_clients_from_group_returns_list():
    """Verifica se get_clients_from_group retorna a lista de clientes correta."""
    with patch("logic.services.client_group_service._get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_db = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        mock_adapter._get_db.return_value = mock_db
        
        # Mocking doc.get()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"clients": ["C1", "C2"]}
        mock_db.collection().document().get.return_value = mock_doc
        
        from logic.services.client_group_service import get_clients_from_group
        
        clients = get_clients_from_group("Group X")
        assert clients == ["C1", "C2"]
