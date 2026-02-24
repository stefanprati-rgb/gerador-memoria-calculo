"""
Configuração centralizada de logging para o projeto.
"""

import logging
import sys


def setup_logging(level: str = "INFO"):
    """
    Configura o logging para todo o projeto.
    
    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,  # Garante que a configuração é aplicada mesmo que já exista uma
    )
    
    # Silenciar logs verbosos de libs externas
    logging.getLogger("streamlit").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
