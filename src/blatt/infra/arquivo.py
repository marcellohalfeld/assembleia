"""Arquivo imutável: gravar uma vez e ler conferindo o SHA-256 (PLAT-0022, item 1.2).

Generalização de ``blatt.folha.adaptadores.arquivo_imutavel.PastaImutavel`` (P-65 da folha),
sem o layout de pastas e sem o índice no banco, que continuam sendo de cada módulo: aqui só se
grava e se lê, com segurança, um caminho relativo dentro de uma raiz (``BLATT_DIR_ARQUIVO``,
lida por ``blatt.infra.configuracao.dir_arquivo``).

Gravação (contrato da imagem de módulo do ``oper``, item 5):

1. o conteúdo vai para um temporário **na mesma pasta do destino** (assim o arquivo herda o
   grupo do backup, que a pasta tem por *setgid*), com o modo 0640 dado por ``fchmod`` antes
   de o arquivo ficar visível (``mkstemp`` cria com 0600, que o ``umask`` não muda);
2. ``fsync`` do temporário;
3. ``os.link`` do temporário para o nome final: falha se o nome já existe, então nunca
   sobrescreve, nem numa corrida entre dois processos (``os.replace`` sobrescreveria);
4. o temporário é removido e a pasta recebe ``fsync``, para o nome sobreviver a uma queda.

O nome final só aparece com o conteúdo completo; uma queda no meio deixa no máximo um
temporário oculto (``.gravando-*.parcial``), nunca um arquivo pela metade. Mesmo conteúdo já
gravado com o mesmo nome: nada muda (``novo=False``). Conteúdo diferente com o mesmo nome:
``ErroArquivoImutavel``, e nada é sobrescrito. A leitura sempre confere o SHA-256 que o módulo
guardou no banco.

O módulo grava o arquivo **antes** da transação do banco que registra o hash (PLAT-0022, item
1.1): se o banco falhar, o arquivo fica, e gravar de novo (no-op) completa o registro.
"""

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MODO_ARQUIVO = 0o640  # dono lê e grava; grupo (backup, na instância) só lê; outros nada
MODO_PASTA = 0o750  # ainda mascarado pelo umask do processo (0027 na instância)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PARTE = re.compile(r"^[A-Za-z0-9_@+=,-][A-Za-z0-9._@+=,-]*$")


class ErroArquivoImutavel(Exception):
    """Caminho inválido, conteúdo diferente com o mesmo nome ou hash que não confere."""


@dataclass(frozen=True)
class ArquivoGravado:
    caminho: PurePosixPath  # relativo à raiz
    sha256: str
    tamanho: int
    novo: bool  # False quando o mesmo conteúdo já estava gravado


def sha256(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def _relativo(caminho: str | PurePosixPath) -> PurePosixPath:
    """Confere o caminho relativo: partes com letras, números e ``._@+=,-``; nenhuma parte
    começa por ponto (ficam de fora ``..``, arquivos ocultos e os temporários desta gravação)."""
    texto = str(caminho)
    # Confere o texto, parte por parte, antes de o PurePosixPath normalizar "a/./b" ou "a//b".
    if not texto or any(not _PARTE.fullmatch(parte) for parte in texto.split("/")):
        raise ErroArquivoImutavel(f"caminho não permitido no arquivo imutável: {texto!r}")
    return PurePosixPath(texto)


class ArquivoImutavel:
    """Arquivo imutável sob ``raiz``: grava uma vez, nunca sobrescreve, lê conferindo o hash."""

    def __init__(self, raiz: Path) -> None:
        if not raiz.is_absolute():
            raise ErroArquivoImutavel(f"a raiz do arquivo imutável tem de ser absoluta: {raiz}")
        if not raiz.is_dir():
            raise ErroArquivoImutavel(f"a raiz do arquivo imutável não existe: {raiz}")
        self._raiz = raiz
        self._raiz_real = Path(os.path.realpath(raiz))

    @property
    def raiz(self) -> Path:
        return self._raiz

    def _conferir_dentro(self, pasta: Path, relativo: PurePosixPath) -> None:
        # Uma ligação simbólica dentro da raiz não pode levar a gravação para fora dela.
        real = Path(os.path.realpath(pasta))
        if real != self._raiz_real and self._raiz_real not in real.parents:
            raise ErroArquivoImutavel(f"caminho sai do arquivo imutável: {relativo}")

    def _destino(self, relativo: PurePosixPath) -> Path:
        destino = self._raiz.joinpath(*relativo.parts)
        self._conferir_dentro(destino.parent, relativo)
        return destino

    def gravar(self, caminho: str | PurePosixPath, conteudo: bytes) -> ArquivoGravado:
        """Grava ``conteudo`` em ``caminho`` (relativo à raiz), uma vez só."""
        relativo = _relativo(caminho)
        hash_conteudo = sha256(conteudo)
        self._criar_pastas(relativo)
        destino = self._destino(relativo)
        if destino.exists():
            self._conferir_existente(destino, relativo, hash_conteudo)
            return ArquivoGravado(relativo, hash_conteudo, len(conteudo), novo=False)
        descritor, temporario = tempfile.mkstemp(
            dir=destino.parent, prefix=".gravando-", suffix=".parcial"
        )
        novo = True
        try:
            os.fchmod(descritor, MODO_ARQUIVO)
            with os.fdopen(descritor, "wb") as arquivo:
                arquivo.write(conteudo)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            try:
                os.link(temporario, destino)
            except FileExistsError:
                # Gravado por outro processo entre a conferência e a ligação.
                self._conferir_existente(destino, relativo, hash_conteudo)
                novo = False
        finally:
            os.unlink(temporario)
        _sincronizar_pasta(destino.parent)
        return ArquivoGravado(relativo, hash_conteudo, len(conteudo), novo=novo)

    def ler(self, caminho: str | PurePosixPath, sha256_esperado: str) -> bytes:
        """Conteúdo de ``caminho``, conferido com o SHA-256 guardado pelo módulo.

        Arquivo ausente: ``FileNotFoundError``; hash diferente: ``ErroArquivoImutavel``."""
        if not _SHA256.fullmatch(sha256_esperado):
            raise ErroArquivoImutavel(f"SHA-256 inválido: {sha256_esperado!r}")
        relativo = _relativo(caminho)
        conteudo = self._destino(relativo).read_bytes()
        if sha256(conteudo) != sha256_esperado:
            raise ErroArquivoImutavel(f"{relativo}: o conteúdo não confere com o SHA-256 esperado")
        return conteudo

    def existe(self, caminho: str | PurePosixPath) -> bool:
        return self._destino(_relativo(caminho)).is_file()

    def _criar_pastas(self, relativo: PurePosixPath) -> None:
        pasta = self._raiz
        for parte in relativo.parts[:-1]:
            self._conferir_dentro(pasta, relativo)
            proxima = pasta / parte
            try:
                proxima.mkdir(mode=MODO_PASTA)
            except FileExistsError:
                pass
            else:
                _sincronizar_pasta(pasta)
            pasta = proxima

    @staticmethod
    def _conferir_existente(destino: Path, relativo: PurePosixPath, esperado: str) -> None:
        if sha256(destino.read_bytes()) != esperado:
            raise ErroArquivoImutavel(
                f"{relativo} já existe com outro conteúdo; nada foi sobrescrito"
            )


def _sincronizar_pasta(pasta: Path) -> None:
    descritor = os.open(pasta, os.O_RDONLY)
    try:
        os.fsync(descritor)
    finally:
        os.close(descritor)
