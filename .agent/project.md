# Project Overview: Gerador de Memória de Cálculo

## Goal
The primary goal of this project is to generate **Memória de Cálculo** (Calculation Memory) reports from **Balanço Energético** (Energetical Balance) spreadsheets, enriched with data from **Gestão de Cobrança** (Collection Management).

## Tech Stack
- **Language**: Python 3.12+
- **UI Framework**: Streamlit
- **Data Processing**: Pandas, Openpyxl
- **Persistence & Cloud**: Google Cloud Firestore, Firebase Cloud Storage
- **Configuration**: Streamlit Secrets / Environment Variables

## Data Privacy (LGPD)
The project processes sensitive personal information, including:
- Razão Social (Company Name)
- CPF/CNPJ (Tax ID)
- UC Numbers (Consumer Units)

**Mandatory Compliance Rules:**
1. **No Sensitive Logging**: Never log CPFs, CNPJs, or any personal identifiers.
2. **Document IDs**: Avoid using CPFs as document IDs in Firestore in clear text.
3. **Data Minimization**: Only store and process necessary fields.
