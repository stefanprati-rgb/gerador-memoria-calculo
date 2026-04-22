"""
Adaptador para comunicação com o Firebase Cloud Storage.
Permite inicializar o app, verificar metadata, fazer upload e download de arquivos.
"""

import os
import firebase_admin
from firebase_admin import credentials, storage, firestore
from datetime import datetime, timezone
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class FirebaseAdapterError(Exception):
    """Exceção customizada para erros operacionais do Firebase."""
    pass

class FirebaseAdapter:
    """Cliente para operações no Firebase Storage e Firestore."""

    def __init__(self, credentials_path: str, bucket_name: str):
        if not bucket_name:
            raise FirebaseAdapterError("FIREBASE_STORAGE_BUCKET não configurado. Impossível iniciar FirebaseAdapter.")
            
        self.credentials_path = credentials_path
        self.bucket_name = bucket_name
        self._app = self._initialize_app()
        self._db = self._get_db()

    def _initialize_app(self):
        """
        Inicializa o app do Firebase com prioridade:
        1. Dicionário direto (dict)
        2. Arquivo Local (string + exists)
        3. Streamlit Secrets (st.secrets["firebase"])
        """
        try:
            if not firebase_admin._apps:
                import streamlit as st
                cred = None
                source = ""

                # 1. Caso seja um dicionário direto
                if isinstance(self.credentials_path, dict):
                    cred_dict = self.credentials_path
                    if "private_key" in cred_dict:
                        cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                    cred = credentials.Certificate(cred_dict)
                    source = "Dicionário Direto"

                # 2. Caso seja uma string (Caminho de Arquivo)
                elif isinstance(self.credentials_path, str) and self.credentials_path.strip():
                    abs_path = os.path.abspath(self.credentials_path)
                    if os.path.exists(abs_path):
                        cred = credentials.Certificate(abs_path)
                        source = f"Arquivo Local ({abs_path})"
                
                # 3. Fallback para st.secrets (caso path não exista, seja nulo ou vazio)
                if not cred:
                    try:
                        if "firebase" in st.secrets:
                            cred_dict = dict(st.secrets["firebase"])
                            if "private_key" in cred_dict:
                                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                            cred = credentials.Certificate(cred_dict)
                            source = "Streamlit Secrets"
                        elif "firebase_credentials" in st.secrets:
                            cred_dict = dict(st.secrets["firebase_credentials"])
                            if "private_key" in cred_dict:
                                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                            cred = credentials.Certificate(cred_dict)
                            source = "Streamlit Secrets (legacy key)"
                    except Exception:
                        pass

                if not cred:
                    raise FirebaseAdapterError("Nenhuma credencial Firebase encontrada (Dict/Arquivo/Secrets não resolvidos).")

                app = firebase_admin.initialize_app(cred, {
                    'storageBucket': self.bucket_name
                })
                logger.info("Firebase | App inicializado com sucesso via %s.", source)
                return app
            else:
                return firebase_admin.get_app()
        except FirebaseAdapterError:
            raise
        except Exception as e:
            raise FirebaseAdapterError(f"Falha inesperada ao inicializar credenciais Firebase: {e}")

    def test_connection(self):
        """Tenta listar as coleções do Firestore para validar conexão. Levanta erro se falhar."""
        try:
            db = self._get_db()
            _ = list(db.collections(timeout=5))
            return True
        except Exception as e:
            raise FirebaseAdapterError(f"Firestore indisponível ou timeout na conexão: {e}")

    def _get_bucket(self):
        if not self._app:
            raise FirebaseAdapterError("App Firebase não inicializado corretamente. Bucket inacessível.")
        try:
            return storage.bucket(app=self._app)
        except Exception as e:
            raise FirebaseAdapterError(f"Erro ao acessar Storage Bucket '{self.bucket_name}': {e}")

    def _get_db(self):
        """Inicializa e retorna o cliente do Firestore."""
        if not self._app:
            raise FirebaseAdapterError("App Firebase não inicializado. Banco de dados inacessível.")
        try:
            return firestore.client(app=self._app)
        except Exception as e:
            raise FirebaseAdapterError(f"Erro ao obter cliente Firestore: {e}")

    def get_file_updated_time(self, blob_name: str) -> Optional[datetime]:
        """Retorna a data de atualização do arquivo no Storage, ou None se não existir."""
        bucket = self._get_bucket()
        blob = bucket.blob(blob_name)
        if not blob.exists():
            return None
        blob.reload()
        return blob.updated

    def download_file(self, blob_name: str, dest_path: str) -> bool:
        """Baixa um arquivo do Storage para o disco local. Retorna True se sucesso."""
        bucket = self._get_bucket()
        blob = bucket.blob(blob_name)
        if not blob.exists():
            raise FirebaseAdapterError(f"Arquivo '{blob_name}' não existe no bucket '{self.bucket_name}'.")
            
        try:
            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
            blob.download_to_filename(dest_path)
            logger.info("Arquivo baixado com sucesso: %s -> %s", blob_name, dest_path)
            return True
        except Exception as e:
            raise FirebaseAdapterError(f"Erro no download do arquivo '{blob_name}': {e}")

    def upload_file(self, file_path_or_bytes: str | bytes, blob_name: str) -> bool:
        """
        Faz o upload de um arquivo para o Storage.
        Pode receber um caminho local ou os bytes do arquivo em si.
        """
        bucket = self._get_bucket()
        blob = bucket.blob(blob_name)
        try:
            if isinstance(file_path_or_bytes, str):
                if not os.path.exists(file_path_or_bytes):
                    raise FirebaseAdapterError(f"Arquivo local para upload não encontrado: {file_path_or_bytes}")
                blob.upload_from_filename(file_path_or_bytes)
            else:
                blob.upload_from_string(file_path_or_bytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
            logger.info("Arquivo enviado com sucesso para: %s", blob_name)
            return True
        except Exception as e:
            raise FirebaseAdapterError(f"Erro ao fazer upload do arquivo para '{blob_name}': {e}")
