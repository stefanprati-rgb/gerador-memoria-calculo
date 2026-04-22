
import pandas as pd
import numpy as np

def _format_date(val):
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (pd.Timestamp,)):
        return val.strftime("%m/%Y")
    try:
        ts = pd.to_datetime(val, dayfirst=True)
        return ts.strftime("%m/%Y")
    except Exception as e:
        return f"ERROR: {e}"

def _format_date_full(val):
    if val is None or pd.isna(val):
        return "Não disponível"
    if isinstance(val, (pd.Timestamp,)):
        return val.strftime("%d-%m-%Y")
    try:
        ts = pd.to_datetime(val, dayfirst=True)
        return ts.strftime("%d-%m-%Y")
    except Exception as e:
        return f"ERROR: {e}"

test_cases = ["12-2025", "12/2025", "05-2024", "05/2024"]

print("--- Testing current _format_date_full (the problematic one for Reference) ---")
for tc in test_cases:
    print(f"Input: {tc} -> Output: {_format_date_full(tc)}")

print("\n--- Testing current _format_date (the one it SHOULD use) ---")
for tc in test_cases:
    print(f"Input: {tc} -> Output: {_format_date(tc)}")

print("\n--- Deep dive into pd.to_datetime ---")
for tc in test_cases:
    try:
        ts = pd.to_datetime(tc, dayfirst=True)
        print(f"Input: {tc} | Parsed: {ts} | Year: {ts.year} | Month: {ts.month} | Day: {ts.day}")
    except Exception as e:
        print(f"Input: {tc} | Error: {e}")
