"""SQL explícito da ``outbox``, da ``inbox`` e da ``entrega_cursor`` (PLAT-0017, PLAT-0019).

Sem ORM, com parâmetros ligados. **A transação é de quem chama**: nenhuma função aqui faz
``commit``. ``gravar_na_outbox`` roda na transação do dado que origina o fato (item 2);
``proximos_da_inbox`` e ``marcar_processado``, na transação em que o módulo aplica o fato.
As tabelas são as de ``blatt.infra.fatos.ddl``, criadas pelas migrações do módulo.

Consumo idempotente (item 3), dentro de uma transação do módulo::

    with conexao.transaction():
        for fato in proximos_da_inbox(conexao, limite=50):
            aplicar(fato.envelope)            # efeito do módulo, no mesmo banco
            marcar_processado(conexao, fato.envelope.id)

``proximos_da_inbox`` trava as linhas lidas (``FOR UPDATE SKIP LOCKED``): dois processos do
mesmo módulo não aplicam o mesmo fato, e um fato aplicado e marcado na mesma transação nunca é
aplicado duas vezes.
"""

import json
import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import TupleRow

from blatt.infra.fatos.envelope import Envelope, ErroEnvelope, conteudo_json, ler_json

type Conexao = psycopg.Connection[TupleRow]

_COLUNAS = "id, tenant_id, tipo, versao, origem, instante, correlacao, causa, conteudo::text"

INSERIR_NA_INBOX = """
    INSERT INTO inbox (id, tenant_id, tipo, versao, origem, instante, correlacao, causa,
                       conteudo, sequencia_origem)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
    ON CONFLICT DO NOTHING
"""
# Sem alvo no ON CONFLICT: com "(id)", o PostgreSQL exige SELECT na coluna id, e o entregador só
# tem INSERT na inbox (PLAT-0019, item 9). Na inbox do DDL de referência o id é a única
# restrição de unicidade, então o efeito é o mesmo do "ON CONFLICT (id) DO NOTHING" do item 5.


@dataclass(frozen=True)
class FatoPublicado:
    """Linha da ``outbox``: o envelope e a ``sequencia`` na origem."""

    sequencia: int
    envelope: Envelope


@dataclass(frozen=True)
class FatoRecebido:
    """Linha da ``inbox``."""

    envelope: Envelope
    sequencia_origem: int
    recebido_em: datetime
    processado_em: datetime | None


@dataclass(frozen=True)
class Cursor:
    """Linha da ``entrega_cursor``: até onde a ``origem`` foi entregue a este banco."""

    origem: str
    ultima_sequencia: int
    ultimo_id: uuid.UUID | None


class ErroCursor(RuntimeError):
    """Cursor que recuaria, ou sequência sem o fato correspondente."""


def _texto_conteudo(envelope: Envelope) -> str:
    return json.dumps(envelope.conteudo, ensure_ascii=False, separators=(",", ":"))


def _envelope(linha: tuple[object, ...]) -> Envelope:
    """Envelope a partir das colunas de ``_COLUNAS``; o conteúdo é lido estrito do texto."""
    id_, tenant, tipo, versao, origem, instante, correlacao, causa, conteudo = linha
    if not isinstance(conteudo, str) or not isinstance(instante, datetime):
        raise ErroEnvelope("linha de fato com tipos inesperados")  # pragma: no cover
    if not isinstance(tipo, str) or not isinstance(origem, str) or not isinstance(versao, int):
        raise ErroEnvelope("linha de fato com tipos inesperados")  # pragma: no cover
    if not isinstance(id_, uuid.UUID) or not isinstance(tenant, uuid.UUID):
        raise ErroEnvelope("linha de fato com tipos inesperados")  # pragma: no cover
    if not isinstance(correlacao, uuid.UUID) or not (causa is None or isinstance(causa, uuid.UUID)):
        raise ErroEnvelope("linha de fato com tipos inesperados")  # pragma: no cover
    return Envelope(
        id=id_,
        tipo=tipo,
        versao=versao,
        tenant_id=tenant,
        origem=origem,
        instante=instante,
        correlacao=correlacao,
        causa=causa,
        conteudo=conteudo_json(ler_json(conteudo)),
    )


# --- outbox (módulo que publica) ---------------------------------------------------------------


def gravar_na_outbox(conexao: Conexao, envelope: Envelope) -> int:
    """Grava o fato na ``outbox``, na transação de quem chama; devolve a ``sequencia``.

    Grave os fatos perto do fim da transação do dado: a linha mantém a ``outbox`` com escrita
    em curso até o ``commit``, e o entregador espera por ela antes de avançar o cursor
    (``blatt.infra.fatos.entrega``).
    """
    linha = conexao.execute(
        """
        INSERT INTO outbox (id, tenant_id, tipo, versao, origem, instante, correlacao, causa,
                            conteudo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        RETURNING sequencia
        """,
        (
            envelope.id,
            envelope.tenant_id,
            envelope.tipo,
            envelope.versao,
            envelope.origem,
            envelope.instante,
            envelope.correlacao,
            envelope.causa,
            _texto_conteudo(envelope),
        ),
    ).fetchone()
    if linha is None:  # pragma: no cover - INSERT ... RETURNING sempre devolve a linha
        raise RuntimeError("a outbox não devolveu a sequência")
    return int(linha[0])


def ler_outbox(conexao: Conexao, depois_de: int = 0, limite: int = 500) -> list[FatoPublicado]:
    """Fatos da ``outbox`` com ``sequencia`` maior que ``depois_de``, em ordem.

    Leitura simples, para exibição (portal) e para testes. **Não serve para avançar um
    cursor**: um fato de sequência menor pode ainda estar em transação aberta e aparecer
    depois. Para entregar, use ``blatt.infra.fatos.entrega.entregar``.
    """
    linhas = conexao.execute(
        f"SELECT sequencia, {_COLUNAS} FROM outbox WHERE sequencia > %s "  # noqa: S608
        "ORDER BY sequencia LIMIT %s",
        (depois_de, limite),
    ).fetchall()
    return [FatoPublicado(int(linha[0]), _envelope(linha[1:])) for linha in linhas]


# --- inbox (módulo que consome) ----------------------------------------------------------------


def inserir_na_inbox(conexao: Conexao, fato: FatoPublicado) -> bool:
    """Insere o fato na ``inbox``; repetido (mesmo ``id``), não faz nada.

    Devolve ``True`` se o fato é novo e ``False`` se já estava lá (entrega repetida).
    """
    envelope = fato.envelope
    cursor = conexao.execute(
        INSERIR_NA_INBOX,
        (
            envelope.id,
            envelope.tenant_id,
            envelope.tipo,
            envelope.versao,
            envelope.origem,
            envelope.instante,
            envelope.correlacao,
            envelope.causa,
            _texto_conteudo(envelope),
            fato.sequencia,
        ),
    )
    return cursor.rowcount == 1


def proximos_da_inbox(
    conexao: Conexao, limite: int = 100, tipos: Collection[str] | None = None
) -> list[FatoRecebido]:
    """Fatos ainda não processados, por origem e ordem de publicação, travados para quem chama.

    ``FOR UPDATE SKIP LOCKED``: linhas travadas por outra transação do módulo são puladas.
    Chame dentro de uma transação e marque cada fato aplicado com ``marcar_processado``.
    """
    filtro = "" if tipos is None else "AND tipo = ANY(%s)"
    parametros: tuple[object, ...] = (limite,) if tipos is None else (list(tipos), limite)
    linhas = conexao.execute(
        f"SELECT {_COLUNAS}, sequencia_origem, recebido_em, processado_em FROM inbox "  # noqa: S608
        f"WHERE processado_em IS NULL {filtro} "
        "ORDER BY origem, sequencia_origem LIMIT %s FOR UPDATE SKIP LOCKED",
        parametros,
    ).fetchall()
    return [
        FatoRecebido(_envelope(linha[:9]), int(linha[9]), linha[10], linha[11]) for linha in linhas
    ]


def marcar_processado(conexao: Conexao, id_fato: uuid.UUID) -> bool:
    """Marca o fato como processado. ``False`` se ele já estava marcado (ou não existe)."""
    cursor = conexao.execute(
        "UPDATE inbox SET processado_em = now() WHERE id = %s AND processado_em IS NULL",
        (id_fato,),
    )
    return cursor.rowcount == 1


# --- entrega_cursor (no banco de destino) ------------------------------------------------------


def ler_cursor(conexao: Conexao, origem: str, *, travar: bool = False) -> Cursor:
    """Cursor da ``origem`` neste banco; sem linha, cursor zero (inscrição nova).

    ``travar=True`` cria a linha se faltar e a trava (``FOR UPDATE``) até o fim da transação:
    dois entregadores da mesma origem para o mesmo destino não andam ao mesmo tempo.
    """
    if travar:
        conexao.execute(
            "INSERT INTO entrega_cursor (origem, ultima_sequencia) VALUES (%s, 0) "
            "ON CONFLICT (origem) DO NOTHING",
            (origem,),
        )
    consulta = (
        "SELECT ultima_sequencia, ultimo_id FROM entrega_cursor WHERE origem = %s FOR UPDATE"
        if travar
        else "SELECT ultima_sequencia, ultimo_id FROM entrega_cursor WHERE origem = %s"
    )
    linha = conexao.execute(consulta, (origem,)).fetchone()
    if linha is None:
        return Cursor(origem, 0, None)
    return Cursor(origem, int(linha[0]), linha[1])


def avancar_cursor(
    conexao: Conexao, origem: str, sequencia: int, id_fato: uuid.UUID | None
) -> None:
    """Grava o cursor da ``origem`` em ``sequencia`` (o fato ``id_fato``); nunca recua.

    ``id_fato`` nulo só para um ponto de partida declarado numa inscrição (PLAT-0019, item 8).
    """
    if sequencia < 0:
        raise ErroCursor(f"sequência negativa: {sequencia}")
    if sequencia == 0 and id_fato is not None:
        raise ErroCursor("cursor zero não tem fato")
    atual = ler_cursor(conexao, origem)
    if sequencia < atual.ultima_sequencia:
        raise ErroCursor(
            f"o cursor de {origem} não recua: está em {atual.ultima_sequencia}, pedido {sequencia}"
        )
    conexao.execute(
        """
        INSERT INTO entrega_cursor (origem, ultima_sequencia, ultimo_id, atualizado_em)
        VALUES (%s, %s, %s, now())
        ON CONFLICT (origem) DO UPDATE
            SET ultima_sequencia = EXCLUDED.ultima_sequencia,
                ultimo_id = EXCLUDED.ultimo_id,
                atualizado_em = EXCLUDED.atualizado_em
        """,
        (origem, sequencia, id_fato),
    )
