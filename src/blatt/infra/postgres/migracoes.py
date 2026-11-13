"""Migrações em SQL puro, versionadas e com hash (ADR 0009).

Cada arquivo ``sql/NNNN_descricao.sql`` do pacote informado é uma migração. Pela ADR 0014
(item 2), cada módulo tem a sua sequência no próprio pacote e aplica no próprio banco. O pacote
é obrigatório: o ``blatt-plataforma`` não traz migração de módulo nenhum, e um padrão apontaria
para um pacote sem ``sql/`` (PLAT-0016, item 4). Todas as pendentes são aplicadas
numa única transação, sob um lock consultivo, e registradas em ``public.blatt_migracao``
com o SHA-256 do conteúdo. Uma migração já aplicada nunca muda: se o arquivo divergir do
hash registrado, nada é aplicado e o erro diz qual arquivo foi alterado.
"""

import hashlib
import re
from dataclasses import dataclass
from importlib.resources import files

import psycopg
from psycopg.rows import TupleRow

_NOME = re.compile(r"^([0-9]{4})_([a-z0-9_]+)\.sql$")
_LOCK = 724_100_301  # identificador fixo do lock consultivo das migrações do Blatt


class ErroMigracao(RuntimeError):
    pass


@dataclass(frozen=True)
class Migracao:
    versao: int
    nome: str
    sql: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.sql.encode()).hexdigest()


def disponiveis(pacote: str) -> list[Migracao]:
    """Migrações do diretório ``sql`` do ``pacote``, em ordem; a numeração tem de ser contínua
    desde 0001."""
    encontradas = []
    for arquivo in files(pacote).joinpath("sql").iterdir():
        casamento = _NOME.fullmatch(arquivo.name)
        if casamento is None:
            if arquivo.name.endswith(".sql"):
                raise ErroMigracao(f"nome de migração fora do padrão NNNN_nome.sql: {arquivo.name}")
            continue
        encontradas.append(
            Migracao(int(casamento.group(1)), casamento.group(2), arquivo.read_text("utf-8"))
        )
    encontradas.sort(key=lambda m: m.versao)
    esperadas = list(range(1, len(encontradas) + 1))
    if [m.versao for m in encontradas] != esperadas:
        raise ErroMigracao(
            f"numeração das migrações não é contínua: {[m.versao for m in encontradas]}"
        )
    return encontradas


def aplicar(conexao: psycopg.Connection[TupleRow], pacote: str) -> list[int]:
    """Aplica as migrações pendentes do ``pacote``. Devolve as versões aplicadas agora."""
    migracoes = disponiveis(pacote)
    with conexao.transaction():
        conexao.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK,))
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS public.blatt_migracao (
                versao integer PRIMARY KEY,
                nome text NOT NULL,
                sha256 char(64) NOT NULL,
                aplicada_em timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        aplicadas = _aplicadas(conexao)
        _conferir_aplicadas(migracoes, aplicadas)
        novas = [m for m in migracoes if m.versao not in aplicadas]
        for migracao in novas:
            conexao.execute(migracao.sql.encode())
            conexao.execute(
                "INSERT INTO public.blatt_migracao (versao, nome, sha256) VALUES (%s, %s, %s)",
                (migracao.versao, migracao.nome, migracao.sha256),
            )
    return [m.versao for m in novas]


def _aplicadas(conexao: psycopg.Connection[TupleRow]) -> dict[int, str]:
    return {
        versao: sha
        for versao, sha in conexao.execute(
            "SELECT versao, sha256 FROM public.blatt_migracao"
        ).fetchall()
    }


def _conferir_aplicadas(migracoes: list[Migracao], aplicadas: dict[int, str]) -> None:
    alteradas = [
        m.versao for m in migracoes if m.versao in aplicadas and aplicadas[m.versao] != m.sha256
    ]
    if alteradas:
        raise ErroMigracao(f"migrações já aplicadas foram alteradas: {alteradas}")
    desconhecidas = sorted(set(aplicadas) - {m.versao for m in migracoes})
    if desconhecidas:
        raise ErroMigracao(f"o banco tem migrações que este código não conhece: {desconhecidas}")


def conferir(conexao: psycopg.Connection[TupleRow], pacote: str) -> list[int]:
    """Confere, **sem alterar nada**, as migrações aplicadas no banco contra as do ``pacote``.

    Para o comando de verificação que o teste de restauração do ``oper`` chama contra um banco
    restaurado (contrato da imagem de módulo, item 8; PLAT-0022, item 5.1; P-65 da folha).
    Levanta ``ErroMigracao`` se uma migração aplicada foi alterada, se o banco tem migração que
    o código não conhece ou se o banco nunca foi migrado (sem ``public.blatt_migracao``).
    Devolve as versões ainda pendentes (lista vazia: banco em dia).
    """
    migracoes = disponiveis(pacote)
    tabela = conexao.execute("SELECT to_regclass('public.blatt_migracao')").fetchone()
    if tabela is None or tabela[0] is None:
        raise ErroMigracao("o banco não tem public.blatt_migracao: nenhuma migração aplicada")
    aplicadas = _aplicadas(conexao)
    _conferir_aplicadas(migracoes, aplicadas)
    return [m.versao for m in migracoes if m.versao not in aplicadas]
