
import pandas as pd
from logic.adapters.excel_adapter import TemplateExcelWriter
from logic.core.cleaning import enforce_payment_rules

def test_formatting():
    print("--- Testing excel_adapter.py formatting ---")
    writer = TemplateExcelWriter(None)
    
    # Test cases for _format_date (Reference)
    ref_cases = ["12-2025", "12/2025", pd.Timestamp("2025-12-01")]
    print("Reference (should be MM-YYYY):")
    for c in ref_cases:
        res = writer._format_date(c)
        print(f"Input: {c} -> Output: {res}")
        assert res == "12-2025", f"Expected 12-2025 but got {res}"

    # Test cases for _format_date_full (Vencimento/Pagamento)
    full_cases = ["15-12-2025", "15/12/2025", pd.Timestamp("2025-12-15")]
    print("\nFull Date (should be DD-MM-YYYY):")
    for c in full_cases:
        res = writer._format_date_full(c)
        print(f"Input: {c} -> Output: {res}")
        assert res == "15-12-2025", f"Expected 15-12-2025 but got {res}"

def test_cleaning():
    print("\n--- Testing cleaning.py sanitization ---")
    data = {
        "Referencia": ["12-2025", "05/2024", "invalid", None],
        "Vencimento": ["15/12/2025", "20/05/2024", None, "-"],
        "Status Pos-Faturamento": ["Pago", "Aberto", "Aberto", "Aberto"],
        "Data de Pagamento": ["16/12/2025", None, None, None]
    }
    df = pd.DataFrame(data)
    
    cleaned_df = enforce_payment_rules(df)
    
    print("Cleaned DataFrame:")
    print(cleaned_df[["Referencia", "Vencimento", "Status Pos-Faturamento", "Data de Pagamento"]])
    
    # Check normalization
    assert cleaned_df.loc[0, "Referencia"] == "12-2025"
    assert cleaned_df.loc[1, "Referencia"] == "05-2024"
    # Invalid one should be kept as is or handled (currently my validation just returns it or logs)
    # But Vencimento should be cleaned
    assert cleaned_df.loc[0, "Vencimento"] == "15-12-2025"

if __name__ == "__main__":
    try:
        test_formatting()
        test_cleaning()
        print("\nVerification PASSED!")
    except Exception as e:
        print(f"\nVerification FAILED: {e}")
        import traceback
        traceback.print_exc()
