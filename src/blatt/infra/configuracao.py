"""Configuração da instância, lida do ambiente num único ponto (PLAT-0017, item 5).

``BLATT_TENANT_ID`` identifica o escritório (ADR 0004): na instância única é constante e
nenhum código de negócio o lê diretamente; ele chega aos repositórios por aqui.

Variáveis lidas (valores na instância: ``docs/contrato-imagem-modulo.md`` do ``oper``):

- ``BLATT_TENANT_ID``, ``BLATT_DSN`` e ``BLATT_DSN_<MODULO>`` (0.1.0);
- ``BLATT_DIR_ARQUIVO``: raiz do arquivo imutável do módulo (PLAT-0022, item 1; ``/arquivo``
  no container);
- ``BLATT_DIR_DADOS``: pasta de trabalho persistente do módulo (``/dados`` no container);
- ``BLATT_DIR_PARAMETROS``: pasta dos parâmetros legais (PLAT-0003); sem ela, ``parametros``
  relativo à pasta de trabalho;
- ``BLATT_WEB_NAVEGACAO``: itens do menu entre módulos da interface web (PLAT-0021), no formato
  ``Título=/caminho/;Outro=/outro/``.

Cada função recebe o ambiente como parâmetro opcional (para os testes) e, sem ele, lê
``os.environ``. Erro de configuração é sempre ``ErroConfiguracao``, com o nome da variável.
"""

import os
import re
import uuid
from collections.abc import Mapping
from pathlib import Path


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


def _ler(variavel: str, ambiente: Mapping[str, str] | None) -> str:
    return (os.environ if ambiente is None else ambiente).get(variavel, "")


def _pasta_existente(variavel: str, valor: str) -> Path:
    pasta = Path(valor)
    if not pasta.is_absolute():
        raise ErroConfiguracao(f"{variavel} tem de ser caminho absoluto: {valor!r}")
    if not pasta.is_dir():
        raise ErroConfiguracao(f"{variavel} não é uma pasta existente: {valor!r}")
    return pasta


def dir_arquivo_opcional(ambiente: Mapping[str, str] | None = None) -> Path | None:
    """Raiz do arquivo imutável (``BLATT_DIR_ARQUIVO``), ou ``None`` se não definida.

    Para o módulo que funciona também sem arquivo imutável (a linha de comando da folha sem
    banco, por exemplo). Definida, tem de ser caminho absoluto de uma pasta que existe: o
    arquivo imutável nunca é criado por engano na pasta de trabalho.
    """
    valor = _ler("BLATT_DIR_ARQUIVO", ambiente)
    return _pasta_existente("BLATT_DIR_ARQUIVO", valor) if valor else None


def dir_arquivo(ambiente: Mapping[str, str] | None = None) -> Path:
    """Raiz do arquivo imutável (``BLATT_DIR_ARQUIVO``), obrigatória."""
    pasta = dir_arquivo_opcional(ambiente)
    if pasta is None:
        raise ErroConfiguracao("defina BLATT_DIR_ARQUIVO (raiz do arquivo imutável, ex.: /arquivo)")
    return pasta


def dir_dados_opcional(ambiente: Mapping[str, str] | None = None) -> Path | None:
    """Pasta de trabalho persistente do módulo (``BLATT_DIR_DADOS``), ou ``None``."""
    valor = _ler("BLATT_DIR_DADOS", ambiente)
    return _pasta_existente("BLATT_DIR_DADOS", valor) if valor else None


def dir_dados(ambiente: Mapping[str, str] | None = None) -> Path:
    """Pasta de trabalho persistente do módulo (``BLATT_DIR_DADOS``), obrigatória."""
    pasta = dir_dados_opcional(ambiente)
    if pasta is None:
        raise ErroConfiguracao("defina BLATT_DIR_DADOS (pasta de trabalho do módulo, ex.: /dados)")
    return pasta


def dir_parametros(ambiente: Mapping[str, str] | None = None) -> Path:
    """Pasta dos parâmetros legais (``BLATT_DIR_PARAMETROS``).

    Sem a variável, ``parametros`` relativo à pasta de trabalho, como na linha de comando dos
    módulos. Não confere se a pasta existe: o carregador de parâmetros de cada módulo dá o erro
    com o contexto dele.
    """
    valor = _ler("BLATT_DIR_PARAMETROS", ambiente)
    return Path(valor) if valor else Path("parametros")


_ITEM_NAVEGACAO = re.compile(r"^([^=;]+)=(/[A-Za-z0-9._~/-]*)$")


def navegacao_web(ambiente: Mapping[str, str] | None = None) -> tuple[tuple[str, str], ...]:
    """Itens do menu entre módulos (``BLATT_WEB_NAVEGACAO``), como pares (título, caminho).

    Formato: ``Início=/;Folha=/folha/;Fiscal=/fiscal/``. Sem a variável, tupla vazia (a base
    web mostra só o próprio módulo). Caminho tem de começar por ``/``: o menu nunca aponta para
    fora da instância.
    """
    valor = _ler("BLATT_WEB_NAVEGACAO", ambiente).strip()
    if not valor:
        return ()
    itens = []
    for parte in valor.split(";"):
        casamento = _ITEM_NAVEGACAO.fullmatch(parte.strip())
        if casamento is None or not casamento.group(1).strip():
            raise ErroConfiguracao(
                f"BLATT_WEB_NAVEGACAO: item fora do formato 'Título=/caminho/': {parte!r}"
            )
        itens.append((casamento.group(1).strip(), casamento.group(2)))
    return tuple(itens)
