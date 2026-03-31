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

A suíte de testes cobre a lógica de sincronização, merge e resilência de dados.

```bash
# Rodar todos os testes
python -m pytest tests/test_sync_service.py -v
```

## 🏗️ Arquitetura

O projeto segue uma arquitetura em camadas (`ui/`, `logic/services/`, `logic/adapters/`, `logic/core/`, `config/`), garantindo separação de responsabilidades e alta testabilidade.
