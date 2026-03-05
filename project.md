# Memória de Cálculo — Gerador

Aplicação Streamlit para geração automática de planilhas de Memória de Cálculo a partir da base Balanço Energético e um template Excel de destino.

## Como Rodar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com credenciais reais do Firebase e senha admin

# 3. Executar
streamlit run app.py
```

## Arquitetura

```
├── app.py                   # Ponto de entrada — orquestra UI e lógica
├── config/
│   └── settings.py          # Configurações centralizadas via pydantic-settings (.env)
├── logic/
│   ├── adapters/
│   │   ├── excel_adapter.py # Leitura da base Balanço + escrita no template
│   │   └── firebase_adapter.py # Upload/download no Firebase Storage
│   ├── core/
│   │   ├── mapping.py       # Mapeamento de colunas base → template
│   │   └── logging_config.py
│   └── services/
│       ├── orchestrator.py  # Orquestração: filtrar → agrupar → gerar Excel/ZIP
│       └── sync_service.py  # Sincronização de planilhas + cache em Parquet
├── ui/
│   ├── styles.py            # CSS customizado
│   ├── components.py        # Componentes de UI (header, grupos, geração)
│   └── admin.py             # Painel administrativo (upload de bases)
├── tests/                   # Testes unitários (pytest)
└── scripts/                 # Scripts de debug e inspeção
```

### Camadas

| Camada | Responsabilidade |
|---|---|
| `ui/` | Apresentação — componentes Streamlit, CSS, interação |
| `logic/services/` | Lógica de negócio — orquestração, sincronização |
| `logic/adapters/` | Integração externa — Excel, Firebase |
| `logic/core/` | Domínio — mapeamento de colunas, constantes |
| `config/` | Configuração — .env, pydantic-settings |

## Testes

```bash
python -m pytest -v
```

## Fluxo de Dados

1. **Admin** faz upload das planilhas (Balanço + Gestão) via sidebar
2. **sync_service** salva localmente, faz merge, gera cache Parquet + backup Firebase
3. **Usuário** seleciona clientes e períodos em grupos
4. **Orchestrator** filtra, aplica agrupamento, gera Excel via template
5. Resultado disponível para download (.xlsx ou .zip para múltiplos)
