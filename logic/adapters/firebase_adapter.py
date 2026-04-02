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

class FirebaseAdapter:
    """Cliente para operações no Firebase Storage e Firestore."""

    def __init__(self, credentials_path: str, bucket_name: str):
        self.credentials_path = credentials_path
        self.bucket_name = bucket_name
        self._app = self._initialize_app()
        # Inicializa o banco de dados no momento da criação
        self._db = self._get_db()

    def _initialize_app(self):
        """
        Inicializa o app do Firebase com prioridade:
        1. Dicionário direto (dict)
        2. Arquivo Local (string + exists)
        3. Streamlit Secrets (st.secrets["firebase"])
        """
        # --- Backup do método anterior ---
        # def _prev_initialize_app(self):
        #     if not firebase_admin._apps:
        #         import streamlit as st
        #         if "firebase_credentials" in st.secrets:
        #             cred_dict = dict(st.secrets["firebase_credentials"])
        #             if "private_key" in cred_dict: cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
        #             cred = credentials.Certificate(cred_dict)
        #         else:
        #             abs_path = os.path.abspath(self.credentials_path)
        #             if not os.path.exists(abs_path): return None
        #             cred = credentials.Certificate(abs_path)
        #         return firebase_admin.initialize_app(cred, {'storageBucket': self.bucket_name})
        # ---------------------------------

        try:
            if not firebase_admin._apps:
                import streamlit as st
                cred = None
                source = ""

                # 1. Caso seja um dicionário direto
                if isinstance(self.credentials_path, dict):
                    logger.info("Firebase | Inicializando via Dicionário de credenciais fornecido.")
                    cred_dict = self.credentials_path
                    if "private_key" in cred_dict:
                        cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                    cred = credentials.Certificate(cred_dict)
                    source = "Dicionário Direto"

                # 2. Caso seja uma string (Caminho de Arquivo)
                elif isinstance(self.credentials_path, str):
                    abs_path = os.path.abspath(self.credentials_path)
                    if os.path.exists(abs_path):
                        logger.info("Firebase | Inicializando via Arquivo Local: %s", abs_path)
                        cred = credentials.Certificate(abs_path)
                        source = f"Arquivo Local ({abs_path})"
                    
                    # 3. Fallback para st.secrets se o arquivo não existir
                    elif "firebase" in st.secrets:
                        logger.info("Firebase | Arquivo não encontrado. Usando st.secrets['firebase'].")
                        cred_dict = dict(st.secrets["firebase"])
                        if "private_key" in cred_dict:
                            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                        cred = credentials.Certificate(cred_dict)
                        source = "Streamlit Secrets"
                    
                    # 3.1 Fallback secundário (compatibilidade)
                    elif "firebase_credentials" in st.secrets:
                        logger.info("Firebase | Arquivo não encontrado. Usando st.secrets['firebase_credentials'].")
                        cred_dict = dict(st.secrets["firebase_credentials"])
                        if "private_key" in cred_dict:
                            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                        cred = credentials.Certificate(cred_dict)
                        source = "Streamlit Secrets (legacy key)"

                if not cred:
                    logger.error("ERRO CRÍTICO | Nenhuma credencial Firebase encontrada (Dict/Arquivo/Secrets).")
                    return None

                app = firebase_admin.initialize_app(cred, {
                    'storageBucket': self.bucket_name
                })
                logger.info("Firebase | App inicializado com sucesso via %s.", source)
                return app
            else:
                return firebase_admin.get_app()
        except Exception as e:
            logger.error("Falha ao inicializar Firebase: %s", e)
            return None

    def test_connection(self):
        """Tenta listar as coleções do Firestore para validar conexão silênciosamente."""
        try:
            db = self._get_db()
            if not db:
                logger.error("Falha silenciosa: Firestore indisponível.")
                return False
            
            # Lista apenas a primeira para teste rápido
            _ = list(db.collections(timeout=5))
            logger.info("Conexão Firestore OK")
            return True
        except Exception as e:
            logger.error("Falha no teste de conexão Firestore: %s", e)
            return False

    def _get_bucket(self):
        if not self._app:
            return None
        return storage.bucket(app=self._app)

    def _get_db(self):
        """Inicializa e retorna o cliente do Firestore."""
        if not self._app:
            logger.error("ERROR | App Firebase não inicializado. Verifique as credenciais.")
            return None
        try:
            return firestore.client(app=self._app)
        except Exception as e:
            logger.error("Erro ao obter cliente Firestore: %s", e)
            return None

    def get_file_updated_time(self, blob_name: str) -> Optional[datetime]:
        """Retorna a data de atualização do arquivo no Storage, ou None se não existir."""
        bucket = self._get_bucket()
        if not bucket:
            return None
            
        blob = bucket.blob(blob_name)
        if not blob.exists():
            return None
            
        blob.reload()  # Força pegar os metadados mais recentes
        return blob.updated  # Retorna datetime com timezone

    def download_file(self, blob_name: str, dest_path: str) -> bool:
        """Baixa um arquivo do Storage para o disco local. Retorna True se sucesso."""
        bucket = self._get_bucket()
        if not bucket:
            logger.error("Bucket não inicializado para download.")
            return False
            
        blob = bucket.blob(blob_name)
        if not blob.exists():
            logger.warning("Arquivo %s não existe no bucket.", blob_name)
            return False
            
        try:
            # Garante que a pasta de destino existe
            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
            blob.download_to_filename(dest_path)
            logger.info("Arquivo baixado com sucesso: %s -> %s", blob_name, dest_path)
            return True
        except Exception as e:
            logger.error("Erro ao baixar %s: %s", blob_name, e)
            return False

    def upload_file(self, file_path_or_bytes: str | bytes, blob_name: str) -> bool:
        """
        Faz o upload de um arquivo para o Storage.
        Pode receber um caminho local ou os bytes do arquivo em si.
        """
        bucket = self._get_bucket()
        if not bucket:
            logger.error("Bucket não inicializado para upload.")
            return False
            
        blob = bucket.blob(blob_name)
        try:
            if isinstance(file_path_or_bytes, str):
                if not os.path.exists(file_path_or_bytes):
                    logger.error("Arquivo local não encontrado: %s", file_path_or_bytes)
                    return False
                blob.upload_from_filename(file_path_or_bytes)
            else:
                blob.upload_from_string(file_path_or_bytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
            logger.info("Arquivo enviado com sucesso para: %s", blob_name)
            return True
        except Exception as e:
            logger.error("Erro ao enviar arquivo para %s: %s", blob_name, e)
            return False
