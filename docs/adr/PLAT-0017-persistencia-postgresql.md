# PLAT-0017: Persistência em PostgreSQL — um banco por módulo, SQL explícito, migrações e tenant

- **Status:** Aceita (12/11/2026: "plat-0017 a 0022 aprovadas")
- **Data:** 2026-11-12
- **Decisor:** Marcello
- **Substitui:** [PLAT-0009](PLAT-0009-persistencia-postgresql.md) (inteira; o item 8, núcleo
  comum, passa para a [PLAT-0016](PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md)) e os
  itens 1 e 2 da [PLAT-0014](PLAT-0014-banco-por-modulo-e-orquestrador.md), além das partes de
  persistência dos itens 10 e 11 (faseamento) dela.
- **Origem:** consolidação de 12/11/2026. Não muda o sentido de nenhuma regra: junta num texto
  só o que estava espalhado entre a PLAT-0009 e a PLAT-0014, já aceita nesses itens.

## Contexto

As regras de persistência estavam em duas ADRs: a PLAT-0009 (SQL explícito, migrações, tenant,
schema por módulo) e a PLAT-0014, aceita em 03/11/2026, que trocou o schema por módulo por um
banco por módulo e as migrações globais por migrações por módulo. Quem lia a PLAT-0009 precisava
saber quais itens a PLAT-0014 tinha alterado. Esta ADR junta as duas, sem rediscutir o mérito.

Já decidido e mantido: PostgreSQL ([PLAT-0020](PLAT-0020-infraestrutura-e-implantacao.md)),
driver psycopg 3 ([PLAT-0008](PLAT-0008-driver-postgresql-psycopg.md)), `tenant_id` em toda
tabela ([PLAT-0004](PLAT-0004-instancia-por-escritorio.md)).

## Decisão

1. **Um banco (*database*) PostgreSQL por módulo**, no mesmo servidor da instância (`folha`,
   `cadastro`, `fiscal_aspirador` e assim por diante; mapa na PLAT-0016).
   - Cada módulo conecta com usuário próprio e só tem privilégio no seu banco. No PostgreSQL,
     uma conexão enxerga um único banco, então o isolamento é imposto pelo servidor, não por
     convenção.
   - Nenhum módulo lê o banco de outro. Os únicos acessos de fora são os papéis restritos da
     integração ([PLAT-0019](PLAT-0019-integracao-por-fatos-e-entregador.md)) e do backup
     ([PLAT-0022](PLAT-0022-backup-arquivo-imutavel-e-dossies.md)).
   - Passar um módulo para servidor próprio no futuro é mudar só a configuração de conexão.
2. **SQL explícito, sem ORM.** Os adaptadores escrevem as consultas à mão, com parâmetros
   ligados pelo psycopg (nunca concatenação de valores). Identificadores dinâmicos, quando
   houver, passam por `psycopg.sql.Identifier`.
3. **Migrações por módulo.** Cada módulo tem a sua sequência de arquivos `NNNN_nome.sql` a partir
   de 0001, no próprio pacote, e a sua tabela de controle no próprio banco
   (`public.blatt_migracao`). O executor (`blatt.infra.postgres.migracoes`, no pacote
   `blatt-plataforma`, PLAT-0016):
   - roda todas as pendentes numa única transação, sob `pg_advisory_xact_lock`, para que duas
     instâncias subindo ao mesmo tempo não apliquem a mesma migração duas vezes;
   - registra versão, nome e SHA-256 de cada migração;
   - recusa iniciar se uma migração já aplicada foi alterada ou se o banco tem migração que o
     código não conhece (código mais antigo que o banco);
   - só avança: correção de esquema é migração nova, nunca edição de migração aplicada.
   Antes de cada migração em produção é feita uma cópia do banco (PLAT-0022).
4. **`tenant_id` em toda tabela de negócio**, desde a primeira migração, e toda consulta filtra
   por ele. Dentro de um banco, as chaves estrangeiras incluem o `tenant_id`
   (`FOREIGN KEY (tenant_id, empresa_id) REFERENCES … (tenant_id, id)`), de modo que o próprio
   banco impede um registro de apontar para outro tenant. Sem chave estrangeira entre bancos
   (nem entre schemas, na exceção do item 9): a integridade entre módulos fica na aplicação.
5. **Tenant e conexão num único ponto:** `blatt.infra.configuracao` lê `BLATT_TENANT_ID` (o
   mesmo em todos os bancos da instância) e a conexão de cada módulo (`BLATT_DSN_<MODULO>`, por
   exemplo `BLATT_DSN_FISCAL_ASPIRADOR`, pela função `dsn_modulo()`). Nenhum código de negócio
   lê variáveis de ambiente. A senha não vai na conexão: vem de arquivo de segredo (PLAT-0020).
   Cada repositório recebe o `tenant_id` no construtor, filtra toda consulta por ele e recusa
   gravar entidade de outro tenant (inclusive tentativa de sobrescrever um id que já pertence a
   outro tenant).
6. **Transação é de quem chama.** Repositórios não fazem `commit`; o caso de uso (ou o ponto de
   entrada) abre a conexão e decide quando confirmar. A gravação na `outbox` entra na mesma
   transação (PLAT-0019).
7. **Valores monetários** em `numeric(15,2)`, lidos como `Decimal` pelo psycopg, coerente com a
   regra de nunca usar `float`.
8. **Testes contra PostgreSQL real.** Os testes sobem um cluster temporário (`initdb` +
   `pg_ctl`, socket local, sem rede) e criam um banco novo e migrado por teste. No CI,
   `BLATT_EXIGIR_POSTGRES=1` transforma a ausência do PostgreSQL em falha, não em teste pulado.
9. **Exceção datada: a folha, até a etapa do cadastro.** A folha continua num banco com os
   schemas `cadastro` e `folha`, uma sequência de migrações e a conexão `BLATT_DSN`, como estava
   na PLAT-0009, e não muda durante o MVP dela (PLAT-0014, item 10, mantido). Dentro dessa
   exceção valem as regras de antes: sem chave estrangeira entre os dois schemas, a folha
   acessa o cadastro só por um port. A exceção termina na etapa do cadastro
   ([PLAT-0018](PLAT-0018-dono-de-cada-dado-e-cadastro.md)), quando `cadastro` e `folha`
   passam a bancos próprios, com migrações próprias.

## Alternativas consideradas

- **Schema por módulo num banco único** (PLAT-0009, itens 2 e 3). Mais simples de operar e
  permite SQL entre módulos, mas o isolamento depende de disciplina, e backup, restauração e
  migração não são independentes. Descartada como alvo pela PLAT-0014; mantida só na exceção
  do item 9.
- **Um servidor PostgreSQL por módulo.** Isolamento máximo, inclusive contra queda do servidor,
  mas multiplica processos, backups e atualizações. Na escala de um escritório, não compensa.
  A decisão permite chegar lá depois mudando só a configuração.
- **SQLAlchemy + Alembic** (MIT). ORM e migrações automáticas, mas duas dependências grandes,
  uma camada de abstração sobre o SQL e migrações geradas que ainda precisam de revisão manual.

## Consequências

- Uma dependência a menos para auditar; o SQL fica legível na revisão; o que roda no banco é
  exatamente o que está no repositório.
- Mudanças de esquema exigem escrever a migração à mão e testá-la; não há geração automática
  nem migração reversa. A volta atrás é a restauração da cópia feita antes da migração.
- O isolamento por tenant tem três camadas: filtro no repositório, recusa na gravação e chave
  composta no banco. Ainda não há *row-level security*; ela fica para quando houver
  multi-tenant de fato (PLAT-0004, item 2).
- Sem transação entre módulos: a consistência entre eles é eventual (PLAT-0019).
- Relatórios cruzados (folha + fiscal + contábil) não podem ser um SQL único; passam por um
  módulo que agregue a partir dos fatos (o contábil, por exemplo). É o principal custo do banco
  por módulo.
- Os testes de persistência dependem dos binários do PostgreSQL na máquina; sem eles, rodam
  localmente como pulados (e falham no CI).
- Na folha, a etapa do cadastro inclui separar os bancos e trocar `BLATT_DSN` pelas conexões
  por módulo.

## Referências

- [PLAT-0009](PLAT-0009-persistencia-postgresql.md) e
  [PLAT-0014](PLAT-0014-banco-por-modulo-e-orquestrador.md), itens 1, 2, 10 e 11 (substituídas
  nestes pontos).
- PostgreSQL, *Managing Databases — Overview* (cada conexão acessa um único banco):
  https://www.postgresql.org/docs/current/manage-ag-overview.html
- PostgreSQL, *Advisory Locks*:
  https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS
- PostgreSQL, chaves estrangeiras:
  https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK
- psycopg 3, passagem de parâmetros: https://www.psycopg.org/psycopg3/docs/basic/params.html e
  composição de SQL: https://www.psycopg.org/psycopg3/docs/api/sql.html
- C. Richardson, padrão *Database per service*:
  https://microservices.io/patterns/data/database-per-service.html
- Os links acima já eram citados pelas PLAT-0009 e PLAT-0014; nenhum abriu na sessão de
  12/11/2026 (rede da sessão), e ficam como estavam, a conferir.
