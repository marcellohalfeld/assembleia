"""Configuração da instância, lida do ambiente num único ponto.

``BLATT_TENANT_ID`` identifica o escritório (ADR 0004): na instância única é constante e
nenhum código de negócio o lê diretamente; ele chega aos repositórios por aqui.
"""

import os
import uuid
from collections.abc import Mapping


class ErroConfiguracao(Exception):
    """Variável de configuração ausente ou inválida."""


def tenant_id(ambiente: Mapping[str, str] | None = None) -> uuid.UUID:
    valor = (os.environ if ambiente is None else ambiente).get("BLATT_TENANT_ID", "")
    if not valor:
        raise ErroConfiguracao("defina BLATT_TENANT_ID (UUID do escritório desta instância)")
    try:
        return uuid.UUID(valor)
    except ValueError:
        raise ErroConfiguracao(f"BLATT_TENANT_ID não é um UUID: {valor!r}") from None


def dsn_postgres(ambiente: Mapping[str, str] | None = None) -> str:
    """Conexão ao PostgreSQL (``BLATT_DSN``, no formato aceito pelo libpq)."""
    valor = (os.environ if ambiente is None else ambiente).get("BLATT_DSN", "")
    if not valor:
        raise ErroConfiguracao("defina BLATT_DSN (ex.: 'host=/var/run/postgresql dbname=blatt')")
    return valor


def dsn_modulo(modulo: str, ambiente: Mapping[str, str] | None = None) -> str:
    """Conexão ao banco próprio de um módulo (ADR 0014, itens 1 e 11).

    Lê ``BLATT_DSN_<MODULO>``, com o nome do módulo em maiúsculas e pontos trocados por
    sublinhado: ``fiscal.aspirador`` → ``BLATT_DSN_FISCAL_ASPIRADOR``.
    """
    variavel = "BLATT_DSN_" + modulo.upper().replace(".", "_")
    valor = (os.environ if ambiente is None else ambiente).get(variavel, "")
    if not valor:
        raise ErroConfiguracao(
            f"defina {variavel} (ex.: 'host=/var/run/postgresql dbname=fiscal_aspirador')"
        )
    return valor
