"""DDL de referência da ``outbox``, da ``inbox`` e da ``entrega_cursor`` (PLAT-0019).

As migrações são de cada módulo (PLAT-0017): este pacote **não cria tabela nenhuma**. O módulo
copia o texto devolvido por estas funções para uma migração própria (``sql/NNNN_nome.sql``) e
nunca mais o altera; uma mudança futura é migração nova. Para ver o texto::

    uv run python -c "from blatt.infra.fatos import ddl; print(ddl.ddl_outbox('fiscal.aspirador'))"

Concessões (PLAT-0019, item 9; OPER-0003, item 3), no padrão "se o papel existir" da migração
0005 do aspirador: o papel é do ``oper``, que pode ainda não o ter criado; rodar o
provisionamento depois de migrar completa as concessões.

- ``blatt_entregador``: ``SELECT`` na ``outbox`` (origem); ``INSERT`` na ``inbox`` e
  ``SELECT, INSERT, UPDATE`` na ``entrega_cursor`` (destino). Nada mais.
- ``blatt_portal``: só ``SELECT`` nas três (PLAT-0019, item 11).

A ``outbox`` é a do aspirador (``sql/0001_inicial.sql``), sem mudança de coluna: quem já a tem
não precisa de migração para usar ``blatt.infra.fatos``. O ``CHECK`` em ``origem`` prende a
tabela ao módulo dono do banco.
"""

import re

_ORIGEM = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")

_OUTBOX = """\
-- Fatos publicados por {origem} (PLAT-0019, itens 2 e 4), gravados na mesma transação do
-- dado. A sequencia dá a ordem de publicação. Ninguém de fora do módulo altera ou apaga linha.
-- Texto de referência do blatt-plataforma (blatt.infra.fatos.ddl.ddl_outbox).
CREATE TABLE outbox (
    sequencia bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id uuid NOT NULL UNIQUE,
    tenant_id uuid NOT NULL,
    tipo text NOT NULL,
    versao integer NOT NULL CHECK (versao > 0),
    origem text NOT NULL CHECK (origem = '{origem}'),
    instante timestamptz NOT NULL,
    correlacao uuid NOT NULL,
    causa uuid,
    conteudo jsonb NOT NULL
);

-- Leitura pelo entregador e pelo portal (PLAT-0019, itens 9 e 11; OPER-0003). O CONNECT e o
-- USAGE em public são do provisionamento do oper.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'blatt_entregador') THEN
        GRANT SELECT ON outbox TO blatt_entregador;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'blatt_portal') THEN
        GRANT SELECT ON outbox TO blatt_portal;
    END IF;
END
$$;
"""

_INBOX = """\
-- Fatos recebidos (PLAT-0019, item 3). O entregador só insere, com INSERT ... ON CONFLICT
-- DO NOTHING: a entrega é "pelo menos uma vez" e o id do fato é a chave. O id é a ÚNICA
-- restrição de unicidade da tabela, e é por isso que o ON CONFLICT sem alvo equivale ao
-- "ON CONFLICT (id)" do item 5: com alvo explícito, o PostgreSQL exige SELECT na coluna do
-- alvo, e o papel do entregador só tem INSERT aqui (item 9). Não acrescente outra restrição
-- UNIQUE: uma repetição nela seria ignorada calada. processado_em é do módulo, que processa
-- cada fato uma vez (blatt.infra.fatos.postgres.marcar_processado).
-- Texto de referência do blatt-plataforma (blatt.infra.fatos.ddl.ddl_inbox).
CREATE TABLE inbox (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    tipo text NOT NULL,
    versao integer NOT NULL CHECK (versao > 0),
    origem text NOT NULL,
    instante timestamptz NOT NULL,
    correlacao uuid NOT NULL,
    causa uuid,
    conteudo jsonb NOT NULL,
    sequencia_origem bigint NOT NULL CHECK (sequencia_origem > 0),
    recebido_em timestamptz NOT NULL DEFAULT now(),
    processado_em timestamptz
);

CREATE INDEX inbox_pendentes ON inbox (origem, sequencia_origem) WHERE processado_em IS NULL;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'blatt_entregador') THEN
        GRANT INSERT ON inbox TO blatt_entregador;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'blatt_portal') THEN
        GRANT SELECT ON inbox TO blatt_portal;
    END IF;
END
$$;
"""

_ENTREGA_CURSOR = """\
-- Até onde cada origem foi entregue a este banco (PLAT-0019, item 6), atualizado na mesma
-- transação da inserção na inbox. ultimo_id é o id do fato na ultima_sequencia da origem: o
-- entregador confere que ele continua lá antes de ler adiante, e para com erro se a origem
-- foi restaurada de uma cópia anterior a essa entrega (ultimo_id nulo: inscrição que começa
-- de um ponto declarado, sem fato conhecido). Sem tenant_id: tabela de operação,
-- não de negócio (a instância tem um tenant, PLAT-0004).
-- Texto de referência do blatt-plataforma (blatt.infra.fatos.ddl.ddl_entrega_cursor).
CREATE TABLE entrega_cursor (
    origem text PRIMARY KEY,
    ultima_sequencia bigint NOT NULL CHECK (ultima_sequencia >= 0),
    ultimo_id uuid,
    atualizado_em timestamptz NOT NULL DEFAULT now(),
    CHECK (ultima_sequencia > 0 OR ultimo_id IS NULL)
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'blatt_entregador') THEN
        GRANT SELECT, INSERT, UPDATE ON entrega_cursor TO blatt_entregador;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'blatt_portal') THEN
        GRANT SELECT ON entrega_cursor TO blatt_portal;
    END IF;
END
$$;
"""


def ddl_outbox(origem: str) -> str:
    """DDL da ``outbox`` do módulo ``origem`` (por exemplo, ``"folha"``), com as concessões."""
    if not _ORIGEM.fullmatch(origem):
        raise ValueError(f"nome de módulo inválido para a outbox: {origem!r}")
    return _OUTBOX.format(origem=origem)


def ddl_inbox() -> str:
    """DDL da ``inbox`` de um módulo que consome fatos, com as concessões."""
    return _INBOX


def ddl_entrega_cursor() -> str:
    """DDL da ``entrega_cursor`` de um módulo que consome fatos, com as concessões."""
    return _ENTREGA_CURSOR


def ddl_consumidor() -> str:
    """``inbox`` e ``entrega_cursor`` juntas: o que um módulo cria ao passar a consumir."""
    return _INBOX + "\n" + _ENTREGA_CURSOR
