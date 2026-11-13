"""Executor de migrações (``blatt.infra.postgres.migracoes``; PLAT-0009, PLAT-0017).

Adaptados de ``tests/test_migracoes.py`` da folha e de ``tests/fiscal/aspirador/test_banco.py``
do aspirador, com migrações fictícias (``tests/migracoes_teste``) no lugar das de cada módulo:
o pacote ``blatt-plataforma`` não traz migração de módulo nenhum.
"""

import inspect
from importlib.resources import files

import psycopg
import pytest
from psycopg.rows import TupleRow

from blatt.infra.postgres import migracoes
from blatt.infra.postgres.migracoes import ErroMigracao, Migracao, aplicar, conferir, disponiveis

VALIDAS = "tests.migracoes_teste.validas"
SO_A_PRIMEIRA = "tests.migracoes_teste.so_a_primeira"
LACUNA = "tests.migracoes_teste.lacuna"
NOME_FORA_DO_PADRAO = "tests.migracoes_teste.nome_fora_do_padrao"
OUTRO_MODULO = "tests.migracoes_teste.outro_modulo"


def _tabelas(banco: psycopg.Connection[TupleRow]) -> set[str]:
    linhas = banco.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    ).fetchall()
    return {linha[0] for linha in linhas}


# --- sem banco -------------------------------------------------------------------------------


def test_pacote_das_migracoes_e_obrigatorio() -> None:
    """Sem padrão: o pacote de plataforma não tem migrações, e cada módulo informa as suas."""
    for funcao in (disponiveis, aplicar):
        parametro = inspect.signature(funcao).parameters["pacote"]
        assert parametro.default is inspect.Parameter.empty
    assert not hasattr(migracoes, "PACOTE_PADRAO")


def test_pacote_de_plataforma_nao_traz_migracoes() -> None:
    assert not files("blatt.infra.postgres").joinpath("sql").is_dir()


def test_numeracao_continua() -> None:
    encontradas = disponiveis(VALIDAS)
    assert [(m.versao, m.nome) for m in encontradas] == [(1, "tabela"), (2, "coluna")]


def test_numeracao_com_lacuna_e_recusada() -> None:
    with pytest.raises(ErroMigracao, match=r"não é contínua: \[1, 3\]"):
        disponiveis(LACUNA)


def test_nome_fora_do_padrao_e_recusado() -> None:
    with pytest.raises(ErroMigracao, match=r"2_Segunda\.sql"):
        disponiveis(NOME_FORA_DO_PADRAO)


def test_sha256_e_do_conteudo() -> None:
    primeira = disponiveis(VALIDAS)[0]
    assert primeira.sha256 == disponiveis(SO_A_PRIMEIRA)[0].sha256
    assert Migracao(1, "tabela", primeira.sql + " ").sha256 != primeira.sha256


# --- com banco -------------------------------------------------------------------------------


def test_aplica_e_registra(banco: psycopg.Connection[TupleRow]) -> None:
    assert aplicar(banco, VALIDAS) == [1, 2]
    assert {"exemplo", "blatt_migracao"} <= _tabelas(banco)
    registradas = banco.execute(
        "SELECT versao, nome, sha256 FROM public.blatt_migracao ORDER BY versao"
    ).fetchall()
    assert registradas == [(m.versao, m.nome, m.sha256) for m in disponiveis(VALIDAS)]


def test_aplicar_de_novo_nao_faz_nada(banco: psycopg.Connection[TupleRow]) -> None:
    aplicar(banco, VALIDAS)
    assert aplicar(banco, VALIDAS) == []


def test_aplica_so_as_pendentes(banco: psycopg.Connection[TupleRow]) -> None:
    """Banco que parou na 0001 recebe só a 0002 (caso da 0002 do aspirador)."""
    assert aplicar(banco, SO_A_PRIMEIRA) == [1]
    assert aplicar(banco, VALIDAS) == [2]


def test_aplica_so_o_pacote_informado(banco: psycopg.Connection[TupleRow]) -> None:
    aplicar(banco, OUTRO_MODULO)
    tabelas = _tabelas(banco)
    assert "outra" in tabelas
    assert "exemplo" not in tabelas


def test_migracao_alterada_depois_de_aplicada_e_recusada(
    banco: psycopg.Connection[TupleRow], monkeypatch: pytest.MonkeyPatch
) -> None:
    aplicar(banco, VALIDAS)
    originais = disponiveis(VALIDAS)
    alterada = [
        Migracao(m.versao, m.nome, m.sql + "\n-- mexi") if m.versao == 1 else m for m in originais
    ]
    monkeypatch.setattr(migracoes, "disponiveis", lambda pacote: alterada)
    with pytest.raises(ErroMigracao, match=r"alteradas: \[1\]"):
        aplicar(banco, VALIDAS)


def test_banco_a_frente_do_codigo_e_recusado(banco: psycopg.Connection[TupleRow]) -> None:
    aplicar(banco, VALIDAS)
    with pytest.raises(ErroMigracao, match=r"não conhece: \[2\]"):
        aplicar(banco, SO_A_PRIMEIRA)


def test_falha_no_meio_nao_deixa_nada_aplicado(
    banco: psycopg.Connection[TupleRow], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Todas as pendentes numa transação só: se uma falha, nenhuma fica registrada."""
    quebrada = [*disponiveis(VALIDAS), Migracao(3, "quebrada", "SELECT * FROM nao_existe;")]
    monkeypatch.setattr(migracoes, "disponiveis", lambda pacote: quebrada)
    with pytest.raises(psycopg.errors.UndefinedTable):
        aplicar(banco, VALIDAS)
    banco.rollback()
    assert _tabelas(banco) == set()


# --- conferir (só leitura; P-65 da folha, contrato da imagem do oper, item 8) -----------------


def test_conferir_banco_em_dia(banco: psycopg.Connection[TupleRow]) -> None:
    aplicar(banco, VALIDAS)
    banco.commit()
    assert conferir(banco, VALIDAS) == []


def test_conferir_mostra_as_pendentes_sem_aplicar(banco: psycopg.Connection[TupleRow]) -> None:
    aplicar(banco, SO_A_PRIMEIRA)
    assert conferir(banco, VALIDAS) == [2]
    assert "nome" not in {
        linha[0]
        for linha in banco.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'exemplo'"
        ).fetchall()
    }


def test_conferir_banco_nunca_migrado(banco: psycopg.Connection[TupleRow]) -> None:
    with pytest.raises(ErroMigracao, match="nenhuma migração aplicada"):
        conferir(banco, VALIDAS)
    assert _tabelas(banco) == set()


def test_conferir_recusa_alterada_e_desconhecida(
    banco: psycopg.Connection[TupleRow], monkeypatch: pytest.MonkeyPatch
) -> None:
    aplicar(banco, VALIDAS)
    with pytest.raises(ErroMigracao, match=r"não conhece: \[2\]"):
        conferir(banco, SO_A_PRIMEIRA)
    alterada = [Migracao(m.versao, m.nome, m.sql + "\n-- mexi") for m in disponiveis(VALIDAS)]
    monkeypatch.setattr(migracoes, "disponiveis", lambda pacote: alterada)
    with pytest.raises(ErroMigracao, match=r"alteradas: \[1, 2\]"):
        conferir(banco, VALIDAS)
