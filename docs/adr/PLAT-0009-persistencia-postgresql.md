# PLAT-0009: Persistência em PostgreSQL — SQL explícito, migrações versionadas e tenant

> Transferida de `marcellohalfeld/blatt` (`docs/adr/0009-persistencia-postgresql.md`, commit `2bcff8e`; atualizada para `e4352fc`, com o aceite da PLAT-0014 em 03/11/2026, P-57) em 2026-11-03, pela [PLAT-0015](PLAT-0015-governanca-no-assembleia.md). Texto sem alteração, salvo o título e os links, que passaram a apontar para cá ou para o repositório da folha. Nas referências do texto, "ADR NNNN" é o número de origem: ver a tabela de correspondência no [README](README.md).

- **Status:** Proposta.
  Alterada em parte pela [ADR 0014](PLAT-0014-banco-por-modulo-e-orquestrador.md) (aceita em
  03/11/2026): itens 2 e 3, um banco por módulo em vez de um schema por módulo.
- **Data:** 2026-10-25
- **Decisor:** Marcello

## Contexto

A Etapa 3 grava os primeiros dados de negócio: cadastro (empresa, estabelecimento, lotação,
pessoa) e o histórico de pagamentos que o IRRF precisa para somar as retenções do mês
(RIR/2018, art. 677, § 2º). Já estavam decididos o PostgreSQL (ADR 0006), o driver psycopg
(ADR 0008, com a diretriz "quanto mais simples, melhor"), o `tenant_id` em toda tabela
(ADR 0004) e o cadastro isolado em schema próprio (ADR 0005). Faltava decidir como o esquema
evolui, como o código fala com o banco e como o isolamento por tenant é garantido.

Opções avaliadas para o esquema e o acesso:

- **SQLAlchemy + Alembic** (MIT): ORM e migrações automáticas. Acrescenta duas dependências
  grandes, uma camada de abstração sobre o SQL e migrações geradas que ainda precisam de
  revisão manual.
- **SQL explícito + migrador próprio**: arquivos `.sql` numerados e um aplicador de ~100
  linhas. Nenhuma dependência além do psycopg; o que roda no banco é exatamente o que está
  no repositório.

## Decisão

1. **SQL explícito, sem ORM.** Os adaptadores escrevem as consultas à mão, com parâmetros
   ligados pelo psycopg (nunca concatenação de valores). Identificadores dinâmicos, quando
   houver, passam por `psycopg.sql.Identifier`.
2. **Migrações versionadas** em `src/blatt/infra/postgres/sql/NNNN_nome.sql`, numeração
   contínua. O aplicador (`blatt.infra.postgres.migracoes`):
   - roda tudo numa única transação, sob `pg_advisory_xact_lock`, para que duas instâncias
     subindo ao mesmo tempo não apliquem a mesma migração duas vezes;
   - registra versão, nome e SHA-256 de cada migração em `public.blatt_migracao`;
   - recusa iniciar se uma migração já aplicada foi alterada ou se o banco tem migração que o
     código não conhece (código mais antigo que o banco);
   - só avança: correção de esquema é migração nova, nunca edição de migração aplicada.
3. **Schemas por módulo:** `cadastro` e `folha`. Sem chave estrangeira entre schemas
   (ADR 0005); dentro de um schema, as chaves estrangeiras incluem o `tenant_id`
   (`FOREIGN KEY (tenant_id, empresa_id) REFERENCES … (tenant_id, id)`), de modo que o
   próprio banco impede um registro de apontar para outro tenant.
4. **Tenant num único ponto:** `BLATT_TENANT_ID` é lido só em `blatt.infra.configuracao`.
   Cada repositório recebe o `tenant_id` no construtor, filtra toda consulta por ele e
   recusa gravar entidade de outro tenant (inclusive tentativa de sobrescrever um id que já
   pertence a outro tenant).
5. **Transação é de quem chama.** Repositórios não fazem `commit`; o caso de uso (ou o
   ponto de entrada) abre a conexão e decide quando confirmar.
6. **Valores monetários** em `numeric(15,2)`, lidos como `Decimal` pelo psycopg — coerente
   com a regra de nunca usar `float`.
7. **Testes contra PostgreSQL real.** Os testes sobem um cluster temporário (`initdb` +
   `pg_ctl`, socket local, sem rede) e criam um banco novo e migrado por teste. No CI,
   `BLATT_EXIGIR_POSTGRES=1` transforma a ausência do PostgreSQL em falha, não em teste
   pulado.
8. **Núcleo comum (`blatt.comum`)**: tipos e validações de formato usados por mais de um
   módulo — `AnoMes`, CPF/CNPJ (incluindo o CNPJ alfanumérico) e as regras de texto do
   eSocial para códigos e campos livres. Não importa nenhum módulo de negócio; o
   `import-linter` verifica.

## Consequências

- Uma dependência a menos para auditar e atualizar; o SQL fica legível na revisão.
- Mudanças de esquema exigem escrever a migração à mão e testá-la; não há geração
  automática nem migração reversa. Para um banco por escritório e poucas tabelas, é aceitável.
- O isolamento por tenant tem três camadas: filtro no repositório, recusa na gravação e
  chave composta no banco. Ainda não há *row-level security*; ela fica para quando houver
  multi-tenant de fato (ADR 0004, item 2).
- Os testes de persistência dependem de binários do PostgreSQL na máquina; sem eles, rodam
  localmente como pulados (e falham no CI).

## Referências

- [psycopg 3 — passagem de parâmetros](https://www.psycopg.org/psycopg3/docs/basic/params.html)
- [psycopg 3 — composição de SQL (`psycopg.sql`)](https://www.psycopg.org/psycopg3/docs/api/sql.html)
- [PostgreSQL 16 — advisory locks](https://www.postgresql.org/docs/16/explicit-locking.html#ADVISORY-LOCKS)
- [PostgreSQL 16 — chaves estrangeiras](https://www.postgresql.org/docs/16/ddl-constraints.html#DDL-CONSTRAINTS-FK)
- [Decreto 9.580/2018 (RIR/2018), art. 677](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/decreto/d9580.htm)
