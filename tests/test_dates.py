import pytest
import pandas as pd
from logic.core.dates import (
    parse_full_date,
    parse_reference_period,
    format_full_date,
    format_reference_period,
)

def test_parse_full_date_iso():
    # Deve respeitar ISO sem dayfirst ambiguity
    assert parse_full_date("2026-05-12").strftime("%Y-%m-%d") == "2026-05-12"
    # Mesmo com tempo
    assert parse_full_date("2026-05-12 14:30:00").strftime("%Y-%m-%d") == "2026-05-12"

def test_parse_full_date_br():
    # Deve interpretar como DD/MM/YYYY
    assert parse_full_date("12/05/2026").strftime("%Y-%m-%d") == "2026-05-12"
    assert parse_full_date("05-12-2026").strftime("%Y-%m-%d") == "2026-12-05" # 5 de dezembro

def test_parse_full_date_invalid_and_empty():
    assert parse_full_date("N/A") is None
    assert parse_full_date("") is None
    assert parse_full_date(None) is None
    assert parse_full_date("texto qualquer") is None

def test_parse_reference_period():
    assert parse_reference_period("05/2026") == "05-2026"
    assert parse_reference_period("05-2026") == "05-2026"
    assert parse_reference_period("2026-05") == "05-2026"
    assert parse_reference_period("2026-05-12") == "05-2026"
    assert parse_reference_period("12/05/2026") == "05-2026"
    
def test_parse_reference_period_invalid():
    assert parse_reference_period("N/A") is None
    assert parse_reference_period("") is None
    assert parse_reference_period(None) is None

def test_format_full_date():
    assert format_full_date("2026-05-12") == "12-05-2026"
    assert format_full_date("12/05/2026") == "12-05-2026"
    assert format_full_date("N/A") == "Não disponível"
    assert format_full_date(None) == "Não disponível"

def test_format_reference_period():
    assert format_reference_period("05/2026") == "05/2026"
    assert format_reference_period("05-2026") == "05/2026"
    assert format_reference_period("2026-05") == "05/2026"
    assert format_reference_period("2026-05-12") == "05/2026"
    assert format_reference_period("N/A") == "Não disponível"
