import pandas as pd
from datetime import datetime
import logging
from logic.core.dates import format_full_date, parse_full_date, format_reference_period

logger = logging.getLogger(__name__)


def enforce_payment_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica as regras rigorosas de Vencimento e Situação do Pagamento.
    
    Regras:
    1. Vencimento formatado como DD-MM-YYYY ou 'Não disponível'.
    2. Situação do Pagamento hierarquia: Negociado > Pago > Atrasado > Em aberto.
    3. Consistência entre Data de Pagamento e Status Pago.
    """
    if df.empty:
        return df

    # --- Regra 0: Referência (Blindagem de Competência) ---
    df = sanitize_reference_period(df)

    # Faz uma cópia para não alterar referências indesejadas
    df_clean = df.copy()
    hoje = pd.Timestamp(datetime.now().date())
    
    # Nomes das colunas
    col_venc = "Vencimento"
    col_status = "Status Pos-Faturamento"
    col_pag = "Data de Pagamento"
    
    # Garante que as colunas existem para evitar KeyError
    for col in [col_venc, col_status, col_pag]:
        if col not in df_clean.columns:
            df_clean[col] = pd.NA

    df_clean["_venc_date_temp"] = df_clean[col_venc].apply(parse_full_date)
    
    df_clean[col_venc] = df_clean[col_venc].apply(lambda val: format_full_date(val, default="Não disponível"))

    # --- Regras 2 e 3: Situação do Pagamento e Consistência ---
    def avaliar_situacao(row):
        status_raw = str(row[col_status]).strip().lower()
        data_pag = row[col_pag]
        venc_date = row["_venc_date_temp"]
        
        invalids = ["", "-", "n/a", "não", "none", "nan", "nat"]
        
        # Teste de robustez para a Data de Pagamento
        tem_pagamento_valido = False
        if pd.notna(data_pag):
            str_pag = str(data_pag).strip().lower()
            if str_pag not in invalids:
                try:
                    ts_pag = parse_full_date(data_pag)
                    if ts_pag is not None:
                        tem_pagamento_valido = True
                        data_pag = ts_pag.strftime("%d-%m-%Y") # Normaliza a data
                except:
                    pass
        
        # Prioridade 1: Negociado (Acordos suspendem a régua de atraso padrão)
        if "negociad" in status_raw or "acordo" in status_raw:
            return "Negociado", pd.NA
            
        # Prioridade 2: Pago (Exige data de pagamento ou status explícito)
        if "pago" in status_raw or tem_pagamento_valido:
            # Se for considerado pago, tentamos manter a data se ela existir
            return "Pago", data_pag if tem_pagamento_valido else ""
            
        # Prioridade 3: Atrasado ou Em aberto (Baseado no Vencimento vs Data Atual)
        if pd.notna(venc_date):
            if hoje > venc_date:
                return "Atrasado", pd.NA
            else:
                return "Em aberto", pd.NA
                
        # Fallback seguro (Se não tem vencimento nem pagamento, assume-se em aberto)
        return "Em aberto", pd.NA

    # Aplica as regras de negócio linha a linha
    df_clean[[col_status, col_pag]] = df_clean.apply(avaliar_situacao, axis=1, result_type="expand")
    
    # Limpeza da coluna auxiliar
    df_clean.drop(columns=["_venc_date_temp"], inplace=True)
    
    # --- Regra 4: Validação Rigorosa (Raise Error if logic fails) ---
    assert not df_clean[col_venc].isna().any(), "Erro crítico: Existem datas de vencimento nulas após saneamento."
    assert not df_clean[col_status].isna().any(), "Erro crítico: Existem situações de pagamento nulas após saneamento."
    
    valid_status = {"Pago", "Atrasado", "Em aberto", "Negociado"}
    actual_status = set(df_clean[col_status].unique())
    invalid_found = actual_status - valid_status
    
    if invalid_found:
        logger.error("Status de pagamento inválidos detectados: %s", invalid_found)
        raise ValueError(f"Status de pagamento inválidos detectados: {invalid_found}")
    
    return df_clean


def sanitize_reference_period(df: pd.DataFrame) -> pd.DataFrame:
    """
    Higieniza a coluna de Referência (mês/ano).
    Garante que valores válidos sejam normalizados para MM/YYYY
    e que valores inválidos não escapem do saneamento.
    """
    if df.empty or "Referencia" not in df.columns:
        return df

    df_clean = df.copy()

    def validate_ref(val):
        if pd.isna(val):
            return pd.NA
        return format_reference_period(val, default="Não disponível")

    df_clean["Referencia"] = df_clean["Referencia"].apply(validate_ref)

    return df_clean
