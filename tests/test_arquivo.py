"""Arquivo imutável (``blatt.infra.arquivo``; PLAT-0022, item 1.2).

Casos vindos de ``tests/test_arquivo_imutavel.py`` da folha (P-65), sem layout nem índice:
atomicidade, permissão, idempotência, conflito, corrida e leitura conferindo o hash.
"""

import os
import stat
import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

import pytest

from blatt.infra import arquivo
from blatt.infra.arquivo import ArquivoImutavel, ErroArquivoImutavel, sha256

CONTEUDO = b"<retorno>conteudo</retorno>"


@pytest.fixture
def imutavel(tmp_path: Path) -> ArquivoImutavel:
    raiz = tmp_path / "arquivo"
    raiz.mkdir()
    return ArquivoImutavel(raiz)


@pytest.fixture
def umask_permissivo() -> Iterator[None]:
    """O modo 0640 não pode depender do umask do processo."""
    anterior = os.umask(0o002)
    try:
        yield
    finally:
        os.umask(anterior)


def _ocultos(raiz: Path) -> list[Path]:
    return [p for p in raiz.rglob(".*")]


def test_grava_e_le(imutavel: ArquivoImutavel) -> None:
    gravado = imutavel.gravar("t/empresa/2026/11/lote-x.xml", CONTEUDO)
    assert gravado.caminho == PurePosixPath("t/empresa/2026/11/lote-x.xml")
    assert gravado.sha256 == sha256(CONTEUDO)
    assert gravado.tamanho == len(CONTEUDO)
    assert gravado.novo
    assert imutavel.existe(gravado.caminho)
    assert imutavel.ler(gravado.caminho, gravado.sha256) == CONTEUDO
    assert _ocultos(imutavel.raiz) == []


def test_modo_0640_qualquer_que_seja_o_umask(
    imutavel: ArquivoImutavel, umask_permissivo: None
) -> None:
    gravado = imutavel.gravar("a/b.xml", CONTEUDO)
    modo = stat.S_IMODE((imutavel.raiz / "a" / "b.xml").stat().st_mode)
    assert modo == 0o640
    assert gravado.novo


def test_pasta_criada_sem_permissao_para_outros(imutavel: ArquivoImutavel) -> None:
    anterior = os.umask(0o000)
    try:
        imutavel.gravar("nova/pasta/x.xml", CONTEUDO)
    finally:
        os.umask(anterior)
    for pasta in (imutavel.raiz / "nova", imutavel.raiz / "nova" / "pasta"):
        assert stat.S_IMODE(pasta.stat().st_mode) == 0o750


def test_temporario_na_mesma_pasta_do_destino(
    imutavel: ArquivoImutavel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Na instância, só o arquivo criado na pasta herda o grupo do backup (setgid)."""
    pastas: list[str] = []
    original = tempfile.mkstemp

    def espiao(**argumentos: str) -> tuple[int, str]:
        pastas.append(argumentos["dir"])
        return original(**argumentos)  # type: ignore[call-overload,no-any-return]

    monkeypatch.setattr(arquivo.tempfile, "mkstemp", espiao)
    imutavel.gravar("p/q/r.xml", CONTEUDO)
    assert [Path(p) for p in pastas] == [imutavel.raiz / "p" / "q"]


def test_mesmo_conteudo_de_novo_nao_muda_nada(imutavel: ArquivoImutavel) -> None:
    primeiro = imutavel.gravar("x.xml", CONTEUDO)
    instante = (imutavel.raiz / "x.xml").stat().st_mtime_ns
    segundo = imutavel.gravar("x.xml", CONTEUDO)
    assert (segundo.novo, segundo.sha256) == (False, primeiro.sha256)
    assert (imutavel.raiz / "x.xml").stat().st_mtime_ns == instante
    assert _ocultos(imutavel.raiz) == []


def test_conteudo_diferente_no_mesmo_nome_e_erro(imutavel: ArquivoImutavel) -> None:
    imutavel.gravar("x.xml", CONTEUDO)
    with pytest.raises(ErroArquivoImutavel, match="já existe com outro conteúdo"):
        imutavel.gravar("x.xml", b"outro")
    assert (imutavel.raiz / "x.xml").read_bytes() == CONTEUDO


def test_queda_antes_da_ligacao_nao_deixa_nada(
    imutavel: ArquivoImutavel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def queda(origem: str, destino: Path) -> None:
        raise OSError("disco cheio")

    monkeypatch.setattr(arquivo.os, "link", queda)
    with pytest.raises(OSError, match="disco cheio"):
        imutavel.gravar("pasta/x.xml", CONTEUDO)
    assert not (imutavel.raiz / "pasta" / "x.xml").exists()
    assert _ocultos(imutavel.raiz) == []


def test_queda_no_meio_da_escrita_nao_deixa_arquivo_pela_metade(
    imutavel: ArquivoImutavel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def queda(descritor: int) -> None:
        raise OSError("falha de E/S")

    monkeypatch.setattr(arquivo.os, "fsync", queda)
    with pytest.raises(OSError, match="falha de E/S"):
        imutavel.gravar("x.xml", CONTEUDO)
    assert list(imutavel.raiz.iterdir()) == []


def test_corrida_com_o_mesmo_conteudo(imutavel: ArquivoImutavel) -> None:
    """Vários gravando o mesmo arquivo ao mesmo tempo: todos terminam bem, um só é o novo."""
    resultados: list[bool] = []
    erros: list[BaseException] = []
    largada = threading.Barrier(8)

    def gravar() -> None:
        largada.wait()
        try:
            resultados.append(imutavel.gravar("corrida/x.xml", CONTEUDO).novo)
        except BaseException as erro:  # o teste só junta e confere
            erros.append(erro)

    linhas = [threading.Thread(target=gravar) for _ in range(8)]
    for linha in linhas:
        linha.start()
    for linha in linhas:
        linha.join()
    assert erros == []
    assert sorted(resultados) == [False] * 7 + [True]
    assert imutavel.ler("corrida/x.xml", sha256(CONTEUDO)) == CONTEUDO
    assert _ocultos(imutavel.raiz) == []


def test_corrida_com_conteudos_diferentes_nunca_sobrescreve(imutavel: ArquivoImutavel) -> None:
    conteudos = [f"versao {n}".encode() for n in range(8)]
    vencedores: list[bytes] = []
    recusados: list[bytes] = []
    largada = threading.Barrier(len(conteudos))

    def gravar(conteudo: bytes) -> None:
        largada.wait()
        try:
            imutavel.gravar("disputa.xml", conteudo)
            vencedores.append(conteudo)
        except ErroArquivoImutavel:
            recusados.append(conteudo)

    linhas = [threading.Thread(target=gravar, args=(c,)) for c in conteudos]
    for linha in linhas:
        linha.start()
    for linha in linhas:
        linha.join()
    assert len(vencedores) == 1
    assert len(recusados) == len(conteudos) - 1
    assert (imutavel.raiz / "disputa.xml").read_bytes() == vencedores[0]


def test_ligacao_ja_existente_na_corrida_confere_o_conteudo(
    imutavel: ArquivoImutavel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Outro processo grava o mesmo nome entre a conferência e a ligação."""
    original = os.link

    def outro_processo_antes(origem: str, destino: Path) -> None:
        Path(destino).write_bytes(b"do outro processo")
        original(origem, destino)

    monkeypatch.setattr(arquivo.os, "link", outro_processo_antes)
    with pytest.raises(ErroArquivoImutavel, match="outro conteúdo"):
        imutavel.gravar("x.xml", CONTEUDO)
    assert (imutavel.raiz / "x.xml").read_bytes() == b"do outro processo"
    assert _ocultos(imutavel.raiz) == []


def test_leitura_confere_o_hash(imutavel: ArquivoImutavel) -> None:
    gravado = imutavel.gravar("x.xml", CONTEUDO)
    (imutavel.raiz / "x.xml").chmod(0o600)
    (imutavel.raiz / "x.xml").write_bytes(b"adulterado")
    with pytest.raises(ErroArquivoImutavel, match="não confere"):
        imutavel.ler("x.xml", gravado.sha256)
    with pytest.raises(ErroArquivoImutavel, match="SHA-256 inválido"):
        imutavel.ler("x.xml", "abc")
    with pytest.raises(FileNotFoundError):
        imutavel.ler("nao-existe.xml", gravado.sha256)


@pytest.mark.parametrize(
    "caminho",
    [
        "",
        "/absoluto.xml",
        "../fora.xml",
        "a/../../fora.xml",
        "a/./b.xml",
        ".oculto.xml",
        "a/.gravando-x.parcial",
        "a//b.xml",
        "a/",
        "a\\b.xml",
        "com espaço.xml",
        "acentuação.xml",
        "quebra\n.xml",
    ],
)
def test_caminho_invalido(imutavel: ArquivoImutavel, caminho: str) -> None:
    with pytest.raises(ErroArquivoImutavel, match="caminho não permitido"):
        imutavel.gravar(caminho, CONTEUDO)
    assert list(imutavel.raiz.iterdir()) == []


def test_ligacao_simbolica_nao_leva_para_fora(imutavel: ArquivoImutavel, tmp_path: Path) -> None:
    fora = tmp_path / "fora"
    fora.mkdir()
    (imutavel.raiz / "atalho").symlink_to(fora)
    with pytest.raises(ErroArquivoImutavel, match="sai do arquivo imutável"):
        imutavel.gravar("atalho/x.xml", CONTEUDO)
    with pytest.raises(ErroArquivoImutavel, match="sai do arquivo imutável"):
        imutavel.gravar("atalho/sub/x.xml", CONTEUDO)
    assert list(fora.iterdir()) == []


def test_raiz_tem_de_ser_pasta_absoluta(tmp_path: Path) -> None:
    with pytest.raises(ErroArquivoImutavel, match="absoluta"):
        ArquivoImutavel(Path("relativa"))
    with pytest.raises(ErroArquivoImutavel, match="não existe"):
        ArquivoImutavel(tmp_path / "nao-existe")
