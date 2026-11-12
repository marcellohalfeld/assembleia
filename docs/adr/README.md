# ADRs da plataforma

Cada decisão que vale para todos os módulos tem um arquivo, no formato de Michael Nygard:
título, status, contexto, decisão e consequências
([Nygard, 2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)).

Regras (PLAT-0016, item 5, mantidas da PLAT-0015):

- Prefixo `PLAT-`, numeração sequencial, nunca reaproveitada. A próxima é a **PLAT-0023**.
- Status: **Proposta** → **Aceita** (ou **Rejeitada**). Uma decisão revista não é apagada nem
  reescrita: ganha status **Substituída por PLAT-NNNN** e a nova ADR aponta para ela. A ADR
  nova é autocontida: traz a regra inteira, sem obrigar a ler a substituída.
- Só o Marcello muda o status para Aceita.
- Modelo em [0000-modelo.md](0000-modelo.md).
- Decisão que vale só para um módulo fica no repositório dele, com o prefixo do módulo.

## Conjunto vigente

As ADRs de 12/11/2026 (PLAT-0016 a PLAT-0022) reorganizam a plataforma e, à medida que forem
aceitas, formam com as anteriores que não foram substituídas o conjunto que vale. A PLAT-0016
foi aceita em 12/11/2026; as PLAT-0017 a 0022 continuam propostas:

| Tema | ADR |
| --- | --- |
| Linguagem e licenças | [PLAT-0001](PLAT-0001-python-e-politica-de-licencas.md), [PLAT-0008](PLAT-0008-driver-postgresql-psycopg.md) |
| Arquitetura de cada módulo | [PLAT-0002](PLAT-0002-arquitetura-hexagonal.md) |
| Parâmetros legais | [PLAT-0003](PLAT-0003-contrato-dos-parametros-externos.md) |
| Instância e tenant | [PLAT-0004](PLAT-0004-instancia-por-escritorio.md) |
| Repositórios, módulos, código comum, governança | [PLAT-0016](PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md) |
| Persistência | [PLAT-0017](PLAT-0017-persistencia-postgresql.md) |
| Dono de cada dado e cadastro | [PLAT-0018](PLAT-0018-dono-de-cada-dado-e-cadastro.md) |
| Integração entre módulos | [PLAT-0019](PLAT-0019-integracao-por-fatos-e-entregador.md) |
| Infraestrutura e implantação | [PLAT-0020](PLAT-0020-infraestrutura-e-implantacao.md) |
| Interface web | [PLAT-0021](PLAT-0021-interface-web.md) |
| Backup | [PLAT-0022](PLAT-0022-backup-arquivo-imutavel-e-dossies.md) |

A PLAT-0016, aceita, substitui a PLAT-0015. **Enquanto as PLAT-0017 a 0022 forem propostas,
valem as antigas** (PLAT-0005, 0006, 0009, 0010 e 0014), cujo status já aponta para a
substituta. A PLAT-0019 muda uma decisão
aceita (o orquestrador da PLAT-0014) e pede atenção no aceite (pendência A-08).

## Índice

| ADR | Título | Status |
| --- | --- | --- |
| [PLAT-0001](PLAT-0001-python-e-politica-de-licencas.md) | Python e política de licenças | Proposta |
| [PLAT-0002](PLAT-0002-arquitetura-hexagonal.md) | Arquitetura hexagonal | Proposta |
| [PLAT-0003](PLAT-0003-contrato-dos-parametros-externos.md) | Contrato dos parâmetros externos | Proposta |
| [PLAT-0004](PLAT-0004-instancia-por-escritorio.md) | Uma instância por escritório, com `tenant_id` | Proposta |
| [PLAT-0005](PLAT-0005-cadastro-interno-extraivel.md) | Cadastro interno, desenhado para extração | Substituída pela PLAT-0018 (proposta) |
| [PLAT-0006](PLAT-0006-infraestrutura-aberta.md) | Infraestrutura aberta | Substituída pela PLAT-0020 (proposta) |
| [PLAT-0008](PLAT-0008-driver-postgresql-psycopg.md) | Driver do PostgreSQL: psycopg (exceção LGPL) | Aceita |
| [PLAT-0009](PLAT-0009-persistencia-postgresql.md) | Persistência em PostgreSQL: SQL explícito, migrações e tenant | Substituída pela PLAT-0017 e, no item 8, pela PLAT-0016 (propostas) |
| [PLAT-0010](PLAT-0010-vinculos-e-dados-pessoais.md) | Vínculos e dados pessoais no banco, com histórico por data | Aceita; regra comum substituída pela PLAT-0018 (proposta); parte da folha a virar FOLHA-0016 |
| [PLAT-0014](PLAT-0014-banco-por-modulo-e-orquestrador.md) | Um banco por módulo e integração por orquestrador; dados pessoais dos trabalhadores só na folha, empresa e sócios no cadastro | Aceita (03/11/2026, P-57 da folha); substituída pelas PLAT-0017, 0018 e 0019 (propostas) |
| [PLAT-0015](PLAT-0015-governanca-no-assembleia.md) | Decisões de plataforma num repositório próprio, o `assembleia` | Substituída pela PLAT-0016 (aceita em 12/11/2026) |
| [PLAT-0016](PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md) | Mapa de módulos, papel de cada repositório e código comum como pacote | Aceita (12/11/2026) |
| [PLAT-0017](PLAT-0017-persistencia-postgresql.md) | Persistência em PostgreSQL: um banco por módulo, SQL explícito, migrações e tenant | Proposta |
| [PLAT-0018](PLAT-0018-dono-de-cada-dado-e-cadastro.md) | Dono de cada dado, histórico por vigência e cadastro geral | Proposta |
| [PLAT-0019](PLAT-0019-integracao-por-fatos-e-entregador.md) | Integração por fatos: outbox, inbox e um entregador sem banco próprio | Proposta (altera a PLAT-0014, aceita) |
| [PLAT-0020](PLAT-0020-infraestrutura-e-implantacao.md) | Infraestrutura aberta e implantação por Docker Compose na rede local | Proposta |
| [PLAT-0021](PLAT-0021-interface-web.md) | Interface web: adaptador web em cada módulo e um portal no `oper` | Proposta |
| [PLAT-0022](PLAT-0022-backup-arquivo-imutavel-e-dossies.md) | Backup em três camadas: arquivo imutável, cópia dos bancos e dossiês | Proposta |

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

**Classificação da PLAT-0010 (pendência A-02, encaminhada):** a PLAT-0010 mistura uma regra
comum (histórico por data de vigência, só acrescentado) com o modelo de vínculo da folha. A
regra comum passa para a PLAT-0018; a parte só da folha vai para a FOLHA-0016, no `blatt`.
