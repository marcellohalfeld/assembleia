"""PostgreSQL temporário para os testes (ADR 0009).

Ordem de preferência:
1. ``BLATT_TESTE_DSN``: usa um servidor já existente (cada teste cria e apaga o próprio banco);
2. binários locais (``initdb``/``pg_ctl``): sobe um cluster descartável num diretório
   temporário, ouvindo só em socket Unix; como root, roda como o usuário ``postgres``.
Sem nenhum dos dois, os testes de banco são pulados, a menos que ``BLATT_EXIGIR_POSTGRES=1``
(como no CI), caso em que falham.
"""

import glob
import os
import pwd
import shutil
import socket
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def _bindir() -> Path | None:
    if os.environ.get("BLATT_PG_BINDIR"):
        return Path(os.environ["BLATT_PG_BINDIR"])
    if shutil.which("initdb"):
        return Path(shutil.which("initdb") or "").parent
    candidatos = sorted(glob.glob("/usr/lib/postgresql/*/bin/initdb"), reverse=True)
    return Path(candidatos[0]).parent if candidatos else None


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@contextmanager
def servidor_temporario() -> Iterator[str | None]:
    """Devolve o conninfo de um servidor (sem dbname) ou None se não houver PostgreSQL."""
    if os.environ.get("BLATT_TESTE_DSN"):
        yield os.environ["BLATT_TESTE_DSN"]
        return
    bindir = _bindir()
    if bindir is None:
        yield None
        return
    como_root = os.geteuid() == 0
    prefixo = ["runuser", "-u", "postgres", "--"] if como_root else []
    raiz = Path(tempfile.mkdtemp(prefix="blatt-pg-"))
    if como_root:
        dono = pwd.getpwnam("postgres")
        os.chown(raiz, dono.pw_uid, dono.pw_gid)
    dados = raiz / "dados"
    porta = _porta_livre()

    def rodar(*argumentos: str) -> None:
        # Só binários do PostgreSQL com argumentos montados aqui; nenhuma entrada externa.
        subprocess.run(  # noqa: S603
            [*prefixo, *argumentos], check=True, capture_output=True, text=True, timeout=120
        )

    rodar(str(bindir / "initdb"), "-D", str(dados), "-U", "blatt", "--auth=trust", "-E", "UTF8")
    opcoes = f"-p {porta} -k {raiz} -c listen_addresses='' -c fsync=off"
    rodar(
        str(bindir / "pg_ctl"),
        "-D",
        str(dados),
        "-o",
        opcoes,
        "-w",
        "-l",
        str(raiz / "log"),
        "start",
    )
    try:
        yield f"host={raiz} port={porta} user=blatt"
    finally:
        rodar(str(bindir / "pg_ctl"), "-D", str(dados), "-m", "immediate", "-w", "stop")
        shutil.rmtree(raiz, ignore_errors=True)
