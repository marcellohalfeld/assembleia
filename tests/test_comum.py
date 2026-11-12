"""Tipos de ``blatt.comum``.

Na folha e no aspirador estes tipos são exercitados por testes do próprio negócio
(``Competencia``, entidades do cadastro, rubricas e lotações do eSocial). Aqui ficam os mesmos
casos, aplicados direto às funções comuns: ``tests/test_parametros_dominio.py``,
``tests/test_cadastro.py`` e ``tests/test_esocial_tabelas.py`` da folha.
"""

import pytest

from blatt.comum.documentos import cnpj_base_valida, cnpj_valido, cpf_valido
from blatt.comum.periodo import AnoMes
from blatt.comum.texto import (
    exigir_codigo_do_empregador,
    exigir_texto_livre,
    exigir_texto_permitido,
)

# Documentos fictícios com dígitos verificadores válidos (não pertencem a ninguém real).
CNPJ = "11222333000181"
CPF = "52998224725"
# Exemplo de CNPJ alfanumérico divulgado pela Receita Federal (12.ABC.345/01DE-35); citado de
# memória, a conferir. Os verificadores conferem pela regra da IN RFB 2.229/2024.
CNPJ_ALFANUMERICO = "12ABC34501DE35"

# --- AnoMes ----------------------------------------------------------------------------------


def test_ano_mes_le_e_escreve() -> None:
    assert AnoMes.de_texto("2026-01") == AnoMes(2026, 1)
    assert str(AnoMes(2025, 12)) == "2025-12"


@pytest.mark.parametrize(
    "texto", ["2026-13", "2026-1", "26-01", "2026-00", " 2026-01", "2026-01\n"]
)
def test_ano_mes_invalido(texto: str) -> None:
    with pytest.raises(ValueError):
        AnoMes.de_texto(texto)


@pytest.mark.parametrize(("ano", "mes"), [(2026, 0), (2026, 13), (1899, 1), (10000, 1)])
def test_ano_mes_fora_do_intervalo(ano: int, mes: int) -> None:
    with pytest.raises(ValueError):
        AnoMes(ano, mes)


def test_virada_de_ano() -> None:
    assert AnoMes(2025, 12).seguinte() == AnoMes(2026, 1)
    assert AnoMes(2026, 1).seguinte() == AnoMes(2026, 2)


def test_ordem() -> None:
    assert AnoMes(2025, 12) < AnoMes(2026, 1) < AnoMes(2026, 2)


def test_subclasse_preserva_o_tipo() -> None:
    """A folha deriva ``Competencia`` e ``MesPagamento``; ``seguinte`` e ``de_texto`` devolvem
    a subclasse, e subclasses irmãs não se comparam."""

    class Competencia(AnoMes):
        pass

    class MesPagamento(AnoMes):
        pass

    assert type(Competencia.de_texto("2026-01").seguinte()) is Competencia
    with pytest.raises(TypeError):
        _ = Competencia(2026, 1) < MesPagamento(2026, 2)  # type: ignore[operator]


# --- CPF e CNPJ ------------------------------------------------------------------------------


def test_cpf() -> None:
    assert cpf_valido(CPF)
    assert not cpf_valido("52998224726")


@pytest.mark.parametrize(
    "cpf", ["11111111111", "5299822472", "529982247250", "٥٢٩٩٨٢٢٤٧٢٥", "52998224725\n"]
)
def test_cpf_recusado(cpf: str) -> None:
    assert not cpf_valido(cpf)


def test_cnpj() -> None:
    assert cnpj_valido(CNPJ)
    assert not cnpj_valido("11222333000180")


def test_cnpj_alfanumerico() -> None:
    assert cnpj_valido(CNPJ_ALFANUMERICO)
    assert not cnpj_valido("12ABC34501DE36")
    assert not cnpj_valido("12abc34501de35")


@pytest.mark.parametrize(
    "cnpj", ["00000000000000", "1122233300018", "11222333000181\n", "1122233300018A"]
)
def test_cnpj_recusado(cnpj: str) -> None:
    assert not cnpj_valido(cnpj)


@pytest.mark.parametrize("base", ["11222333", "12ABC345"])
def test_raiz_do_cnpj(base: str) -> None:
    assert cnpj_base_valida(base)


@pytest.mark.parametrize("base", ["1122233", "112223330", "abcdefgh", "11222333\n", "١١٢٢٢٣٣٣"])
def test_raiz_do_cnpj_recusada(base: str) -> None:
    assert not cnpj_base_valida(base)


# --- Texto do eSocial ------------------------------------------------------------------------


def test_regra_de_caracteres_especiais() -> None:
    exigir_texto_permitido("x", "Ação nº 1 - ok? (R$ 1.000,00) § ©")
    travessao, espaco_sem_quebra = chr(0x2013), chr(0xA0)
    for ruim in [
        "texto ",
        " texto",
        f"a{espaco_sem_quebra}b",
        "a\nb",
        "a\tb",
        f"a {travessao} b",
        "½",
    ]:
        with pytest.raises(ValueError):
            exigir_texto_permitido("x", ruim)


@pytest.mark.parametrize("codigo", ["", "eSocial01", "ESOCIALX", "x" * 31, " LOT", "LOT\t1"])
def test_codigo_do_empregador_invalido(codigo: str) -> None:
    with pytest.raises(ValueError, match="lotação"):
        exigir_codigo_do_empregador("código de lotação", codigo, 30)


def test_codigo_do_empregador_valido() -> None:
    exigir_codigo_do_empregador("código de lotação", "LOT01", 30)
    exigir_codigo_do_empregador("código de lotação", "x" * 30, 30)


@pytest.mark.parametrize("texto", ["Salario\tmensal", "Salário ", " Salário", "a\nb", ""])
def test_texto_livre_recusa_controle_e_espaco_nas_pontas(texto: str) -> None:
    with pytest.raises(ValueError):
        exigir_texto_livre("descrição", texto, 100)


def test_texto_livre_aceita_o_que_a_regra_de_caracteres_recusaria() -> None:
    """dscRubr e observacao não têm a REGRA_CARACTERE_ESPECIAL no leiaute."""
    exigir_texto_livre("descrição", "Salário – mensal", 100)  # noqa: RUF001
    with pytest.raises(ValueError, match="1 a 10"):
        exigir_texto_livre("descrição", "x" * 11, 10)
