import hashlib
import re
import datetime
from collections import OrderedDict
from logic.core.dates import parse_reference_period

_MONTH_ABBR = {
    1: "jan", 2: "fev", 3: "mar", 4: "abr",
    5: "mai", 6: "jun", 7: "jul", 8: "ago",
    9: "set", 10: "out", 11: "nov", 12: "dez",
}
_MONTH_ABBR_SET = set(_MONTH_ABBR.values())

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

def _parse_period_parts(raw_period: str):
    """Converte referências diversas para (ano, mês) quando possível."""
    normalized = parse_reference_period(raw_period)  # MM-YYYY
    if not normalized:
        return None
    try:
        month_str, year_str = normalized.split("-")
        month = int(month_str)
        year = int(year_str)
        if month < 1 or month > 12:
            return None
        return (year, month)
    except Exception:
        return None

def format_period_token(raw_period: str) -> str:
    """
    Formata um período para uso em nome de arquivo no padrão:
    - jan_2026
    """
    parsed = _parse_period_parts(raw_period)
    if not parsed:
        return sanitize_filename(str(raw_period).lower())
    year, month = parsed
    return f"{_MONTH_ABBR[month]}_{year}"

def format_periods_for_filename(periods: list) -> str:
    """
    Gera sufixo inteligente de períodos para nome de arquivo.
    Exemplos:
    - ['12/2025', '01/2026'] -> 'dez_2025_jan_2026'
    - ['01/2026', '02/2026'] -> 'jan_fev_2026'
    """
    parsed = []
    for p in periods:
        pp = _parse_period_parts(p)
        if pp:
            parsed.append(pp)

    if not parsed:
        return ""

    parsed = sorted(set(parsed))  # ordena e remove duplicados

    # Agrupa meses por ano preservando ordem crescente de ano.
    grouped: OrderedDict[int, list[int]] = OrderedDict()
    for year, month in parsed:
        grouped.setdefault(year, [])
        if month not in grouped[year]:
            grouped[year].append(month)

    parts = []
    if len(grouped) == 1:
        year = next(iter(grouped))
        months_part = "_".join(_MONTH_ABBR[m] for m in grouped[year])
        parts.append(f"{months_part}_{year}")
    else:
        for year, months in grouped.items():
            months_part = "_".join(_MONTH_ABBR[m] for m in months)
            parts.append(f"{months_part}_{year}")

    return "_".join(parts)

def _strip_trailing_period_signature(name: str) -> str:
    """
    Remove sufixos de período já embutidos no final do nome.
    Ex.:
    - Fortbras_nov_2025 -> Fortbras
    - Fortbras_nov_dez_2025_jan_fev_2026 -> Fortbras
    """
    safe = sanitize_filename(name)
    tokens = [t for t in safe.split("_") if t]
    if not tokens:
        return safe

    i = len(tokens) - 1
    consumed_any = False

    while i >= 0:
        tok = tokens[i]
        if re.fullmatch(r"\d{4}", tok):
            j = i - 1
            month_count = 0
            while j >= 0 and tokens[j].lower() in _MONTH_ABBR_SET:
                month_count += 1
                j -= 1

            if month_count >= 1:
                consumed_any = True
                i = j
                continue
        break

    if consumed_any:
        stripped = "_".join(tokens[: i + 1]).strip("_")
        if stripped:
            return stripped

    return safe

def build_scope_base_name(name: str, clients: list) -> str:
    """
    Define a base textual do arquivo a partir do contexto do grupo.
    Não inclui período nem timestamp.
    """
    if name and not name.startswith("Grupo_"):
        base = _strip_trailing_period_signature(name)
    elif len(clients) == 1:
        base = clients[0]
    elif len(clients) > 1:
        base = f"{clients[0]}_e_outros"
    else:
        base = "Memoria_Calculo"
    return sanitize_filename(base)

def build_zip_entry_filename(name: str, clients: list, period: str) -> str:
    """
    Gera nome interno de arquivo dentro do ZIP por período.
    Ex.: embracon_e_outros_jan_2026.xlsx
    """
    base = build_scope_base_name(name, clients)
    token = format_period_token(period)
    return f"{base}_{token}.xlsx"

def generate_suggested_filename(name: str, clients: list, periods: list) -> str:
    """Gera uma sugestão de nome de arquivo baseada nas seleções."""
    # 1. Base Name
    base = build_scope_base_name(name, clients)

    # 2. Periods
    period_part = format_periods_for_filename(periods)

    parts = [base]
    if period_part:
        parts.append(period_part)
    
    return "_".join(parts)

def build_runtime_filename(base_name: str, extension: str) -> str:
    """
    Gera nome final de arquivo com timestamp apenas no momento da geração.
    Ex.: Projeto_Alpha_jan_fev_2026_2026-04-22_1903.xlsx
    """
    safe_base = sanitize_filename(base_name)
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    ext = extension if extension.startswith(".") else f".{extension}"
    return f"{safe_base}_{now}{ext}"
