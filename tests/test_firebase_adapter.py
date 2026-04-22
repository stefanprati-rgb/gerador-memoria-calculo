import pytest
import sys
from unittest.mock import MagicMock

# Mock firebase_admin antes de importar o módulo
sys.modules['firebase_admin'] = MagicMock()
sys.modules['firebase_admin.credentials'] = MagicMock()
sys.modules['firebase_admin.storage'] = MagicMock()
sys.modules['firebase_admin.firestore'] = MagicMock()

import firebase_admin
firebase_admin._apps = {}

from logic.adapters.firebase_adapter import FirebaseAdapter, FirebaseAdapterError

def test_firebase_missing_bucket():
    # Deve falhar imediatamente sem bucket
    with pytest.raises(FirebaseAdapterError, match="FIREBASE_STORAGE_BUCKET não configurado"):
        FirebaseAdapter(credentials_path="cred.json", bucket_name=None)

def test_firebase_missing_credentials():
    # Bucket existe, mas credentials_path aponta para um arquivo inexistente
    # A inicialização vai tentar ler e eventualmente falhar na credencial nula
    with pytest.raises(FirebaseAdapterError, match="Nenhuma credencial Firebase encontrada"):
        FirebaseAdapter(credentials_path="/fake/path/doesnt_exist.json", bucket_name="dummy_bucket")
