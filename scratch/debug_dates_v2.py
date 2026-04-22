
import pandas as pd

def test(val, dayfirst):
    try:
        ts = pd.to_datetime(val, dayfirst=dayfirst)
        return ts.strftime("%d-%m-%Y")
    except Exception as e:
        return str(e)

print(f"12-2025 (dayfirst=True)  -> {test('12-2025', True)}")
print(f"12-2025 (dayfirst=False) -> {test('12-2025', False)}")
print(f"01-2025 (dayfirst=True)  -> {test('01-2025', True)}")

# Maybe the input is slightly different?
print(f"12/2025 (dayfirst=True)  -> {test('12/2025', True)}")
