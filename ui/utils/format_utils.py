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

def generate_suggested_filename(name: str, clients: list, periods: list) -> str:
    """Gera uma sugestão de nome de arquivo baseada nas seleções."""
    # 1. Base Name
    if name and not name.startswith("Grupo_"):
        base = name
    elif len(clients) == 1:
        base = clients[0]
    elif len(clients) > 1:
        base = f"{clients[0]}_e_outros"
    else:
        base = "Memoria_Calculo"
    
    base = sanitize_filename(base)

    # 2. Periods
    if not periods:
        period_part = ""
    elif len(periods) == 1:
        period_part = format_period_label(periods[0]).replace("/", "_")
    elif len(periods) > 2:
        # Se muitos meses, pegar o primeiro e o último (assumindo que estão ordenados ou são sequenciais)
        # Ordenação básica por string deve funcionar para YYYY-MM
        sorted_p = sorted(periods)
        start = format_period_label(sorted_p[0]).replace("/", "_")
        end = format_period_label(sorted_p[-1]).replace("/", "_")
        period_part = f"{start}_a_{end}"
    else:
        # 2 meses
        period_part = "_".join([format_period_label(p).replace("/", "_") for p in sorted(periods)])

    # 3. Timestamp
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    
    parts = [base]
    if period_part:
        parts.append(period_part)
    parts.append(now)
    
    return "_".join(parts)
