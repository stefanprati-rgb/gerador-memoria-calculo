# Decisões de Arquitetura

## Padrão Arquitetural
Aplicação baseada em scripts interativos gerenciados pelo Streamlit (MVC adaptado para dados).
A interface interativa não deverá conter lógica de negócios. E o core responsável pelo processamento de planilhas deve ser desacoplado do framework Streamlit para testabilidade em scripts locais.

## Estrutura de Pastas
- **logic/core/**: Modelos de dados, constantes de coluna, regras para tratamento das planilhas de cobrança.
- **logic/services/**: Orquestração do processamento, lendo a planilha `gd_gestao_cobranca`, extraindo os dados dos clientes selecionados e alimentando o template da `mc`.
- **logic/adapters/**: Leitura e escrita de Excel usando openpyxl/pandas.
- **app.py**: Ponto de entrada do frontend em Streamlit.

> [!NOTE]
> A pasta raiz de código foi renomeada de `src` para `logic` para evitar conflitos de `KeyError: 'src'` específicos do ambiente de deploy do Streamlit Cloud.

## Decisões Importantes
Em breve em cases específicos documentados via ADR.
