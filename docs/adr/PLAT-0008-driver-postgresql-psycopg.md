# PLAT-0008: Driver do PostgreSQL — psycopg (exceção LGPL)

> Transferida de `marcellohalfeld/blatt` (`docs/adr/0008-driver-postgresql-psycopg.md`, commit `2bcff8e`) em 2026-11-03, pela [PLAT-0015](PLAT-0015-governanca-no-assembleia.md). Texto sem alteração, salvo o título e os links, que passaram a apontar para cá ou para o repositório da folha. Nas referências do texto, "ADR NNNN" é o número de origem: ver a tabela de correspondência no [README](README.md).

- **Status:** Aceita
- **Data:** 2026-10-25
- **Decisor:** Marcello

## Contexto

A Etapa 3 introduz a persistência em PostgreSQL (ADR 0006). O driver mais usado em Python,
o **psycopg** (versão 3), é licenciado sob **LGPL-3.0-only** (metadados do PyPI, consultados
em 25/10/2026). Pela ADR 0001, item 3, LGPL exige ADR específica, e a verificação de licenças
do CI a barra por padrão.

Opções avaliadas: **psycopg** (LGPL-3.0, baseado na libpq oficial do PostgreSQL),
**pg8000** (BSD-3, Python puro) e **asyncpg** (Apache-2.0, só assíncrono).

## Decisão

1. Usar o **psycopg 3**, no pacote `psycopg[binary]`, que já traz a libpq; não é preciso
   instalar bibliotecas do sistema.
2. **Condições da exceção à ADR 0001:**
   - usar o psycopg **sem modificar** o código dele, importado em tempo de execução, sempre
     atrás de um adaptador (ADR 0002);
   - em toda distribuição do Blatt (imagem de container, pacote instalado no escritório):
     incluir o aviso de que o psycopg é usado sob LGPL-3.0, o texto da licença e a versão
     exata usada, com o link para o código-fonte no PyPI;
   - não impedir a troca do psycopg por outra versão (em Python isso é natural).
3. **CI:** a verificação de licenças passa a ignorar nominalmente `psycopg` e
   `psycopg-binary`, e só eles. Qualquer outra dependência GPL, LGPL ou AGPL continua
   reprovando o build.

## Alternativas consideradas

- **pg8000 (BSD-3):** suficiente para o volume de uma MPE e sem obrigações de licença, mas
  com um mantenedor principal e menos uso em produção. Preterido pelo critério do Marcello:
  "mais garantido; quanto mais simples, melhor".
- **asyncpg (Apache-2.0):** exige o código todo assíncrono, o que complica sem ganho no MVP.

## Consequências

- O driver é o padrão do ecossistema, com a libpq oficial: autenticação, TLS e
  comportamento de conexão iguais aos das ferramentas do PostgreSQL; COPY rápido para a
  carga inicial (Etapa 6).
- Cada distribuição leva o aviso de LGPL (item 2). Custo baixo, mas não pode ser esquecido:
  entra na lista de verificação de entrega quando houver empacotamento.
- Clientes com política contra qualquer licença "GPL" podem questionar; a resposta é esta
  ADR e o fato de a LGPL não alcançar o código do Blatt quando a biblioteca é usada sem
  modificação.
- Se um dia a exceção precisar cair, a troca para o pg8000 se limita ao adaptador.

## Referências

- [psycopg no PyPI](https://pypi.org/project/psycopg/) (licença LGPL-3.0-only)
- [GNU LGPL versão 3](https://www.gnu.org/licenses/lgpl-3.0.html)
- [pg8000 no PyPI](https://pypi.org/project/pg8000/) e [asyncpg no PyPI](https://pypi.org/project/asyncpg/)
- ADR 0001 (política de licenças), ADR 0002 (adaptadores), ADR 0006 (PostgreSQL)
