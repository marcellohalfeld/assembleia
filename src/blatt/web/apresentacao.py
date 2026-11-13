"""Formatos de apresentação em português do Brasil, sem regra de negócio (PLAT-0021, item 6).

Só biblioteca padrão e ``blatt.comum``: pode ser usado também fora da web (relatórios, dossiês
da PLAT-0022). Registrados como filtros nos modelos pela ``criar_app``
(``{{ valor | moeda }}``, ``{{ cnpj | cnpj }}`` e assim por diante).

Dinheiro é ``Decimal``, nunca ``float``. ``moeda`` **não arredonda**: um valor com mais casas do
que as pedidas é erro, porque quem calcula arredonda, com o modo declarado (PLAT-0003, regras de
código); a tela mostra o que foi calculado.
"""

from datetime import date, datetime
from decimal import Context, Decimal, Inexact

from blatt.comum.periodo import AnoMes


def numero(valor: Decimal, casas: int = 2) -> str:
    """``Decimal("1234.5")`` → ``"1.234,50"``. Recusa ``float`` e valor com mais ``casas``."""
    if not isinstance(valor, Decimal):
        raise TypeError(f"valores de dinheiro são Decimal, não {type(valor).__name__}")
    if not valor.is_finite():
        raise ValueError(f"valor não finito: {valor}")
    if casas < 0:
        raise ValueError("casas não pode ser negativo")
    try:
        exato = valor.quantize(Decimal(1).scaleb(-casas), context=Context(traps=[Inexact]))
    except Inexact:
        raise ValueError(
            f"{valor} tem mais de {casas} casas; arredonde no cálculo, com o modo declarado"
        ) from None
    if exato.is_zero():
        exato = abs(exato)  # sem "-0,00"
    texto = format(exato, f",.{casas}f")
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def moeda(valor: Decimal, *, simbolo: bool = False) -> str:
    """``Decimal("1234.56")`` → ``"1.234,56"`` (ou ``"R$ 1.234,56"`` com ``simbolo``)."""
    texto = numero(valor, 2)
    return f"R$ {texto}" if simbolo else texto


def data(valor: date) -> str:
    """``date(2026, 11, 13)`` → ``"13/11/2026"``."""
    if not isinstance(valor, date):
        raise TypeError(f"data espera date, não {type(valor).__name__}")
    return f"{valor.day:02d}/{valor.month:02d}/{valor.year:04d}"


def data_hora(valor: datetime) -> str:
    """``datetime(2026, 11, 13, 9, 5)`` → ``"13/11/2026 09:05"``, no fuso do próprio valor."""
    if not isinstance(valor, datetime):
        raise TypeError(f"data_hora espera datetime, não {type(valor).__name__}")
    return f"{data(valor)} {valor.hour:02d}:{valor.minute:02d}"


def competencia(valor: AnoMes | date | str) -> str:
    """``AnoMes(2026, 10)``, ``date(2026, 10, 1)`` ou ``"2026-10"`` → ``"10/2026"``."""
    if isinstance(valor, str):
        valor = AnoMes.de_texto(valor)
    elif isinstance(valor, date):
        valor = AnoMes(valor.year, valor.month)
    elif not isinstance(valor, AnoMes):
        raise TypeError(f"competência espera AnoMes, date ou texto, não {type(valor).__name__}")
    return f"{valor.mes:02d}/{valor.ano:04d}"


def _so_documento(valor: str, tamanho: int, alfanumerico: bool) -> str:
    if not isinstance(valor, str):
        raise TypeError("documento é texto")
    limpo = valor.replace(".", "").replace("/", "").replace("-", "").strip().upper()
    valido = limpo.isascii() and len(limpo) == tamanho
    if alfanumerico:
        valido = valido and limpo[:-2].isalnum() and limpo[-2:].isdigit()
    else:
        valido = valido and limpo.isdigit()
    if not valido:
        raise ValueError(f"documento com formato inesperado (esperado {tamanho} posições)")
    return limpo


def cnpj(valor: str) -> str:
    """``"12345678000195"`` → ``"12.345.678/0001-95"``; aceita o CNPJ alfanumérico.

    Só formata; não confere os dígitos verificadores (``blatt.comum.documentos``)."""
    c = _so_documento(valor, 14, alfanumerico=True)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def cpf(valor: str) -> str:
    """``"12345678909"`` → ``"123.456.789-09"``. Só formata."""
    c = _so_documento(valor, 11, alfanumerico=False)
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"


def cpf_oculto(valor: str) -> str:
    """``"12345678909"`` → ``"***.456.789-**"``: para listas e telas em que o CPF inteiro não é
    necessário (dado pessoal, PLAT-0018)."""
    c = _so_documento(valor, 11, alfanumerico=False)
    return f"***.{c[3:6]}.{c[6:9]}-**"
