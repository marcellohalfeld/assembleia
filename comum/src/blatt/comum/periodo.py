"""Mês de um ano (``AAAA-MM``), base dos períodos de referência e das vigências."""

import re
from dataclasses import dataclass
from typing import Self

_PADRAO_ANO_MES = re.compile(r"^([0-9]{4})-(0[1-9]|1[0-2])$")


@dataclass(frozen=True, order=True)
class AnoMes:
    """Mês de um ano. Na folha, use ``Competencia`` ou ``MesPagamento``."""

    ano: int
    mes: int

    def __post_init__(self) -> None:
        if not 1 <= self.mes <= 12:
            raise ValueError(f"mês inválido: {self.mes}")
        if not 1900 <= self.ano <= 9999:
            raise ValueError(f"ano fora do intervalo aceito: {self.ano}")

    @classmethod
    def de_texto(cls, texto: str) -> Self:
        """Lê ``AAAA-MM``."""
        casamento = _PADRAO_ANO_MES.fullmatch(texto)
        if casamento is None:
            raise ValueError(f"{cls.__name__} deve estar no formato AAAA-MM: {texto!r}")
        return cls(int(casamento.group(1)), int(casamento.group(2)))

    def seguinte(self) -> Self:
        if self.mes == 12:
            return type(self)(self.ano + 1, 1)
        return type(self)(self.ano, self.mes + 1)

    def __str__(self) -> str:
        return f"{self.ano:04d}-{self.mes:02d}"
