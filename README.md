# Memória de Cálculo — Gerador

[![CI](https://github.com/stefanprati-rgb/gerador-memoria-calculo/actions/workflows/ci.yml/badge.svg)](https://github.com/stefanprati-rgb/gerador-memoria-calculo/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/stefanprati-rgb/gerador-memoria-calculo/actions)

Aplicação Streamlit para geração automática de planilhas de Memória de Cálculo a partir da base Balanço Energético e um template Excel de destino.

## 🚀 Como Rodar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com credenciais reais do Firebase e senha admin

# 3. Executar
streamlit run app.py
```

## 🧪 Testes

A suíte de testes cobre a lógica de sincronização, merge, geração de Excel, configuração,
viewmodels de UI e smoke tests leves da aplicação Streamlit.

```bash
# Rodar toda a suíte
python -m pytest tests -q

# Rodar com warnings tratados como erro
python -m pytest tests -q -W error::UserWarning
```

### Estratégia de Testes

- `tests/test_sync_service.py`, `tests/test_orchestrator.py`, `tests/test_excel_adapter.py`
  validam o núcleo de negócio e a geração dos arquivos.
- `tests/test_config.py`, `tests/test_firebase_adapter.py`
  cobrem configuração e integrações externas.
- `tests/test_admin_viewmodel.py`, `tests/test_wizard_viewmodel.py`
  cobrem a lógica de decisão da UI fora do Streamlit.
- `tests/test_streamlit_smoke.py`, `tests/test_app_smoke.py`
  cobrem smoke tests da interface e do boot da aplicação inteira.

O objetivo é manter a regra de negócio protegida por testes unitários e usar smoke tests
apenas para validar a casca da aplicação e a integração entre módulos.
```

## 🏗️ Arquitetura

O projeto segue uma arquitetura em camadas (`ui/`, `logic/services/`, `logic/adapters/`, `logic/core/`, `config/`), garantindo separação de responsabilidades e alta testabilidade.
