"""Formatos de apresentação (``blatt.web.apresentacao``; PLAT-0021, item 6)."""

from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from blatt.comum.periodo import AnoMes
from blatt.web.apresentacao import (
    cnpj,
    competencia,
    cpf,
    cpf_oculto,
    data,
    data_hora,
    moeda,
    numero,
)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("1234.56", "1.234,56"),
        ("1234.5", "1.234,50"),
        ("0", "0,00"),
        ("-0.00", "0,00"),
        ("-1234567.89", "-1.234.567,89"),
        ("0.1", "0,10"),
        ("1.230", "1,23"),
        ("1E+3", "1.000,00"),
        ("999", "999,00"),
    ],
)
def test_moeda(valor: str, esperado: str) -> None:
    assert moeda(Decimal(valor)) == esperado


def test_moeda_com_simbolo() -> None:
    assert moeda(Decimal("10"), simbolo=True) == "R$ 10,00"


def test_moeda_nao_arredonda() -> None:
    with pytest.raises(ValueError, match="mais de 2 casas"):
        moeda(Decimal("1.005"))
    assert numero(Decimal("1.005"), 3) == "1,005"
    assert numero(Decimal("0.075"), 4) == "0,0750"
    assert numero(Decimal("12345"), 0) == "12.345"


def test_moeda_recusa_float_e_nao_finito() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        moeda(3 / 2)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Decimal"):
        moeda(1)  # type: ignore[arg-type]
    for valor in ("NaN", "Infinity"):
        with pytest.raises(ValueError, match="não finito"):
            moeda(Decimal(valor))


def test_datas() -> None:
    assert data(date(2026, 1, 5)) == "05/01/2026"
    assert data_hora(datetime(2026, 11, 13, 9, 5, tzinfo=UTC)) == "13/11/2026 09:05"
    fuso = timezone(timedelta(hours=-3))
    assert data_hora(datetime(2026, 11, 13, 23, 59, tzinfo=fuso)) == "13/11/2026 23:59"
    with pytest.raises(TypeError):
        data("2026-01-05")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        data_hora(date(2026, 1, 5))  # type: ignore[arg-type]


def test_competencia() -> None:
    assert competencia(AnoMes(2026, 10)) == "10/2026"
    assert competencia(date(2026, 3, 31)) == "03/2026"
    assert competencia("2026-01") == "01/2026"
    with pytest.raises(ValueError, match="AAAA-MM"):
        competencia("10/2026")
    with pytest.raises(TypeError):
        competencia(202610)  # type: ignore[arg-type]


def test_cnpj() -> None:
    assert cnpj("12345678000195") == "12.345.678/0001-95"
    assert cnpj("12.345.678/0001-95") == "12.345.678/0001-95"
    assert cnpj("12abc34501de35") == "12.ABC.345/01DE-35"
    for invalido in ("1234567800019", "123456780001A5", "\uff11" * 14):
        with pytest.raises(ValueError, match="14 posições"):
            cnpj(invalido)


def test_cpf() -> None:
    assert cpf("12345678909") == "123.456.789-09"
    assert cpf("123.456.789-09") == "123.456.789-09"
    assert cpf_oculto("12345678909") == "***.456.789-**"
    for invalido in ("1234567890", "1234567890A"):
        with pytest.raises(ValueError, match="11 posições"):
            cpf(invalido)
