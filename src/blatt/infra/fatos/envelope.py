"""Envelope dos fatos (PLAT-0019, item 4): tipo, validação e serialização em JSON.

O conteúdo é JSON puro: texto, inteiro, booleano, nulo, listas e objetos com chave de texto.
**Nunca ``float``** (nem ``Decimal``): dinheiro e alíquotas vão como texto decimal
(``texto_decimal``), datas e competências como texto (``AAAA-MM-DD``, ``AAAA-MM``). O schema de
cada tipo é do módulo que publica (``contratos/eventos/<tipo>/<versao>.schema.json``); aqui só
se confere a forma do envelope, sem regra de negócio.
"""

import json
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Self

type ValorJson = bool | int | str | Sequence[ValorJson] | Mapping[str, ValorJson] | None

# Fato no passado, com o módulo como prefixo: "fiscal.documento_coletado".
_TIPO = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
# Nome do módulo que publica: "folha", "fiscal.aspirador".
_ORIGEM = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
_CAMPOS = (
    "id",
    "tipo",
    "versao",
    "tenant_id",
    "origem",
    "instante",
    "correlacao",
    "causa",
    "conteudo",
)


class ErroEnvelope(ValueError):
    """Envelope fora do contrato da PLAT-0019, item 4."""


def texto_decimal(valor: Decimal) -> str:
    """Dinheiro ou alíquota como texto decimal (``Decimal("1234.50")`` → ``"1234.50"``).

    Mantém as casas do ``Decimal`` (nenhum arredondamento aqui: quem calcula arredonda, com o
    modo declarado). Recusa ``float``, infinito e NaN.
    """
    if not isinstance(valor, Decimal):
        raise ErroEnvelope(f"texto_decimal recebe Decimal, não {type(valor).__name__}")
    if not valor.is_finite():
        raise ErroEnvelope(f"valor decimal não finito: {valor}")
    return format(valor, "f")


def _conferir_conteudo(valor: object, caminho: str) -> ValorJson:
    """Cópia do conteúdo, recusando o que não é JSON puro sem números fracionários."""
    if valor is None or isinstance(valor, str | bool):
        return valor
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float | Decimal):
        raise ErroEnvelope(
            f"{caminho}: número fracionário ({type(valor).__name__}) no conteúdo; "
            "dinheiro vai como texto decimal (texto_decimal)"
        )
    if isinstance(valor, Mapping):
        copia: dict[str, ValorJson] = {}
        for chave, item in valor.items():
            if not isinstance(chave, str):
                raise ErroEnvelope(f"{caminho}: chave não é texto: {chave!r}")
            copia[chave] = _conferir_conteudo(item, f"{caminho}.{chave}")
        return copia
    if isinstance(valor, list | tuple):
        return [_conferir_conteudo(item, f"{caminho}[{n}]") for n, item in enumerate(valor)]
    raise ErroEnvelope(f"{caminho}: tipo não permitido no conteúdo: {type(valor).__name__}")


def conteudo_json(valor: object) -> dict[str, ValorJson]:
    """Cópia conferida de um conteúdo de fato: objeto JSON puro, sem número fracionário."""
    if not isinstance(valor, Mapping):
        raise ErroEnvelope("conteudo tem de ser um objeto JSON")
    copia = _conferir_conteudo(valor, "conteudo")
    assert isinstance(copia, dict)  # noqa: S101 - _conferir_conteudo devolve dict para Mapping
    return copia


def _recusar_float(texto: str) -> Any:
    raise ErroEnvelope(f"número fracionário no conteúdo ({texto}); dinheiro vai como texto")


def _recusar_constante(texto: str) -> Any:
    raise ErroEnvelope(f"constante não permitida em JSON: {texto}")


def ler_json(texto: str | bytes) -> Any:
    """``json.loads`` estrito: recusa número fracionário, ``NaN``/``Infinity`` e chave repetida."""

    def sem_repeticao(pares: list[tuple[str, Any]]) -> dict[str, Any]:
        resultado: dict[str, Any] = {}
        for chave, valor in pares:
            if chave in resultado:
                raise ErroEnvelope(f"chave repetida no JSON: {chave!r}")
            resultado[chave] = valor
        return resultado

    return json.loads(
        texto,
        parse_float=_recusar_float,
        parse_constant=_recusar_constante,
        object_pairs_hook=sem_repeticao,
    )


def _uuid(valor: object, campo: str) -> uuid.UUID:
    if isinstance(valor, uuid.UUID):
        return valor
    if isinstance(valor, str):
        try:
            return uuid.UUID(valor)
        except ValueError:
            pass
    raise ErroEnvelope(f"{campo} não é um UUID: {valor!r}")


@dataclass(frozen=True)
class Envelope:
    """Um fato, como vai para a ``outbox`` e chega à ``inbox``."""

    id: uuid.UUID
    tipo: str
    versao: int
    tenant_id: uuid.UUID
    origem: str
    instante: datetime
    correlacao: uuid.UUID
    causa: uuid.UUID | None
    conteudo: Mapping[str, ValorJson] = field(hash=False)

    def __post_init__(self) -> None:
        for campo in ("id", "tenant_id", "correlacao"):
            if not isinstance(getattr(self, campo), uuid.UUID):
                raise ErroEnvelope(f"{campo} tem de ser uuid.UUID")
        if self.causa is not None and not isinstance(self.causa, uuid.UUID):
            raise ErroEnvelope("causa tem de ser uuid.UUID ou None")
        if self.causa == self.id:
            raise ErroEnvelope("um fato não pode ser a própria causa")
        if not isinstance(self.tipo, str) or not _TIPO.fullmatch(self.tipo):
            raise ErroEnvelope(f"tipo fora do padrão 'modulo.fato_no_passado': {self.tipo!r}")
        if not isinstance(self.origem, str) or not _ORIGEM.fullmatch(self.origem):
            raise ErroEnvelope(f"origem fora do padrão de nome de módulo: {self.origem!r}")
        if isinstance(self.versao, bool) or not isinstance(self.versao, int) or self.versao < 1:
            raise ErroEnvelope(f"versao tem de ser inteiro positivo: {self.versao!r}")
        if not isinstance(self.instante, datetime) or self.instante.utcoffset() is None:
            raise ErroEnvelope("instante tem de ser datetime com fuso horário")
        object.__setattr__(self, "conteudo", conteudo_json(self.conteudo))

    @classmethod
    def novo(
        cls,
        *,
        tipo: str,
        versao: int,
        tenant_id: uuid.UUID,
        origem: str,
        correlacao: uuid.UUID,
        conteudo: Mapping[str, ValorJson],
        causa: uuid.UUID | None = None,
        instante: datetime | None = None,
    ) -> Self:
        """Fato novo, com ``id`` aleatório e, sem ``instante``, o instante atual em UTC."""
        return cls(
            id=uuid.uuid4(),
            tipo=tipo,
            versao=versao,
            tenant_id=tenant_id,
            origem=origem,
            instante=datetime.now(UTC) if instante is None else instante,
            correlacao=correlacao,
            causa=causa,
            conteudo=conteudo,
        )

    def para_json(self) -> dict[str, ValorJson]:
        """Objeto JSON do envelope; UUIDs e instante (ISO 8601 com fuso) como texto."""
        return {
            "id": str(self.id),
            "tipo": self.tipo,
            "versao": self.versao,
            "tenant_id": str(self.tenant_id),
            "origem": self.origem,
            "instante": self.instante.isoformat(),
            "correlacao": str(self.correlacao),
            "causa": None if self.causa is None else str(self.causa),
            "conteudo": self.conteudo,
        }

    def para_texto(self) -> str:
        """JSON do envelope em uma linha, com chaves ordenadas (estável para hash e diff)."""
        return json.dumps(
            self.para_json(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    @classmethod
    def de_json(cls, dados: Mapping[str, object]) -> Self:
        """Lê o objeto de ``para_json``; exige exatamente os campos do envelope."""
        if not isinstance(dados, Mapping):
            raise ErroEnvelope("o envelope tem de ser um objeto JSON")
        faltando = [c for c in _CAMPOS if c not in dados]
        sobrando = sorted(set(dados) - set(_CAMPOS))
        if faltando or sobrando:
            raise ErroEnvelope(f"campos do envelope: faltam {faltando}, sobram {sobrando}")
        instante = dados["instante"]
        if not isinstance(instante, str):
            raise ErroEnvelope(f"instante tem de ser texto ISO 8601: {instante!r}")
        try:
            lido = datetime.fromisoformat(instante)
        except ValueError:
            raise ErroEnvelope(f"instante fora do ISO 8601: {instante!r}") from None
        causa = dados["causa"]
        tipo, origem, versao = dados["tipo"], dados["origem"], dados["versao"]
        if not isinstance(tipo, str) or not isinstance(origem, str):
            raise ErroEnvelope("tipo e origem têm de ser texto")
        if isinstance(versao, bool) or not isinstance(versao, int):
            raise ErroEnvelope(f"versao tem de ser inteiro positivo: {versao!r}")
        return cls(
            id=_uuid(dados["id"], "id"),
            tipo=tipo,
            versao=versao,
            tenant_id=_uuid(dados["tenant_id"], "tenant_id"),
            origem=origem,
            instante=lido,
            correlacao=_uuid(dados["correlacao"], "correlacao"),
            causa=None if causa is None else _uuid(causa, "causa"),
            conteudo=conteudo_json(dados["conteudo"]),
        )

    @classmethod
    def de_texto(cls, texto: str | bytes) -> Self:
        dados = ler_json(texto)
        if not isinstance(dados, dict):
            raise ErroEnvelope("o envelope tem de ser um objeto JSON")
        return cls.de_json(dados)
