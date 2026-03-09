import unicodedata
import re
from typing import Dict, List

def normalize_string(text: str) -> str:
    """Normaliza string para busca: minúsculas, sem acentos e sem pontuação."""
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    
    # Remove acentos
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    # Transforma em minúsculas
    text = text.lower()
    # Substitui caracteres não-alfanuméricos por espaço
    text = re.sub(r'[^a-z0-9]', ' ', text)
    # Remove espaços contínuos
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def build_search_index(values: List[str]) -> Dict[str, str]:
    """Cria um índice de strings originais para strings normalizadas."""
    return {str(val): normalize_string(val) for val in values}

def filter_values(search_term: str, index: Dict[str, str]) -> List[str]:
    """Filtra valores com base no índice de busca."""
    if not search_term:
        return list(index.keys())
    
    norm_search = normalize_string(search_term)
    return [orig for orig, norm in index.items() if norm_search in norm]
