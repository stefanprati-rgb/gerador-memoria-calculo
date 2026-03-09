import hashlib
import re
import datetime

def safe_key(text: str) -> str:
    """Gera uma chave segura para o Streamlit baseada em hash MD5."""
    if not text:
        text = ""
    return hashlib.md5(str(text).encode('utf-8')).hexdigest()

def sanitize_filename(name: str) -> str:
    """Sanitiza nomes de arquivos para evitar caracteres inválidos."""
    if not name:
        return "memoria_calculo"
    
    # Allow only a-z A-Z 0-9 _ -
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(name))
    
    # Collapse duplicate _
    safe_name = re.sub(r'_+', '_', safe_name)
    
    # Strip leading/trailing _
    safe_name = safe_name.strip('_')
    
    if not safe_name:
        return "memoria_calculo"
    return safe_name

def format_period_label(raw_period: str) -> str:
    """Formata '2025-12-01 00:00:00' para '2025/Dez'."""
    try:
        dt = datetime.datetime.fromisoformat(str(raw_period).split(" ")[0])
        meses = {
            1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
            5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
            9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
        }
        return f"{dt.year}/{meses[dt.month]}"
    except Exception:
        return str(raw_period)

def format_number(val: int) -> str:
    """Formata números com ponto como separador de milhar."""
    return f"{val:,}".replace(",", ".")
