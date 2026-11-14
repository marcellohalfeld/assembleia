"""Certificado A1 em memória (``blatt.infra.certificado``; PLAT-0020, item 5).

Todos os certificados são fictícios, gerados aqui, autoassinados; nenhum é ICP-Brasil. O TLS
mútuo é conferido contra um servidor local, na própria máquina.
"""

import logging
import os
import socket
import ssl
import sys
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
    pkcs12,
)
from cryptography.x509.oid import NameOID

from blatt.infra import certificado as modulo
from blatt.infra.certificado import (
    TAMANHO_MAXIMO_PFX,
    ErroCertificado,
    ErroCertificadoForaDaValidade,
    ErroSemMemoriaAnonima,
    abrir_pkcs12,
    contexto_tls_cliente,
    pem_em_memoria,
)

SENHA = "senha-ficticia-Zq9!"
TITULAR = "EMPRESA FICTICIA LTDA:00000000000191"
AGORA = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
TEM_MEMFD = hasattr(os, "memfd_create") and os.path.isdir("/proc/self/fd")
so_linux = pytest.mark.skipif(not TEM_MEMFD, reason="memfd_create e /proc só no Linux")

ChaveTeste = rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey


def _certificado(
    chave: ChaveTeste,
    nome: str,
    *,
    inicio: datetime,
    fim: datetime,
    emissor: tuple[ChaveTeste, x509.Name] | None = None,
    dns: str | None = None,
    ac: bool = False,
) -> x509.Certificate:
    sujeito = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, nome)])
    chave_emissor, nome_emissor = emissor if emissor else (chave, sujeito)
    construtor = (
        x509.CertificateBuilder()
        .subject_name(sujeito)
        .issuer_name(nome_emissor)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(inicio)
        .not_valid_after(fim)
        .add_extension(x509.BasicConstraints(ca=ac, path_length=None), critical=True)
    )
    if dns:
        construtor = construtor.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(dns)]), critical=False
        )
    return construtor.sign(chave_emissor, hashes.SHA256())


@dataclass(frozen=True)
class Ficticio:
    chave: rsa.RSAPrivateKey
    certificado: x509.Certificate
    ac: x509.Certificate
    pfx: bytes


def _pfx(
    chave: ChaveTeste | None,
    certificado: x509.Certificate | None,
    cadeia: list[x509.Certificate] | None = None,
    senha: str = SENHA,
) -> bytes:
    cifra = BestAvailableEncryption(senha.encode()) if senha else NoEncryption()
    return pkcs12.serialize_key_and_certificates(b"ficticio", chave, certificado, cadeia, cifra)


@pytest.fixture(scope="module")
def chave_rsa() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def ficticio(chave_rsa: rsa.RSAPrivateKey) -> Ficticio:
    """A1 fictício: AC fictícia emite o certificado do titular, válido de 2026 a 2027 e hoje."""
    chave_ac = ec.generate_private_key(ec.SECP256R1())
    nome_ac = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AC FICTICIA DE TESTE")])
    inicio = datetime(2026, 1, 1, tzinfo=UTC)
    fim = max(datetime(2027, 12, 31, tzinfo=UTC), datetime.now(UTC) + timedelta(days=30))
    ac = _certificado(chave_ac, "AC FICTICIA DE TESTE", inicio=inicio, fim=fim, ac=True)
    titular = _certificado(chave_rsa, TITULAR, inicio=inicio, fim=fim, emissor=(chave_ac, nome_ac))
    return Ficticio(chave_rsa, titular, ac, _pfx(chave_rsa, titular, [ac]))


# --- abrir_pkcs12 -------------------------------------------------------------------------------


def test_abre_o_pfx_em_memoria(ficticio: Ficticio) -> None:
    credencial = abrir_pkcs12(ficticio.pfx, SENHA, agora=AGORA)
    assert credencial.certificado == ficticio.certificado
    assert credencial.cadeia == (ficticio.ac,)
    formato = (Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    assert credencial.chave.public_key().public_bytes(*formato) == (
        ficticio.chave.public_key().public_bytes(*formato)
    )
    assert credencial.inicio_validade == datetime(2026, 1, 1, tzinfo=UTC)
    assert abrir_pkcs12(ficticio.pfx, SENHA.encode()).certificado == ficticio.certificado
    pem = credencial.certificado_pem()
    assert pem.count(b"BEGIN CERTIFICATE") == 1
    assert credencial.certificado_pem(com_cadeia=True).count(b"BEGIN CERTIFICATE") == 2


def test_pfx_sem_senha(ficticio: Ficticio) -> None:
    pfx = _pfx(ficticio.chave, ficticio.certificado, senha="")
    assert abrir_pkcs12(pfx, "", agora=AGORA).certificado == ficticio.certificado


def test_chave_de_curva_eliptica() -> None:
    chave = ec.generate_private_key(ec.SECP256R1())
    cert = _certificado(chave, "EC", inicio=AGORA - timedelta(days=1), fim=AGORA + timedelta(1))
    assert isinstance(
        abrir_pkcs12(_pfx(chave, cert), SENHA, agora=AGORA).chave, ec.EllipticCurvePrivateKey
    )


def test_senha_errada(ficticio: Ficticio) -> None:
    with pytest.raises(ErroCertificado, match="senha incorreta") as erro:
        abrir_pkcs12(ficticio.pfx, "outra senha", agora=AGORA)
    assert erro.value.__cause__ is None


@pytest.mark.parametrize(
    "conteudo",
    [b"isto nao e um pkcs12", b"\x30\x03\x02\x01\x03", b"-----BEGIN CERTIFICATE-----\n"],
)
def test_arquivo_que_nao_e_pkcs12(conteudo: bytes) -> None:
    with pytest.raises(ErroCertificado, match="não é PKCS#12"):
        abrir_pkcs12(conteudo, SENHA, agora=AGORA)


def test_vazio_e_acima_do_limite(ficticio: Ficticio) -> None:
    with pytest.raises(ErroCertificado, match="vazio"):
        abrir_pkcs12(b"", SENHA)
    with pytest.raises(ErroCertificado, match="64 KiB"):
        abrir_pkcs12(b"\x30" * (TAMANHO_MAXIMO_PFX + 1), SENHA)
    with pytest.raises(ErroCertificado, match="1 KiB"):
        abrir_pkcs12(ficticio.pfx, SENHA, tamanho_maximo=1024)
    assert len(ficticio.pfx) > 1024


def test_limite_igual_ao_do_formulario() -> None:
    formulario = pytest.importorskip("blatt.web.formulario")
    assert formulario.TAMANHO_MAXIMO_CERTIFICADO == TAMANHO_MAXIMO_PFX


def test_vencido_e_ainda_nao_valido(ficticio: Ficticio) -> None:
    with pytest.raises(ErroCertificadoForaDaValidade, match="venceu em 31/12/2027"):
        abrir_pkcs12(ficticio.pfx, SENHA, agora=datetime(2028, 1, 1, tzinfo=UTC))
    with pytest.raises(ErroCertificadoForaDaValidade, match="a partir de 01/01/2026"):
        abrir_pkcs12(ficticio.pfx, SENHA, agora=datetime(2025, 12, 31, tzinfo=UTC))
    with pytest.raises(ValueError, match="fuso"):
        abrir_pkcs12(ficticio.pfx, SENHA, agora=datetime(2026, 11, 14))


def test_vencido_pelo_relogio(chave_rsa: rsa.RSAPrivateKey) -> None:
    """Sem ``agora``, vale o relógio: um certificado vencido ontem é recusado."""
    hoje = datetime.now(UTC)
    vencido = _certificado(
        chave_rsa, "VENCIDO", inicio=hoje - timedelta(days=400), fim=hoje - timedelta(days=1)
    )
    with pytest.raises(ErroCertificadoForaDaValidade, match="venceu"):
        abrir_pkcs12(_pfx(chave_rsa, vencido), SENHA)


def test_sem_chave_ou_sem_certificado(ficticio: Ficticio) -> None:
    with pytest.raises(ErroCertificado, match="chave privada e o certificado"):
        abrir_pkcs12(_pfx(None, None, [ficticio.certificado]), SENHA, agora=AGORA)


def test_chave_que_nao_e_a_do_certificado(ficticio: Ficticio) -> None:
    """O ``cryptography`` não serializa par trocado; a conferência é testada direto."""
    outra = ec.generate_private_key(ec.SECP256R1())
    assert modulo._mesma_chave_publica(ficticio.chave, ficticio.certificado)
    assert not modulo._mesma_chave_publica(outra, ficticio.certificado)


# --- sem segredo em repr, mensagem e log --------------------------------------------------------


def test_repr_e_mensagens_sem_segredo(ficticio: Ficticio, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    credencial = abrir_pkcs12(ficticio.pfx, SENHA, agora=AGORA)
    texto = repr(credencial) + str(credencial)
    assert texto.startswith("CredencialA1(válido de 2026-01-01")
    assert "FICTICIA" not in texto and "PRIVATE" not in texto
    mensagens: list[str] = []
    for conteudo, senha in ((ficticio.pfx, "errada"), (b"lixo" + SENHA.encode(), SENHA)):
        with pytest.raises(ErroCertificado) as erro:
            abrir_pkcs12(conteudo, senha, agora=AGORA)
        mensagens.append(str(erro.value) + repr(erro.value))
    if TEM_MEMFD:
        with pem_em_memoria(credencial) as pem:
            assert pem.senha_chave is not None
            assert pem.senha_chave.hex() not in repr(pem)
            assert repr(pem.senha_chave) not in repr(pem)
            mensagens.append(repr(pem))
        contexto_tls_cliente(credencial)
    juntas = "\n".join([*mensagens, caplog.text])
    assert SENHA not in juntas
    assert "errada" not in juntas
    assert ficticio.pfx[:32].hex() not in juntas and repr(ficticio.pfx[:32]) not in juntas
    assert [r for r in caplog.records if r.name.startswith("blatt")] == []


# --- pem_em_memoria -----------------------------------------------------------------------------


class SemDisco:
    """Gancho de auditoria (``sys.addaudithook``, PEP 578) que registra, enquanto ativo, toda
    abertura de arquivo e criação de arquivo ou pasta pelo Python. O gancho não sai do processo
    depois de instalado; fica inerte quando não há ninguém ativo."""

    ativa: "SemDisco | None" = None
    instalado = False
    EVENTOS = (
        "open",
        "os.mkdir",
        "os.rename",
        "os.link",
        "os.symlink",
        "os.truncate",
        "tempfile.mkstemp",
        "tempfile.mkdtemp",
        "shutil.copyfile",
    )

    def __init__(self) -> None:
        self.eventos: list[str] = []
        if not SemDisco.instalado:
            sys.addaudithook(SemDisco._gancho)
            SemDisco.instalado = True

    @staticmethod
    def _gancho(evento: str, argumentos: tuple[object, ...]) -> None:
        atual = SemDisco.ativa
        if atual is not None and evento in SemDisco.EVENTOS:
            atual.eventos.append(f"{evento}:{argumentos[0] if argumentos else ''}")

    @contextmanager
    def __call__(self) -> Iterator[None]:
        SemDisco.ativa = self
        try:
            yield
        finally:
            SemDisco.ativa = None


def _descritores() -> set[int]:
    return {int(nome) for nome in os.listdir("/proc/self/fd")}


def _numero(caminho: str) -> int:
    assert caminho.startswith("/proc/self/fd/")
    return int(caminho.rsplit("/", 1)[1])


@so_linux
def test_pem_em_memoria_sem_disco_e_fecha_ao_sair(ficticio: Ficticio) -> None:
    credencial = abrir_pkcs12(ficticio.pfx, SENHA, agora=AGORA)
    with pem_em_memoria(credencial):  # aquece imports e caches fora do gancho
        pass
    antes = _descritores()
    sem_disco = SemDisco()
    with sem_disco(), pem_em_memoria(credencial, com_cadeia=True) as pem:
        numeros = [_numero(pem.certificado), _numero(pem.chave)]
        alvos = [os.readlink(pem.certificado), os.readlink(pem.chave)]
    assert sem_disco.eventos == []
    assert alvos[0].startswith("/memfd:blatt-certificado")
    assert alvos[1].startswith("/memfd:blatt-chave")
    for numero in numeros:
        with pytest.raises(OSError):
            os.fstat(numero)
    assert _descritores() == antes


def test_o_gancho_pega_arquivo_temporario(tmp_path: Path) -> None:
    """Controle negativo: o gancho de auditoria vê o caminho que o plano B do aspirador usaria."""
    sem_disco = SemDisco()
    with sem_disco(), tempfile.TemporaryDirectory(dir=tmp_path) as pasta:
        (Path(pasta) / "chave.pem").write_bytes(b"x")
    assert any(e.startswith("tempfile.mkdtemp") for e in sem_disco.eventos)
    assert any(e.startswith("open") and e.endswith("chave.pem") for e in sem_disco.eventos)


@so_linux
def test_pem_em_memoria_conteudo_cifrado_e_selado(ficticio: Ficticio) -> None:
    credencial = abrir_pkcs12(ficticio.pfx, SENHA, agora=AGORA)
    with pem_em_memoria(credencial) as pem:
        assert Path(pem.certificado).read_bytes() == credencial.certificado_pem()
        chave_pem = Path(pem.chave).read_bytes()
        assert b"ENCRYPTED PRIVATE KEY" in chave_pem
        assert pem.senha_chave is not None and len(pem.senha_chave) == 32
        lida = load_pem_private_key(chave_pem, pem.senha_chave)
        formato = (Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
        assert lida.public_key().public_bytes(*formato) == (
            ficticio.chave.public_key().public_bytes(*formato)
        )
        escrita = os.open(pem.chave, os.O_WRONLY)
        try:
            with pytest.raises(PermissionError):
                os.write(escrita, b"x")  # F_SEAL_WRITE
        finally:
            os.close(escrita)
    with pem_em_memoria(credencial, cifrar_chave=False) as pem:
        assert pem.senha_chave is None
        sem_cifra = Path(pem.chave).read_bytes()
        assert sem_cifra.startswith(b"-----BEGIN PRIVATE KEY-----")
        assert sem_cifra == ficticio.chave.private_bytes(
            Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
        )


@so_linux
def test_pem_em_memoria_fecha_com_erro_no_meio(ficticio: Ficticio) -> None:
    credencial = abrir_pkcs12(ficticio.pfx, SENHA, agora=AGORA)
    antes = _descritores()
    with pytest.raises(RuntimeError, match="no meio"), pem_em_memoria(credencial) as pem:
        numero = _numero(pem.chave)
        raise RuntimeError("erro no meio")
    with pytest.raises(OSError):
        os.fstat(numero)
    assert _descritores() == antes


# --- fora do Linux ------------------------------------------------------------------------------


@pytest.fixture
def sem_temporario(monkeypatch: pytest.MonkeyPatch) -> None:
    """Qualquer tentativa de cair num arquivo ou pasta temporária falha o teste."""

    def proibido(*_a: object, **_k: object) -> None:
        raise AssertionError("tentou usar arquivo temporário para o A1")

    for nome in ("TemporaryDirectory", "NamedTemporaryFile", "mkstemp", "mkdtemp"):
        monkeypatch.setattr(tempfile, nome, proibido)


@pytest.mark.usefixtures("sem_temporario")
def test_sem_memfd_create_e_erro_claro(ficticio: Ficticio, monkeypatch: pytest.MonkeyPatch) -> None:
    """macOS e Windows não têm ``os.memfd_create``: erro, sem plano B em disco."""
    credencial = abrir_pkcs12(ficticio.pfx, SENHA, agora=AGORA)  # abrir funciona em todo lugar
    monkeypatch.delattr(os, "memfd_create", raising=False)
    sem_disco = SemDisco()
    with sem_disco():
        with pytest.raises(ErroSemMemoriaAnonima, match="só Linux"), pem_em_memoria(credencial):
            pass
        with pytest.raises(ErroSemMemoriaAnonima, match="só Linux"):
            contexto_tls_cliente(credencial)
    assert sem_disco.eventos == []


@so_linux
@pytest.mark.usefixtures("sem_temporario")
def test_memfd_bloqueado_e_erro_claro(ficticio: Ficticio, monkeypatch: pytest.MonkeyPatch) -> None:
    credencial = abrir_pkcs12(ficticio.pfx, SENHA, agora=AGORA)

    def bloqueado(*_a: object) -> int:
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "memfd_create", bloqueado)
    with pytest.raises(ErroSemMemoriaAnonima, match="recusado"):
        contexto_tls_cliente(credencial)


@so_linux
@pytest.mark.usefixtures("sem_temporario")
def test_sem_proc_e_erro_claro_e_fecha(ficticio: Ficticio, monkeypatch: pytest.MonkeyPatch) -> None:
    credencial = abrir_pkcs12(ficticio.pfx, SENHA, agora=AGORA)
    antes = _descritores()
    stat_original = os.stat

    def sem_proc(caminho: object, *a: object, **k: object) -> os.stat_result:
        if str(caminho).startswith("/proc/self/fd/"):
            raise FileNotFoundError(2, "No such file or directory")
        return stat_original(caminho, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "stat", sem_proc)
    with pytest.raises(ErroSemMemoriaAnonima, match="/proc/self/fd"):
        contexto_tls_cliente(credencial)
    monkeypatch.undo()
    assert _descritores() == antes


# --- TLS mútuo de verdade -----------------------------------------------------------------------


@contextmanager
def _servidor_tls(
    pasta: Path, ac_cliente: x509.Certificate
) -> Iterator[tuple[int, Path, list[x509.Certificate]]]:
    """Servidor TLS local que exige certificado de cliente emitido por ``ac_cliente``. Os
    arquivos do servidor (fictícios) podem ir para ``pasta``: não são o A1."""
    chave = ec.generate_private_key(ec.SECP256R1())
    hoje = datetime.now(UTC)
    cert = _certificado(
        chave, "localhost", inicio=hoje - timedelta(1), fim=hoje + timedelta(1), dns="localhost"
    )
    arquivo_cert = pasta / "servidor.pem"
    arquivo_chave = pasta / "servidor.key"
    arquivo_cert.write_bytes(cert.public_bytes(Encoding.PEM))
    arquivo_chave.write_bytes(
        chave.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexto.load_cert_chain(str(arquivo_cert), str(arquivo_chave))
    contexto.verify_mode = ssl.CERT_REQUIRED
    contexto.load_verify_locations(cadata=ac_cliente.public_bytes(Encoding.PEM).decode())
    vistos: list[x509.Certificate] = []
    escuta = socket.create_server(("127.0.0.1", 0))
    escuta.settimeout(10)
    porta = escuta.getsockname()[1]

    def atender() -> None:
        try:
            conexao, _ = escuta.accept()
        except OSError:
            return
        try:
            with contexto.wrap_socket(conexao, server_side=True) as tls:
                der = tls.getpeercert(binary_form=True)
                if der:
                    vistos.append(x509.load_der_x509_certificate(der))
                tls.sendall(b"ok")
        except (ssl.SSLError, OSError):
            pass

    tarefa = threading.Thread(target=atender, daemon=True)
    tarefa.start()
    try:
        yield porta, arquivo_cert, vistos
    finally:
        escuta.close()
        tarefa.join(10)


@so_linux
def test_tls_mutuo_com_o_a1_sem_disco(ficticio: Ficticio, tmp_path: Path) -> None:
    credencial = abrir_pkcs12(ficticio.pfx, SENHA, agora=AGORA)
    with _servidor_tls(tmp_path, ficticio.ac) as (porta, cadeia_servidor, vistos):
        contexto_tls_cliente(credencial, cafile=cadeia_servidor)  # aquece fora do gancho
        antes = _descritores()
        sem_disco = SemDisco()
        with sem_disco():
            contexto = contexto_tls_cliente(credencial, cafile=cadeia_servidor)
        assert sem_disco.eventos == []
        assert _descritores() == antes  # os arquivos anônimos já fecharam
        assert contexto.verify_mode is ssl.CERT_REQUIRED and contexto.check_hostname
        assert contexto.minimum_version is ssl.TLSVersion.TLSv1_2
        with (
            socket.create_connection(("127.0.0.1", porta), timeout=10) as bruto,
            contexto.wrap_socket(bruto, server_hostname="localhost") as tls,
        ):
            assert tls.recv(2) == b"ok"
    assert vistos == [ficticio.certificado]


@so_linux
def test_tls_recusa_servidor_fora_da_cadeia(ficticio: Ficticio, tmp_path: Path) -> None:
    """A verificação do servidor fica ligada: sem ``cafile`` que o reconheça, não conecta."""
    credencial = abrir_pkcs12(ficticio.pfx, SENHA, agora=AGORA)
    with _servidor_tls(tmp_path, ficticio.ac) as (porta, _cadeia, vistos):
        contexto = contexto_tls_cliente(credencial)  # raízes do sistema
        with (
            socket.create_connection(("127.0.0.1", porta), timeout=10) as bruto,
            pytest.raises(ssl.SSLCertVerificationError),
        ):
            contexto.wrap_socket(bruto, server_hostname="localhost")
    assert vistos == []


@so_linux
def test_selo_nao_depende_dos_nomes_do_python(
    ficticio: Ficticio, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Python compilado com cabeçalhos antigos pode não trazer ``F_ADD_SEALS``, ``F_SEAL_*`` e
    ``MFD_ALLOW_SEALING``; o selo usa então os valores do kernel, em vez de ser pulado."""
    import fcntl

    for nome in ("F_ADD_SEALS", "F_SEAL_SEAL", "F_SEAL_SHRINK", "F_SEAL_GROW", "F_SEAL_WRITE"):
        monkeypatch.delattr(fcntl, nome, raising=False)
    monkeypatch.delattr(os, "MFD_ALLOW_SEALING", raising=False)
    monkeypatch.delattr(os, "MFD_CLOEXEC", raising=False)
    credencial = abrir_pkcs12(ficticio.pfx, SENHA, agora=AGORA)
    with pem_em_memoria(credencial) as pem:
        escrita = os.open(pem.chave, os.O_WRONLY)
        try:
            with pytest.raises(PermissionError):
                os.write(escrita, b"x")
        finally:
            os.close(escrita)
