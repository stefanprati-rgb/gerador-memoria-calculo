import pandas as pd
import re
import warnings
from typing import Any, Optional

def parse_full_date(val: Any) -> Optional[pd.Timestamp]:
    """
    Realiza o parsing robusto de uma data completa.
    Tenta formatos ISO primeiro, depois formatos brasileiros.
    Retorna pd.Timestamp ou None.
    """
    if pd.isna(val):
        return None
        
    val_str = str(val).strip().lower()
    if val_str in ["", "-", "--", "n/a", "não", "none", "nan", "nat", "não disponível"]:
        return None

    if isinstance(val, pd.Timestamp):
        return val

    # Restaura a string original com case correto para parsing
    val_str = str(val).strip()

    # 1. ISO Format strict check (YYYY-MM-DD...)
    if re.match(r"^\d{4}-\d{2}-\d{2}", val_str):
        try:
            return pd.to_datetime(val_str, format="ISO8601", errors='raise')
        except (ValueError, TypeError):
            # Se falhar o ISO8601 strict, deixa tentar o fallback genérico sem dayfirst
            try:
                return pd.to_datetime(val_str, errors='raise')
            except (ValueError, TypeError):
                pass

    # 2. Formato Brasileiro ou Fallback genérico com dayfirst=True
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=UserWarning, message='.*Parsing dates in.*')
        try:
            ts = pd.to_datetime(val, dayfirst=True, errors='raise')
            if pd.isna(ts):
                return None
            return ts
        except (ValueError, TypeError, Exception):
            return None


def parse_reference_period(val: Any) -> Optional[str]:
    """
    Lida com períodos de referência que chegam como MM/YYYY, MM-YYYY, ou YYYY-MM.
    Retorna sempre no formato padronizado interno MM-YYYY.
    Se não for possível determinar, retorna None.
    """
    if pd.isna(val):
        return None
        
    val_str = str(val).strip().lower()
    if val_str in ["", "-", "--", "n/a", "não", "none", "nan", "nat", "não disponível"]:
        return None

    val_str = str(val).strip()

    # Formatos textuais explícitos de referência
    if re.match(r"^\d{4}-\d{2}$", val_str): # YYYY-MM
        return f"{val_str[5:7]}-{val_str[0:4]}"
        
    if re.match(r"^\d{2}-\d{4}$", val_str): # MM-YYYY
        return val_str
        
    if re.match(r"^\d{2}/\d{4}$", val_str): # MM/YYYY
        return val_str.replace("/", "-")

    # Se calhar de ser uma data ISO truncada (YYYY-MM-DD...)
    iso_match = re.match(r'^(\d{4})-(\d{1,2})-\d{1,2}', val_str)
    if iso_match:
        year = iso_match.group(1)
        month = iso_match.group(2).zfill(2)
        return f"{month}-{year}"

    # Como último recurso, tenta fazer parse genérico de data e extrair mês/ano
    ts = parse_full_date(val)
    if ts is not None:
        return ts.strftime("%m-%Y")

    return None


def format_full_date(val: Any, default: str = "Não disponível") -> str:
    """
    Recebe um valor de data e devolve a string formatada em DD-MM-YYYY,
    ou o valor default se for inválida/vazia.
    """
    if isinstance(val, str) and val.strip().lower() == "não disponível":
        return default

    ts = parse_full_date(val)
    if ts is not None:
        return ts.strftime("%d-%m-%Y")
    return default


def format_reference_period(val: Any, default: str = "Não disponível") -> str:
    """
    Recebe um valor de competência/referência e devolve a string formatada em MM/YYYY,
    ou o valor default se for inválida/vazia.
    (Note a barra '/' no retorno em vez do traço '-')
    """
    if isinstance(val, str) and val.strip().lower() == "não disponível":
        return default

    parsed = parse_reference_period(val)
    if parsed:
        return parsed.replace("-", "/")
    return default
