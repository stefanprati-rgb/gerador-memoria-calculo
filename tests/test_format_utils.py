import re
from ui.utils.format_utils import (
    format_period_token,
    format_periods_for_filename,
    generate_suggested_filename,
    build_runtime_filename,
    build_scope_base_name,
    build_zip_entry_filename,
)


def test_format_period_token_mes_ano():
    assert format_period_token("2026-01-01") == "jan_2026"
    assert format_period_token("02/2026") == "fev_2026"


def test_format_periods_for_filename_anos_diferentes():
    periods = ["12/2025", "01/2026"]
    assert format_periods_for_filename(periods) == "dez_2025_jan_2026"


def test_format_periods_for_filename_mesmo_ano():
    periods = ["02/2026", "01/2026"]
    assert format_periods_for_filename(periods) == "jan_fev_2026"


def test_generate_suggested_filename_sem_timestamp():
    name = generate_suggested_filename("Projeto Alpha", ["CLI_A"], ["01/2026", "02/2026"])
    assert name == "Projeto_Alpha_jan_fev_2026"


def test_build_runtime_filename_com_timestamp():
    filename = build_runtime_filename("Projeto_Alpha_jan_fev_2026", ".xlsx")
    assert re.match(r"^Projeto_Alpha_jan_fev_2026_\d{4}-\d{2}-\d{2}_\d{4}\.xlsx$", filename)


def test_build_scope_base_name_para_multiplos_clientes():
    base = build_scope_base_name("Grupo_1", ["EMBRACON ADM", "DELCI"])
    assert base == "EMBRACON_ADM_e_outros"


def test_build_zip_entry_filename():
    entry = build_zip_entry_filename("Grupo_1", ["EMBRACON ADM", "DELCI"], "01/2026")
    assert entry == "EMBRACON_ADM_e_outros_jan_2026.xlsx"
