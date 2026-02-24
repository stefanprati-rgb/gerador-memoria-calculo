# Project: Memória de Cálculo

## Objetivo
Automação para ler os dados da planilha base (`gd_gestao_cobranca...xlsx`) e gerar planilhas de saída preenchidas usando o template `mc.xlsx`. 
O sistema possuirá um frontend em Streamlit onde o usuário selecionará:
- Qual ou quais clientes terão a planilha gerada.
- O período de interesse disponível na base de dados.
O resultado esperado é a exportação de um ou múltiplos arquivos Excel no formato de "Memória de Cálculo" baseados nas escolhas do usuário.

## Tipo
automação / web app (Streamlit)

## Stack Técnica
- **Linguagem**: Python 3.x
- **Framework**: Streamlit (Interface e Backend)
- **Manipulação de dados**: Pandas, OpenPyXL (para leitura e escrita de Excel)
- **Banco de dados**: None (Arquivos locais)
- **Outras dependências críticas**: `pytest` para testes se necessário.

## Integrações Externas
- Nenhuma integração com APIs mapeada inicialmente.
- Apenas leitura de disco para os arquivos `.xlsx`.

## Requisitos Críticos
- **Performance**: Tempo de processamento rápido para evitar timeout no Streamlit, embora a base seja local.
- **Segurança**: Operação apenas em ambiente local sem exposição de dados na nuvem pública.
- **Compliance**: O projeto rodará com processamento local via GitHub. Cuidado ao comitar as planilhas se contiverem dados sensíveis (recomenda-se adicioná-las no `.gitignore`).
- **Disponibilidade**: n/a (Hospedado localmente)
- **Precisão**: A precisão dos dados é FUNDAMENTAL nas planilhas de saída geradas. Nenhuma perda de casas decimais ou distorção dos valores importados do XLSX é tolerável.

## Contexto do Time
- **Tamanho**: Solo
- **Nível**: n/a
- **Deployment**: Local Scripts via Streamlit

## Ambiente
- **Desenvolvimento**: Windows, processamento local.
- **Produção**: Hospedado no GitHub, rodando localmente.

## Notas Adicionais
O projeto usará a arquitetura em módulos organizados em `./logic`, separando UI das regras de manipulação das planilhas para garantir testabilidade.
