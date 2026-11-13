"""Entrega de fatos (``blatt.infra.fatos.entrega``; PLAT-0019, itens 5 a 7 e 10).

Dois bancos temporários, origem e destino, com as tabelas do DDL de referência, e o entregador
conectado pelo papel ``blatt_entregador`` com as concessões do item 9 (como o provisionamento do
``oper``, OPER-0003). O teste de concorrência prova o item 7: uma transação de sequência menor
que confirma depois de uma de sequência maior não tem o fato pulado.
"""

import threading
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import timedelta

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from psycopg.rows import TupleRow

from blatt.infra.fatos import ddl
from blatt.infra.fatos.entrega import (
    ErroEntrega,
    ErroOrigemRestaurada,
    Inscricao,
    ResultadoEntrega,
    entregar,
)
from blatt.infra.fatos.envelope import Envelope
from blatt.infra.fatos.postgres import (
    avancar_cursor,
    gravar_na_outbox,
    ler_cursor,
    ler_outbox,
)

TENANT = uuid.UUID("00000000-0000-4000-8000-000000000001")
ORIGEM = "fiscal.aspirador"
COLETADO = "fiscal.documento_coletado"
INSCRICAO = Inscricao.de(ORIGEM, [COLETADO, ("fiscal.nfe_coletada", 1)])
ENTREGADOR = "blatt_entregador"


def fato(tipo: str = COLETADO, versao: int = 2, **conteudo: str) -> Envelope:
    return Envelope.novo(
        tipo=tipo,
        versao=versao,
        tenant_id=TENANT,
        origem=ORIGEM,
        correlacao=uuid.uuid4(),
        conteudo=conteudo or {"valor_servico": "1234.50"},
    )


@pytest.fixture(scope="session")
def papel_entregador(servidor_postgres: str) -> str:
    with psycopg.connect(f"{servidor_postgres} dbname=postgres", autocommit=True) as admin:
        admin.execute(
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'blatt_entregador') THEN
                    CREATE ROLE blatt_entregador LOGIN;
                END IF;
            END $$
            """
        )
    return ENTREGADOR


def _provisionar(dsn: str, sql_modulo: str) -> None:
    """Migração do módulo (com o papel já existente) e o que o provisionamento do oper faz."""
    with psycopg.connect(dsn, autocommit=True) as conexao:
        nome = conexao.info.dbname
        conexao.execute(f'REVOKE ALL ON DATABASE "{nome}" FROM PUBLIC')
        conexao.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
        conexao.execute(f'GRANT CONNECT ON DATABASE "{nome}" TO {ENTREGADOR}')
        conexao.execute(f"GRANT USAGE ON SCHEMA public TO {ENTREGADOR}")
        conexao.execute(sql_modulo.encode())
        # Uma tabela de negócio qualquer, que o entregador não pode ver.
        conexao.execute("CREATE TABLE documento (id uuid PRIMARY KEY)")


@dataclass
class Bancos:
    origem_dono: str  # conninfo do módulo que publica (dono das tabelas)
    destino_dono: str
    origem: psycopg.Connection[TupleRow]  # como blatt_entregador, autocommit
    destino: psycopg.Connection[TupleRow]  # como blatt_entregador

    def publicar(self, *fatos: Envelope) -> list[int]:
        with psycopg.connect(self.origem_dono) as conexao:
            return [gravar_na_outbox(conexao, f) for f in fatos]

    def inbox(self) -> list[tuple[uuid.UUID, int]]:
        with psycopg.connect(self.destino_dono) as conexao:
            linhas = conexao.execute(
                "SELECT id, sequencia_origem FROM inbox ORDER BY sequencia_origem"
            ).fetchall()
        return [(linha[0], linha[1]) for linha in linhas]

    def cursor(self) -> tuple[int, uuid.UUID | None]:
        with psycopg.connect(self.destino_dono) as conexao:
            atual = ler_cursor(conexao, ORIGEM)
        return atual.ultima_sequencia, atual.ultimo_id

    def entregar(self, **opcoes: object) -> ResultadoEntrega:
        return entregar(self.origem, self.destino, INSCRICAO, **opcoes)  # type: ignore[arg-type]


@pytest.fixture
def bancos(criar_banco: Callable[[], str], papel_entregador: str) -> Iterator[Bancos]:
    origem_dono, destino_dono = criar_banco(), criar_banco()
    _provisionar(origem_dono, ddl.ddl_outbox(ORIGEM))
    _provisionar(destino_dono, ddl.ddl_consumidor())
    with (
        psycopg.connect(make_conninfo(origem_dono, user=papel_entregador), autocommit=True) as o,
        psycopg.connect(make_conninfo(destino_dono, user=papel_entregador)) as d,
    ):
        yield Bancos(origem_dono, destino_dono, o, d)


# --- caminho normal ----------------------------------------------------------------------------


def test_entrega_os_tipos_inscritos_e_avanca_o_cursor(bancos: Bancos) -> None:
    coletado, outro, nfe, nfe_v2 = (
        fato(),
        fato("fiscal.nfe_cancelada", 1),
        fato("fiscal.nfe_coletada", 1),
        fato("fiscal.nfe_coletada", 2),
    )
    bancos.publicar(coletado, outro, nfe, nfe_v2)
    resultado = bancos.entregar()
    assert resultado == ResultadoEntrega(ORIGEM, 0, 4, 4, 2, 0, 2, aguardando=False)
    assert bancos.inbox() == [(coletado.id, 1), (nfe.id, 3)]
    assert bancos.cursor() == (4, nfe_v2.id)
    assert bancos.entregar() == ResultadoEntrega(ORIGEM, 4, 4, 0, 0, 0, 0, aguardando=False)


def test_copia_o_envelope_como_veio(bancos: Bancos) -> None:
    original = fato(valor_servico="0.10", texto="ação ç")
    bancos.publicar(original)
    bancos.entregar()
    with psycopg.connect(bancos.destino_dono) as conexao:
        linha = conexao.execute(
            "SELECT id, tenant_id, tipo, versao, origem, instante, correlacao, causa, "
            "conteudo::text FROM inbox"
        ).fetchone()
    with psycopg.connect(bancos.origem_dono) as conexao:
        na_origem = conexao.execute(
            "SELECT id, tenant_id, tipo, versao, origem, instante, correlacao, causa, "
            "conteudo::text FROM outbox"
        ).fetchone()
    assert linha == na_origem


def test_lotes(bancos: Bancos) -> None:
    fatos = [fato() for _ in range(5)]
    bancos.publicar(*fatos)
    assert bancos.entregar(lote=2).cursor_depois == 2
    assert bancos.entregar(lote=2).cursor_depois == 4
    assert bancos.entregar(lote=2).lidos == 1
    assert [i for i, _ in bancos.inbox()] == [f.id for f in fatos]


def test_fato_repetido_nao_duplica(bancos: Bancos) -> None:
    """Entrega "pelo menos uma vez": o cursor voltou (destino restaurado de uma cópia) e os
    fatos chegam de novo; a inbox continua com um de cada."""
    primeiro, segundo = fato(), fato()
    bancos.publicar(primeiro, segundo)
    bancos.entregar()
    with psycopg.connect(bancos.destino_dono) as conexao:
        conexao.execute("UPDATE entrega_cursor SET ultima_sequencia = 1, ultimo_id = %s",
                        (primeiro.id,))  # fmt: skip
    resultado = bancos.entregar()
    assert (resultado.inseridos, resultado.repetidos, resultado.cursor_depois) == (0, 1, 2)
    assert bancos.inbox() == [(primeiro.id, 1), (segundo.id, 2)]


def test_papel_do_entregador_nao_ve_outras_tabelas(bancos: Bancos) -> None:
    for conexao in (bancos.origem, bancos.destino):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conexao.execute("SELECT * FROM documento")
        conexao.rollback()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        bancos.origem.execute("DELETE FROM outbox")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        bancos.destino.execute("SELECT * FROM inbox")
    bancos.destino.rollback()


def test_conexoes_exigidas(bancos: Bancos) -> None:
    bancos.origem.autocommit = False
    with pytest.raises(ValueError, match="autocommit"):
        bancos.entregar()
    bancos.origem.autocommit = True
    bancos.destino.execute("SELECT 1")
    with pytest.raises(ValueError, match="transação aberta"):
        bancos.entregar()
    bancos.destino.rollback()
    with pytest.raises(ValueError, match="inscrição sem nenhum tipo"):
        Inscricao.de(ORIGEM, [])


def test_inscricao_com_a_origem_errada(bancos: Bancos) -> None:
    bancos.publicar(fato())
    with pytest.raises(ErroEntrega, match="inscrição trocada"):
        entregar(bancos.origem, bancos.destino, Inscricao.de("folha", [COLETADO]))
    assert bancos.inbox() == []


# --- item 7: fato confirmado fora de ordem -----------------------------------------------------


@pytest.mark.parametrize("preparar", [False, True], ids=["texto", "preparado"])
def test_transacao_de_sequencia_menor_confirmada_depois_nao_e_pulada(
    bancos: Bancos, preparar: bool
) -> None:
    """A reserva 1 e fica aberta; B reserva 2 e confirma. O entregador vê só o 2, espera A
    terminar e entrega os dois, em ordem. Um cursor ingênuo teria ido para 2 e perdido o 1.
    Com ``preparar``, o INSERT de A vai como comando preparado no servidor desde a primeira
    execução (o bloqueio vem da revalidação do plano, também antes da identidade)."""
    lento, rapido = fato(), fato()
    with psycopg.connect(bancos.origem_dono) as a, psycopg.connect(bancos.origem_dono) as b:
        if preparar:
            a.prepare_threshold = 0
        assert gravar_na_outbox(a, lento) == 1
        assert gravar_na_outbox(b, rapido) == 2
        b.commit()
        # O perigo: quem lê agora vê só a sequência 2.
        with psycopg.connect(bancos.origem_dono, autocommit=True) as leitor:
            assert [f.sequencia for f in ler_outbox(leitor)] == [2]

        resultado: list[ResultadoEntrega] = []
        entregador = threading.Thread(
            target=lambda: resultado.append(bancos.entregar(espera_maxima=timedelta(seconds=20)))
        )
        entregador.start()
        time.sleep(0.5)
        assert entregador.is_alive(), "o entregador tinha de estar esperando a transação A"
        assert resultado == []
        a.commit()
        entregador.join(timeout=20)
    assert resultado[0].cursor_depois == 2
    assert resultado[0].inseridos == 2
    assert bancos.inbox() == [(lento.id, 1), (rapido.id, 2)]


def test_escritor_que_nao_termina_a_tempo_nao_deixa_avancar(bancos: Bancos) -> None:
    lento, rapido = fato(), fato()
    with psycopg.connect(bancos.origem_dono) as a:
        gravar_na_outbox(a, lento)
        bancos.publicar(rapido)
        resultado = bancos.entregar(espera_maxima=timedelta(milliseconds=200))
        assert resultado.aguardando
        assert (resultado.cursor_depois, resultado.inseridos) == (0, 0)
        assert bancos.inbox() == []
        assert bancos.cursor() == (0, None)
        a.commit()
    resultado = bancos.entregar()
    assert (resultado.aguardando, resultado.cursor_depois, resultado.inseridos) == (False, 2, 2)
    assert bancos.inbox() == [(lento.id, 1), (rapido.id, 2)]


def test_escritor_desfeito_deixa_lacuna_permanente(bancos: Bancos) -> None:
    desfeito, confirmado = fato(), fato()
    with psycopg.connect(bancos.origem_dono) as a:
        gravar_na_outbox(a, desfeito)
        bancos.publicar(confirmado)
        entregador = threading.Thread(target=bancos.entregar)
        entregador.start()
        time.sleep(0.3)
        a.rollback()
        entregador.join(timeout=20)
    assert bancos.inbox() == [(confirmado.id, 2)]
    assert bancos.cursor() == (2, confirmado.id)


def test_escrita_em_savepoint_desfeito(bancos: Bancos) -> None:
    """ROLLBACK TO SAVEPOINT solta o bloqueio da subtransação; a linha dela não existe mais."""
    principal, no_savepoint, outro = fato(), fato(), fato()
    with psycopg.connect(bancos.origem_dono) as a:
        gravar_na_outbox(a, principal)
        with pytest.raises(RuntimeError), a.transaction():
            gravar_na_outbox(a, no_savepoint)
            raise RuntimeError("desfaz o savepoint")
        bancos.publicar(outro)
        assert bancos.entregar(espera_maxima=timedelta(milliseconds=200)).aguardando
        a.commit()
    bancos.entregar()
    assert bancos.inbox() == [(principal.id, 1), (outro.id, 3)]


# --- falhas: destino fora do ar e origem restaurada ---------------------------------------------


def test_destino_falha_no_meio_nada_avanca(bancos: Bancos) -> None:
    with psycopg.connect(bancos.destino_dono, autocommit=True) as dono:
        dono.execute(
            """
            CREATE FUNCTION falhar() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.tipo = 'fiscal.nfe_coletada' THEN RAISE EXCEPTION 'disco cheio'; END IF;
                RETURN NEW;
            END $$;
            CREATE TRIGGER falhar BEFORE INSERT ON inbox FOR EACH ROW EXECUTE FUNCTION falhar();
            """
        )
    bancos.publicar(fato(), fato("fiscal.nfe_coletada", 1))
    with pytest.raises(psycopg.errors.RaiseException, match="disco cheio"):
        bancos.entregar()
    assert bancos.inbox() == []
    assert bancos.cursor() == (0, None)


def test_destino_fora_do_ar(bancos: Bancos) -> None:
    bancos.publicar(fato())
    bancos.destino.close()
    with pytest.raises(psycopg.OperationalError):
        bancos.entregar()
    assert bancos.inbox() == []
    assert bancos.cursor() == (0, None)


def test_origem_restaurada_com_a_sequencia_reusada(bancos: Bancos) -> None:
    """A origem voltou a uma cópia com só o fato 1 e publicou outros depois: a sequência 2 é
    agora de outro fato. O entregador para, sem entregar nada nem mexer no cursor."""
    primeiro, segundo = fato(), fato()
    bancos.publicar(primeiro, segundo)
    bancos.entregar()
    with psycopg.connect(bancos.origem_dono) as conexao:
        conexao.execute("DELETE FROM outbox WHERE sequencia = 2")
        conexao.execute(
            "INSERT INTO outbox OVERRIDING SYSTEM VALUE SELECT 2, %s, tenant_id, tipo, versao, "
            "origem, instante, correlacao, causa, conteudo FROM outbox WHERE sequencia = 1",
            (uuid.uuid4(),),
        )
    gravar = fato()
    bancos.publicar(gravar)
    with pytest.raises(ErroOrigemRestaurada, match=r"sequência 2.*restaurada"):
        bancos.entregar()
    assert bancos.inbox() == [(primeiro.id, 1), (segundo.id, 2)]
    assert bancos.cursor() == (2, segundo.id)


def test_origem_restaurada_sem_o_ultimo_fato(bancos: Bancos) -> None:
    bancos.publicar(fato(), fato())
    bancos.entregar()
    with psycopg.connect(bancos.origem_dono) as conexao:
        conexao.execute("DELETE FROM outbox WHERE sequencia = 2")
    with pytest.raises(ErroOrigemRestaurada, match="nenhum fato"):
        bancos.entregar()
    assert bancos.cursor()[0] == 2


def test_ponto_de_partida_declarado(bancos: Bancos) -> None:
    """Inscrição nova que começa de um ponto declarado (item 8): sem id conhecido."""
    fatos = [fato(), fato(), fato()]
    bancos.publicar(*fatos)
    with psycopg.connect(bancos.destino_dono) as conexao:
        avancar_cursor(conexao, ORIGEM, 2, None)
    assert bancos.entregar().inseridos == 1
    assert bancos.inbox() == [(fatos[2].id, 3)]
    with psycopg.connect(bancos.destino_dono) as conexao:
        conexao.execute("UPDATE entrega_cursor SET ultima_sequencia = 9, ultimo_id = NULL")
    with pytest.raises(ErroOrigemRestaurada, match="vai só até 3"):
        bancos.entregar()


def test_dois_entregadores_ao_mesmo_tempo(bancos: Bancos, papel_entregador: str) -> None:
    """A linha do cursor fica travada durante a rodada: o segundo espera e não duplica nada."""
    fatos = [fato() for _ in range(3)]
    bancos.publicar(*fatos)
    with (
        psycopg.connect(make_conninfo(bancos.origem_dono, user=papel_entregador),
                        autocommit=True) as origem2,
        psycopg.connect(make_conninfo(bancos.destino_dono, user=papel_entregador)) as destino2,
    ):  # fmt: skip
        resultados: list[ResultadoEntrega] = []
        largada = threading.Barrier(2)

        def rodar(
            origem: psycopg.Connection[TupleRow], destino: psycopg.Connection[TupleRow]
        ) -> None:
            largada.wait()
            resultados.append(entregar(origem, destino, INSCRICAO))

        linhas = [
            threading.Thread(target=rodar, args=(bancos.origem, bancos.destino)),
            threading.Thread(target=rodar, args=(origem2, destino2)),
        ]
        for linha in linhas:
            linha.start()
        for linha in linhas:
            linha.join(timeout=20)
    assert sorted(r.inseridos for r in resultados) == [0, 3]
    assert [i for i, _ in bancos.inbox()] == [f.id for f in fatos]
