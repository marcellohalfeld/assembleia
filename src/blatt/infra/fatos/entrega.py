"""Entrega de fatos de uma ``outbox`` para uma ``inbox`` (PLAT-0019, itens 5 a 7 e 10).

Biblioteca sem regra de negócio para o entregador do ``oper``, que só configura inscrições e
conexões: lê a ``outbox`` da origem a partir do cursor, em ordem de ``sequencia``, insere na
``inbox`` do destino os fatos dos tipos inscritos (``ON CONFLICT DO NOTHING``, sobre o ``id``,
única chave da ``inbox``; ver ``blatt.infra.fatos.ddl``) e avança o
cursor **na mesma transação**, no banco do destino. Copia o envelope como veio: o conteúdo
passa como texto JSON, sem ser lido nem transformado.

Fato confirmado fora de ordem (item 7)
--------------------------------------

A ``sequencia`` é reservada quando a linha é inserida, não quando a transação confirma: a
transação A reserva 1, a B reserva 2 e confirma, e só depois A confirma. Um leitor que visse 2
e gravasse o cursor em 2 nunca mais leria 1. A técnica usada aqui, que só precisa do
``SELECT`` na ``outbox`` (item 9) e não exige nada de quem grava:

1. ler as sequências acima do cursor (até ``lote``) e guardar a maior, ``M``;
2. consultar em ``pg_locks`` as **outras** transações que têm, na ``outbox``, um bloqueio que
   permite inserir (``RowExclusiveLock`` ou mais forte);
3. esperar até nenhuma dessas transações ter mais esse bloqueio (terminaram);
4. ler de novo, com um *snapshot* novo, as linhas com ``cursor < sequencia <= M`` e
   entregá-las; o cursor vai para ``M``.

Por que não perde fato: uma linha de sequência ``s < M`` que não estava visível no passo 1
pertence a uma transação T ainda aberta no passo 1. T reservou ``s`` dentro de um ``INSERT``
na ``outbox``, e o ``INSERT`` toma o ``RowExclusiveLock`` da tabela **antes** de calcular a
identidade (o bloqueio é tomado na análise do comando, ou na revalidação do plano preparado) e
só o solta no fim da transação (ou no ``ROLLBACK TO SAVEPOINT`` da subtransação, e então a
linha não existe mais). Logo, no passo 2, ou T ainda tem o bloqueio (e o passo 3 espera por
ela), ou T já terminou. Em ambos os casos T terminou antes do passo 4, e a releitura vê ``s``
se T confirmou. Uma transação que reserve depois do passo 1 recebe sequência maior que ``M``
(a identidade só cresce) e fica para a próxima rodada. ``pg_locks`` mostra também os bloqueios
*fast-path* e os de transações preparadas (``pid`` nulo).

Se as transações não terminam dentro de ``espera_maxima``, nada é entregue nessa rodada
(``aguardando=True``) e o cursor não anda; a próxima rodada tenta de novo.

Alternativas consideradas (a decisão formal é de uma ADR ``OPER-``):

- **trava de quem grava** (``pg_advisory_xact_lock`` ou ``LOCK TABLE outbox IN SHARE ROW
  EXCLUSIVE MODE`` antes do ``INSERT``, ou um gatilho ``BEFORE INSERT FOR EACH STATEMENT``
  que tome a trava): a ordem de reserva vira a ordem de confirmação, e o leitor fica trivial.
  Mas depende de todo escritor cooperar (o aspirador grava hoje sem trava; o gatilho exigiria
  migração nova nele), serializa as transações que publicam até o ``commit`` e abre espaço
  para *deadlock* entre elas;
- **horizonte de transações** (``pg_snapshot_xmin(pg_current_snapshot())`` e a coluna de
  sistema ``xmin``): a ordem dos identificadores de transação não é a ordem de reserva da
  sequência, e uma transação pode reservar a sequência antes de receber identificador
  (``nextval`` não atribui um); a comparação entre ``xid`` de 32 bits e ``xid8`` ainda exige
  cuidado com a volta do contador. Não dá para provar;
- **reler uma janela antes do cursor** (por número de linhas ou por tempo), com o
  ``ON CONFLICT`` tornando a repetição inócua: simples, mas uma transação mais longa que a
  janela ainda perde o fato;
- **``LOCK TABLE outbox IN SHARE MODE`` pelo leitor**: espera os escritores e bloqueia novos
  enquanto lê, mas o PostgreSQL exige ``UPDATE``, ``DELETE`` ou ``TRUNCATE`` na tabela para
  esse modo, além do ``SELECT`` do item 9, e trava quem publica.

Origem restaurada
-----------------

O cursor guarda também o ``id`` do último fato entregue. Antes de ler adiante, confere que a
origem ainda tem esse fato nessa sequência. Se não tem (a origem voltou a uma cópia anterior à
entrega, e pode até ter reutilizado a sequência para outro fato), levanta
``ErroOrigemRestaurada`` e não entrega nada: a correção é decisão de quem opera, pelo
procedimento de restauração do ``oper`` (PLAT-0019, Consequências), nunca automática.
"""

import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import timedelta

from psycopg import pq

from blatt.infra.fatos.postgres import INSERIR_NA_INBOX, Conexao, avancar_cursor, ler_cursor

# Modos que permitem gravar linhas na tabela (os demais só leem ou não conflitam com INSERT).
_MODOS_DE_ESCRITA = ["RowExclusiveLock", "ShareRowExclusiveLock", "ExclusiveLock",
                     "AccessExclusiveLock"]  # fmt: skip

_ESCRITORES = """
    SELECT DISTINCT virtualtransaction
    FROM pg_locks
    WHERE locktype = 'relation'
      AND database = (SELECT oid FROM pg_database WHERE datname = current_database())
      AND relation = 'outbox'::regclass
      AND mode = ANY(%s)
      AND granted
      AND pid IS DISTINCT FROM pg_backend_pid()
"""


class ErroEntrega(RuntimeError):
    """Entrega impossível sem decisão de quem opera; nada foi entregue."""


class ErroOrigemRestaurada(ErroEntrega):
    """A origem não tem mais o último fato entregue: foi restaurada de uma cópia anterior."""


@dataclass(frozen=True)
class Inscricao:
    """O que um destino recebe de uma origem (PLAT-0019, item 8).

    ``tipos``: pares (tipo, versão); versão ``None`` aceita todas as versões do tipo.
    """

    origem: str
    tipos: frozenset[tuple[str, int | None]]

    @classmethod
    def de(cls, origem: str, tipos: Iterable[str | tuple[str, int]]) -> "Inscricao":
        """``Inscricao.de("fiscal.aspirador", ["fiscal.nfe_coletada", ("fiscal.x", 2)])``."""
        pares: set[tuple[str, int | None]] = set()
        for item in tipos:
            pares.add((item, None) if isinstance(item, str) else (item[0], item[1]))
        if not pares:
            raise ValueError("inscrição sem nenhum tipo")
        return cls(origem, frozenset(pares))

    def aceita(self, tipo: str, versao: int) -> bool:
        return (tipo, None) in self.tipos or (tipo, versao) in self.tipos


@dataclass(frozen=True)
class ResultadoEntrega:
    origem: str
    cursor_antes: int
    cursor_depois: int
    lidos: int  # linhas da outbox percorridas nesta rodada
    inseridos: int  # novos na inbox
    repetidos: int  # já estavam na inbox (entrega repetida)
    ignorados: int  # de tipos não inscritos
    aguardando: bool  # escritores da outbox não terminaram a tempo; nada avançou


def _escritores(origem: Conexao) -> set[str]:
    return {str(linha[0]) for linha in origem.execute(_ESCRITORES, (_MODOS_DE_ESCRITA,))}


def _esperar_escritores(origem: Conexao, espera_maxima: timedelta, intervalo: timedelta) -> bool:
    """Espera terminarem as transações que tinham escrita aberta na outbox agora."""
    pendentes = _escritores(origem)
    limite = time.monotonic() + espera_maxima.total_seconds()
    while pendentes:
        if time.monotonic() >= limite:
            return False
        time.sleep(intervalo.total_seconds())
        pendentes &= _escritores(origem)
    return True


def _conferir_cursor(origem: Conexao, nome: str, ultima: int, ultimo_id: uuid.UUID | None) -> None:
    if ultima == 0:
        return
    if ultimo_id is None:
        linha = origem.execute("SELECT max(sequencia) FROM outbox").fetchone()
        maxima = 0 if linha is None or linha[0] is None else int(linha[0])
        if maxima < ultima:
            raise ErroOrigemRestaurada(
                f"{nome}: o cursor do destino está em {ultima}, mas a outbox da origem vai só "
                f"até {maxima}; a origem foi restaurada de uma cópia anterior (ou o ponto de "
                "partida da inscrição está errado). Nada foi entregue."
            )
        return
    linha = origem.execute("SELECT id FROM outbox WHERE sequencia = %s", (ultima,)).fetchone()
    if linha is None or linha[0] != ultimo_id:
        encontrado = "nenhum fato" if linha is None else f"o fato {linha[0]}"
        raise ErroOrigemRestaurada(
            f"{nome}: o último fato entregue ({ultimo_id}, sequência {ultima}) não está mais na "
            f"outbox da origem (lá está {encontrado}); a origem foi restaurada de uma cópia "
            "anterior a essa entrega. Nada foi entregue; siga o procedimento de restauração."
        )


def entregar(
    origem: Conexao,
    destino: Conexao,
    inscricao: Inscricao,
    *,
    lote: int = 500,
    espera_maxima: timedelta = timedelta(seconds=30),
    intervalo: timedelta = timedelta(milliseconds=50),
) -> ResultadoEntrega:
    """Uma rodada de entrega da ``inscricao``, numa transação no ``destino``.

    ``origem`` em ``autocommit`` (cada leitura com *snapshot* novo; o papel só tem ``SELECT``);
    ``destino`` sem transação aberta: esta função abre e confirma a sua. Chame de novo enquanto
    ``lidos`` for maior ou igual a ``lote``, ou ``aguardando`` for verdadeiro. Destino fora do ar: a
    exceção do psycopg sobe, e nada avança (a transação do destino não confirma).
    """
    if not origem.autocommit:
        raise ValueError("a conexão de origem tem de estar em autocommit")
    if not destino.closed and destino.info.transaction_status != pq.TransactionStatus.IDLE:
        raise ValueError("a conexão de destino não pode ter transação aberta")
    if lote < 1:
        raise ValueError("lote tem de ser positivo")
    with destino.transaction():
        cursor = ler_cursor(destino, inscricao.origem, travar=True)
        antes = cursor.ultima_sequencia

        vazio = ResultadoEntrega(inscricao.origem, antes, antes, 0, 0, 0, 0, aguardando=False)
        _conferir_cursor(origem, inscricao.origem, antes, cursor.ultimo_id)
        visiveis = origem.execute(
            "SELECT sequencia FROM outbox WHERE sequencia > %s ORDER BY sequencia LIMIT %s",
            (antes, lote),
        ).fetchall()
        if not visiveis:
            return vazio
        maxima = int(visiveis[-1][0])
        if not _esperar_escritores(origem, espera_maxima, intervalo):
            return replace(vazio, aguardando=True)
        linhas = origem.execute(
            "SELECT sequencia, id, tenant_id, tipo, versao, origem, instante, correlacao, causa, "
            "conteudo::text FROM outbox WHERE sequencia > %s AND sequencia <= %s "
            "ORDER BY sequencia",
            (antes, maxima),
        ).fetchall()
        if not linhas or int(linhas[-1][0]) != maxima:
            raise ErroEntrega(f"{inscricao.origem}: a sequência {maxima} sumiu da outbox")
        inseridos = repetidos = ignorados = 0
        for linha in linhas:
            sequencia, id_fato, tenant, tipo, versao, origem_fato, *resto = linha
            if origem_fato != inscricao.origem:
                raise ErroEntrega(
                    f"a outbox lida como {inscricao.origem} tem fato de {origem_fato!r} "
                    f"(sequência {sequencia}); conexão ou inscrição trocada"
                )
            if not inscricao.aceita(str(tipo), int(versao)):
                ignorados += 1
                continue
            inserido = destino.execute(
                INSERIR_NA_INBOX,
                (id_fato, tenant, tipo, versao, origem_fato, *resto, sequencia),
            )
            if inserido.rowcount == 1:
                inseridos += 1
            else:
                repetidos += 1
        avancar_cursor(destino, inscricao.origem, maxima, linhas[-1][1])
        return ResultadoEntrega(
            inscricao.origem,
            antes,
            maxima,
            lidos=len(linhas),
            inseridos=inseridos,
            repetidos=repetidos,
            ignorados=ignorados,
            aguardando=False,
        )


__all__ = [
    "ErroEntrega",
    "ErroOrigemRestaurada",
    "Inscricao",
    "ResultadoEntrega",
    "entregar",
]
