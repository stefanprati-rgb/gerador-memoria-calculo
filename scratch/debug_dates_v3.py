
import pandas as pd
print(f"Pandas version: {pd.__version__}")

def test(val, dayfirst):
    try:
        ts = pd.to_datetime(val, dayfirst=dayfirst)
        return ts.strftime("%d-%m-%Y")
    except Exception as e:
        return str(e)

cases = [
    "12-2025",
    "05-2024",
    "13-2025", # 13 can't be a month
    "12/2025",
    "01/2025"
]

for c in cases:
    print(f"Input: {c} | dayfirst=True  -> {test(c, True)}")
    print(f"Input: {c} | dayfirst=False -> {test(c, False)}")
