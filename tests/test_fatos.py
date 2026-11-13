"""Fatos (``blatt.infra.fatos``; PLAT-0019): envelope, DDL de referência e SQL da ``outbox``,
da ``inbox`` e da ``entrega_cursor``. A entrega está em ``tests/test_entrega.py``."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import psycopg
import pytest
from psycopg.rows import TupleRow

from blatt.infra.fatos import ddl
from blatt.infra.fatos.envelope import Envelope, ErroEnvelope, ler_json, texto_decimal
from blatt.infra.fatos.postgres import (
    Cursor,
    ErroCursor,
    FatoPublicado,
    avancar_cursor,
    gravar_na_outbox,
    inserir_na_inbox,
    ler_cursor,
    ler_outbox,
    marcar_processado,
    proximos_da_inbox,
)

TENANT = uuid.UUID("00000000-0000-4000-8000-000000000001")
ORIGEM = "fiscal.aspirador"

# Trecho da outbox do aspirador como está em sql/0001_inicial.sql (lido em 13/11/2026), para
# provar que as funções servem para a tabela que ele já tem, sem migração nova.
OUTBOX_DO_ASPIRADOR = """
CREATE TABLE outbox (
    sequencia bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id uuid NOT NULL UNIQUE,
    tenant_id uuid NOT NULL,
    tipo text NOT NULL,
    versao integer NOT NULL CHECK (versao > 0),
    origem text NOT NULL CHECK (origem = 'fiscal.aspirador'),
    instante timestamptz NOT NULL,
    correlacao uuid NOT NULL,
    causa uuid,
    conteudo jsonb NOT NULL
);
"""


def fato(tipo: str = "fiscal.documento_coletado", **conteudo: object) -> Envelope:
    return Envelope.novo(
        tipo=tipo,
        versao=2,
        tenant_id=TENANT,
        origem=ORIGEM,
        correlacao=uuid.uuid4(),
        conteudo=conteudo or {"valor_servico": "1234.50", "competencia": "2026-10"},  # type: ignore[arg-type]
    )


# --- envelope --------------------------------------------------------------------------------


def test_envelope_ida_e_volta_por_texto() -> None:
    causa = uuid.uuid4()
    original = Envelope.novo(
        tipo="folha.competencia_fechada",
        versao=1,
        tenant_id=TENANT,
        origem="folha",
        correlacao=uuid.uuid4(),
        causa=causa,
        instante=datetime(2026, 11, 13, 10, 30, tzinfo=timezone(timedelta(hours=-3))),
        conteudo={
            "competencia": "2026-10",
            "total": texto_decimal(Decimal("10500.00")),
            "itens": [{"n": 1, "ok": True, "obs": None}],
        },
    )
    texto = original.para_texto()
    assert '"total":"10500.00"' in texto
    assert '"instante":"2026-11-13T10:30:00-03:00"' in texto
    assert Envelope.de_texto(texto) == original


def test_texto_decimal_mantem_as_casas() -> None:
    assert texto_decimal(Decimal("1234.50")) == "1234.50"
    assert texto_decimal(Decimal("-0.01")) == "-0.01"
    assert texto_decimal(Decimal("1E+3")) == "1000"
    for invalido in (Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(ErroEnvelope, match="não finito"):
            texto_decimal(invalido)
    with pytest.raises(ErroEnvelope, match="recebe Decimal"):
        texto_decimal(3 / 2)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "conteudo",
    [
        {"valor": Decimal("1.50")},
        {"lista": [1, {"x": 5 / 2}]},
        {"data": datetime(2026, 1, 1, tzinfo=UTC)},
        {1: "chave numérica"},
        {"conjunto": {1, 2}},
    ],
)
def test_conteudo_so_json_puro_sem_fracionario(conteudo: dict[object, object]) -> None:
    with pytest.raises(ErroEnvelope):
        Envelope.novo(
            tipo="a.b",
            versao=1,
            tenant_id=TENANT,
            origem="a",
            correlacao=uuid.uuid4(),
            conteudo=conteudo,  # type: ignore[arg-type]
        )


def test_conteudo_e_copiado() -> None:
    original: dict[str, object] = {"lista": [1, 2]}
    envelope = fato(**original)
    original["lista"].append(3)  # type: ignore[attr-defined]
    assert envelope.conteudo == {"lista": [1, 2]}


@pytest.mark.parametrize(
    ("campo", "valor", "mensagem"),
    [
        ("tipo", "documento_coletado", "tipo fora do padrão"),
        ("tipo", "Fiscal.Documento", "tipo fora do padrão"),
        ("origem", "Fiscal", "origem fora do padrão"),
        ("versao", 0, "versao"),
        ("versao", True, "versao"),
        ("instante", datetime(2026, 1, 1), "fuso horário"),
        ("tenant_id", "00000000-0000-4000-8000-000000000001", "uuid.UUID"),
    ],
)
def test_envelope_invalido(campo: str, valor: object, mensagem: str) -> None:
    argumentos: dict[str, object] = {
        "id": uuid.uuid4(),
        "tipo": "a.b",
        "versao": 1,
        "tenant_id": TENANT,
        "origem": "a",
        "instante": datetime.now(UTC),
        "correlacao": uuid.uuid4(),
        "causa": None,
        "conteudo": {},
    }
    argumentos[campo] = valor
    with pytest.raises(ErroEnvelope, match=mensagem):
        Envelope(**argumentos)  # type: ignore[arg-type]


def test_fato_nao_e_a_propria_causa() -> None:
    identificador = uuid.uuid4()
    with pytest.raises(ErroEnvelope, match="própria causa"):
        Envelope(identificador, "a.b", 1, TENANT, "a", datetime.now(UTC), uuid.uuid4(),
                 identificador, {})  # fmt: skip


def test_leitura_estrita() -> None:
    envelope = fato().para_json()
    with pytest.raises(ErroEnvelope, match="sobram"):
        Envelope.de_json({**envelope, "extra": 1})
    sem_causa = dict(envelope)
    del sem_causa["causa"]
    with pytest.raises(ErroEnvelope, match="faltam"):
        Envelope.de_json(sem_causa)
    with pytest.raises(ErroEnvelope, match="fracionário"):
        ler_json('{"valor": 1.5}')
    with pytest.raises(ErroEnvelope, match="constante"):
        ler_json('{"valor": NaN}')
    with pytest.raises(ErroEnvelope, match="repetida"):
        ler_json('{"a": 1, "a": 2}')
    with pytest.raises(ErroEnvelope, match="UUID"):
        Envelope.de_json({**envelope, "id": "x"})
    with pytest.raises(ErroEnvelope, match="ISO 8601"):
        Envelope.de_json({**envelope, "instante": "ontem"})


def test_ddl_outbox_confere_o_nome_do_modulo() -> None:
    assert "CHECK (origem = 'folha')" in ddl.ddl_outbox("folha")
    for invalido in ("Folha", "folha'; DROP TABLE x; --", ""):
        with pytest.raises(ValueError, match="nome de módulo"):
            ddl.ddl_outbox(invalido)


# --- banco: outbox ---------------------------------------------------------------------------


def _colunas(conexao: psycopg.Connection[TupleRow], tabela: str) -> list[tuple[object, ...]]:
    return conexao.execute(
        "SELECT column_name, data_type, is_nullable, is_identity FROM information_schema.columns "
        "WHERE table_name = %s ORDER BY ordinal_position",
        (tabela,),
    ).fetchall()


def test_ddl_de_referencia_e_a_outbox_do_aspirador(criar_banco: Callable[[], str]) -> None:
    with psycopg.connect(criar_banco()) as referencia, psycopg.connect(criar_banco()) as aspirador:
        referencia.execute(ddl.ddl_outbox(ORIGEM).encode())
        aspirador.execute(OUTBOX_DO_ASPIRADOR.encode())
        assert _colunas(referencia, "outbox") == _colunas(aspirador, "outbox")


def test_grava_e_le_na_outbox_do_aspirador(banco: psycopg.Connection[TupleRow]) -> None:
    banco.execute(OUTBOX_DO_ASPIRADOR.encode())
    primeiro, segundo = fato(), fato("fiscal.nfe_coletada", chave="1" * 44)
    assert gravar_na_outbox(banco, primeiro) == 1
    assert gravar_na_outbox(banco, segundo) == 2
    lidos = ler_outbox(banco)
    assert lidos == [FatoPublicado(1, primeiro), FatoPublicado(2, segundo)]
    assert ler_outbox(banco, depois_de=1) == [FatoPublicado(2, segundo)]
    assert lidos[0].envelope.conteudo["valor_servico"] == "1234.50"


def test_outbox_recusa_fato_de_outro_modulo(banco: psycopg.Connection[TupleRow]) -> None:
    banco.execute(ddl.ddl_outbox(ORIGEM).encode())
    alheio = Envelope.novo(
        tipo="folha.x_feito", versao=1, tenant_id=TENANT, origem="folha",
        correlacao=uuid.uuid4(), conteudo={},
    )  # fmt: skip
    with pytest.raises(psycopg.errors.CheckViolation):
        gravar_na_outbox(banco, alheio)


def test_gravacao_na_transacao_de_quem_chama(dsn_banco: str) -> None:
    with psycopg.connect(dsn_banco, autocommit=True) as conexao:
        conexao.execute(ddl.ddl_outbox(ORIGEM).encode())
        with pytest.raises(RuntimeError, match="desfaz"), conexao.transaction():
            gravar_na_outbox(conexao, fato())
            raise RuntimeError("o dado falhou: desfaz tudo")
        assert ler_outbox(conexao) == []


# --- banco: inbox e cursor -------------------------------------------------------------------


@pytest.fixture
def consumidor(banco: psycopg.Connection[TupleRow]) -> psycopg.Connection[TupleRow]:
    banco.execute(ddl.ddl_consumidor().encode())
    banco.commit()
    return banco


def test_inbox_idempotente(consumidor: psycopg.Connection[TupleRow]) -> None:
    publicado = FatoPublicado(7, fato())
    assert inserir_na_inbox(consumidor, publicado) is True
    assert inserir_na_inbox(consumidor, publicado) is False
    (quantos,) = consumidor.execute("SELECT count(*) FROM inbox").fetchone() or (0,)
    assert quantos == 1


def test_id_e_a_unica_chave_unica_da_inbox(consumidor: psycopg.Connection[TupleRow]) -> None:
    """O ON CONFLICT sem alvo só equivale ao "ON CONFLICT (id)" se não houver outra chave."""
    indices = consumidor.execute(
        "SELECT indexdef FROM pg_indexes WHERE tablename = 'inbox' AND indexdef LIKE '%UNIQUE%'"
    ).fetchall()
    assert [i[0] for i in indices] == [
        "CREATE UNIQUE INDEX inbox_pkey ON public.inbox USING btree (id)"
    ]


def test_consumo_idempotente(consumidor: psycopg.Connection[TupleRow], dsn_banco: str) -> None:
    primeiro, segundo = fato(), fato("fiscal.nfe_coletada")
    inserir_na_inbox(consumidor, FatoPublicado(2, segundo))
    inserir_na_inbox(consumidor, FatoPublicado(1, primeiro))
    consumidor.commit()
    pendentes = proximos_da_inbox(consumidor)
    assert [p.envelope for p in pendentes] == [primeiro, segundo]
    assert [p.sequencia_origem for p in pendentes] == [1, 2]
    # Outro processo do módulo não pega as linhas travadas por este.
    with psycopg.connect(dsn_banco) as outro:
        assert proximos_da_inbox(outro) == []
    assert marcar_processado(consumidor, primeiro.id) is True
    assert marcar_processado(consumidor, primeiro.id) is False
    consumidor.commit()
    assert [p.envelope for p in proximos_da_inbox(consumidor)] == [segundo]
    assert proximos_da_inbox(consumidor, tipos=["fiscal.documento_coletado"]) == []
    assert marcar_processado(consumidor, uuid.uuid4()) is False


def test_cursor(consumidor: psycopg.Connection[TupleRow]) -> None:
    assert ler_cursor(consumidor, ORIGEM) == Cursor(ORIGEM, 0, None)
    identificador = uuid.uuid4()
    avancar_cursor(consumidor, ORIGEM, 5, identificador)
    assert ler_cursor(consumidor, ORIGEM) == Cursor(ORIGEM, 5, identificador)
    avancar_cursor(consumidor, ORIGEM, 5, identificador)
    with pytest.raises(ErroCursor, match="não recua"):
        avancar_cursor(consumidor, ORIGEM, 4, uuid.uuid4())
    with pytest.raises(ErroCursor, match="negativa"):
        avancar_cursor(consumidor, ORIGEM, -1, None)
    with pytest.raises(ErroCursor, match="zero"):
        avancar_cursor(consumidor, "outra", 0, uuid.uuid4())
    assert ler_cursor(consumidor, "outra") == Cursor("outra", 0, None)
