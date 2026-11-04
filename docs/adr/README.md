# ADRs da plataforma

Cada decisão que vale para todos os módulos tem um arquivo, no formato de Michael Nygard:
título, status, contexto, decisão e consequências
([Nygard, 2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)).

Regras (PLAT-0015):

- Prefixo `PLAT-`, numeração sequencial, nunca reaproveitada. A próxima é a **PLAT-0016**.
- Status: **Proposta** → **Aceita** (ou **Rejeitada**). Uma decisão revista não é apagada nem
  reescrita: ganha status **Substituída por PLAT-NNNN** e a nova ADR aponta para ela.
- Só o Marcello muda o status para Aceita.
- Modelo em [0000-modelo.md](0000-modelo.md).
- Decisão que vale só para um módulo fica no repositório dele, com o prefixo do módulo.

| ADR | Título | Status |
| --- | --- | --- |
| [PLAT-0001](PLAT-0001-python-e-politica-de-licencas.md) | Python e política de licenças | Proposta |
| [PLAT-0002](PLAT-0002-arquitetura-hexagonal.md) | Arquitetura hexagonal | Proposta |
| [PLAT-0003](PLAT-0003-contrato-dos-parametros-externos.md) | Contrato dos parâmetros externos | Proposta |
| [PLAT-0004](PLAT-0004-instancia-por-escritorio.md) | Uma instância por escritório, com `tenant_id` | Proposta |
| [PLAT-0005](PLAT-0005-cadastro-interno-extraivel.md) | Cadastro interno, desenhado para extração | Proposta (alterada em parte pela PLAT-0014: itens 1 a 3) |
| [PLAT-0006](PLAT-0006-infraestrutura-aberta.md) | Infraestrutura aberta | Proposta (alterada em parte pela PLAT-0014: fila de trabalho) |
| [PLAT-0008](PLAT-0008-driver-postgresql-psycopg.md) | Driver do PostgreSQL: psycopg (exceção LGPL) | Aceita |
| [PLAT-0009](PLAT-0009-persistencia-postgresql.md) | Persistência em PostgreSQL: SQL explícito, migrações e tenant | Proposta (alterada em parte pela PLAT-0014: itens 2 e 3) |
| [PLAT-0010](PLAT-0010-vinculos-e-dados-pessoais.md) | Vínculos e dados pessoais no banco, com histórico por data | Aceita (alterada em parte pela PLAT-0014: item 1, a partir da fase 2) |
| [PLAT-0014](PLAT-0014-banco-por-modulo-e-orquestrador.md) | Um banco por módulo e integração por orquestrador; dados pessoais dos trabalhadores só na folha, empresa e sócios no cadastro | Aceita (03/11/2026, P-57 da folha) |
| [PLAT-0015](PLAT-0015-governanca-no-assembleia.md) | Decisões de plataforma num repositório próprio, o `assembleia` | Proposta |

## Tabela de correspondência

Os números de origem não mudam; muda só o prefixo. Use esta tabela para ler citações antigas
("ADR 0005", "ADR 0014 da plataforma").

| Número de origem | Onde foi escrita | Hoje | Onde está |
| --- | --- | --- | --- |
| 0001, 0002, 0003, 0004, 0005, 0006 | blatt | PLAT-0001 a PLAT-0006 | aqui |
| 0007 | blatt | FOLHA-0007 | blatt |
| 0008, 0009, 0010 | blatt | PLAT-0008, PLAT-0009, PLAT-0010 | aqui |
| 0011, 0012, 0013 | blatt | FOLHA-0011, FOLHA-0012, FOLHA-0013 | blatt |
| 0014 | aspirador (redação), blatt (guarda) | PLAT-0014 | aqui |
| 0001 a 0006 do aspirador | aspirador | ASP-0001 a ASP-0006 | aspirador |

Atenção ao ler o aspirador: "ADR 0005" lá é a ASP-0005 (banco próprio, fase 1), não a
PLAT-0005 (cadastro). Quando o texto do aspirador diz "ADR 0014 da plataforma", é a PLAT-0014.

**Classificação a confirmar (pendência A-02):** a PLAT-0010 mistura uma regra comum
(histórico por data de vigência, só acrescentado) com o modelo de vínculo da folha. Foi
transferida inteira porque o resumo da plataforma já a tratava como comum; a parte só da
folha pode virar uma `FOLHA-` numa revisão futura.
