import pandas as pd
import re
from datetime import datetime
import logging

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

    # --- Regra 1: Data de Vencimento (Blindagem) ---
    def format_vencimento(val):
        invalids = ["", "-", "n/a", "não", "none", "nan", "nat"]
        if pd.isna(val) or str(val).strip().lower() in invalids:
            return "Não disponível"
        try:
            # Parse flexível de data
            ts = pd.to_datetime(val, dayfirst=True, errors='coerce')
            if pd.isna(ts):
                return "Não disponível"
            return ts.strftime("%d-%m-%Y")
        except:
            return "Não disponível"

    # Criamos uma coluna temporária com tipo datetime para fazer comparações lógicas
    # (respeitando o dayfirst=True para o padrão brasileiro)
    df_clean["_venc_date_temp"] = pd.to_datetime(df_clean[col_venc], dayfirst=True, errors='coerce')
    df_clean[col_venc] = df_clean[col_venc].apply(format_vencimento)

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
                # Tentar converter para data para garantir que é um dado válido
                try:
                    ts_pag = pd.to_datetime(data_pag, dayfirst=True, errors='coerce')
                    if pd.notna(ts_pag):
                        tem_pagamento_valido = True
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
    Higieniza a coluna de Referência (mês/ano) e valida o formato via regex.
    Garante que valores como '12/2025' ou '12-2025' sejam normalizados e válidos.
    """
    if df.empty or "Referencia" not in df.columns:
        return df

    df_clean = df.copy()
    regex_ref = re.compile(r"^(0[1-9]|1[0-2])[-/](\d{4})$")

    def validate_ref(val):
        if pd.isna(val):
            return val
        
        s_val = str(val).strip()
        match = regex_ref.match(s_val)
        if match:
            # Normaliza para MM/YYYY
            return f"{match.group(1)}/{match.group(2)}"
        
        # Se for um datetime, converte para MM/YYYY
        if isinstance(val, (datetime, pd.Timestamp)):
            return val.strftime("%m/%Y")
            
        # Tratar formato ISO YYYY-MM-DD (com ou sem timestamp)
        iso_match = re.match(r'^(\d{4})-(\d{1,2})-\d{1,2}', s_val)
        if iso_match:
            year = iso_match.group(1)
            month = iso_match.group(2).zfill(2)
            return f"{month}/{year}"

        return val

    df_clean["Referencia"] = df_clean["Referencia"].apply(validate_ref)
    
    # Validação final: se sobrou algo que não bate com a regex (e não é nulo)
    # podemos decidir se limpamos ou se deixamos para o log
    return df_clean
