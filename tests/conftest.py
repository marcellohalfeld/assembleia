"""Fixtures compartilhadas: PostgreSQL temporário (mesmo padrão da folha e do aspirador)."""

import os
import uuid
from collections.abc import Callable, Iterator

import psycopg
import pytest
from psycopg.rows import TupleRow

from tests.postgres_teste import servidor_temporario


@pytest.fixture(scope="session")
def servidor_postgres() -> Iterator[str]:
    with servidor_temporario() as conninfo:
        if conninfo is None:
            if os.environ.get("BLATT_EXIGIR_POSTGRES") == "1":
                pytest.fail("PostgreSQL exigido (BLATT_EXIGIR_POSTGRES=1), mas não encontrado")
            pytest.skip("PostgreSQL não disponível; defina BLATT_TESTE_DSN ou instale o servidor")
        yield conninfo


@pytest.fixture
def dsn_banco(servidor_postgres: str) -> Iterator[str]:
    """Banco novo e vazio (sem migrações) para cada teste; apagado ao final."""
    nome = f"teste_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(f"{servidor_postgres} dbname=postgres", autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{nome}"')
    try:
        yield f"{servidor_postgres} dbname={nome}"
    finally:
        with psycopg.connect(f"{servidor_postgres} dbname=postgres", autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


@pytest.fixture
def banco(dsn_banco: str) -> Iterator[psycopg.Connection[TupleRow]]:
    """Conexão a um banco novo e vazio; cada teste aplica as migrações fictícias que quiser."""
    with psycopg.connect(dsn_banco) as conexao:
        yield conexao


@pytest.fixture
def criar_banco(servidor_postgres: str) -> Iterator[Callable[[], str]]:
    """Fábrica de bancos novos e vazios (origem e destino de uma entrega, por exemplo); devolve
    o conninfo de cada um. Todos são apagados ao final do teste."""
    criados: list[str] = []

    def criar() -> str:
        nome = f"teste_{uuid.uuid4().hex[:12]}"
        with psycopg.connect(f"{servidor_postgres} dbname=postgres", autocommit=True) as admin:
            admin.execute(f'CREATE DATABASE "{nome}"')
        criados.append(nome)
        return f"{servidor_postgres} dbname={nome}"

    try:
        yield criar
    finally:
        with psycopg.connect(f"{servidor_postgres} dbname=postgres", autocommit=True) as admin:
            for nome in criados:
                admin.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')
