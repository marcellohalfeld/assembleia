"""Certificado A1 (PKCS#12) só em memória, para assinar e para TLS mútuo (PLAT-0020, item 5).

Extra ``[certificado]`` (``cryptography``). Sem regra de negócio: abre o ``.pfx``, confere que
tem chave e certificado que combinam e que está dentro da validade, e entrega ao adaptador do
módulo o que ele precisa, sem tocar disco. Conferir CNPJ, raiz do CNPJ, tipo de certificado
(e-CNPJ, e-CPF) ou cadeia ICP-Brasil é regra de cada módulo e fica com ele.

Uso, num adaptador web (o ``.pfx`` e a senha vêm de ``blatt.web.formulario``)::

    credencial = abrir_pkcs12(certificado.conteudo, certificado.senha)
    assinar(evento, credencial.chave, credencial.certificado)        # objetos do cryptography
    contexto = contexto_tls_cliente(credencial, cafile=cadeia_servidor)
    conexao = http.client.HTTPSConnection(host, context=contexto)

Por que ``memfd_create``: o ``ssl`` da biblioteca padrão só carrega o certificado do cliente de
um caminho (``SSLContext.load_cert_chain(certfile, keyfile, password)``, documentação do módulo
``ssl``: https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_cert_chain; ``cadata``
existe só para as raízes de verificação), e o ``cryptography`` não monta ``SSLContext``. No
Linux, ``os.memfd_create`` (https://docs.python.org/3/library/os.html#os.memfd_create;
``memfd_create(2)``: https://man7.org/linux/man-pages/man2/memfd_create.2.html) cria um arquivo
anônimo em memória, que não aparece em sistema de arquivos nenhum e some quando o último
descritor fecha; o OpenSSL o lê pelo caminho ``/proc/self/fd/N``. A chave vai cifrada (PKCS#8,
``BestAvailableEncryption``) com uma senha aleatória de uso único, e os dois arquivos são
selados contra escrita (``F_ADD_SEALS``, ``fcntl(2)``) antes de o caminho ser entregue. É a
técnica do aspirador (``adaptadores/adn.py``, P-42 e ASP-0009 de lá), sem o plano B.

**Fora do Linux não há plano B:** sem ``os.memfd_create`` (macOS, Windows), com ele bloqueado
(``seccomp`` do container, por exemplo) ou sem ``/proc``, ``pem_em_memoria`` e
``contexto_tls_cliente`` levantam ``ErroSemMemoriaAnonima`` e não gravam arquivo temporário.
``abrir_pkcs12`` e a assinatura com ``credencial.chave`` funcionam em qualquer sistema.

Limites do que se garante: o Python não apaga a memória; chave e certificado deixam de existir
quando os objetos deixam de ser referenciados. Enquanto um ``pem_em_memoria`` está aberto, um
processo do mesmo usuário com permissão de ``ptrace`` sobre este consegue abrir
``/proc/<pid>/fd/N`` (``proc(5)``), como conseguiria ler a memória do processo; a chave que ele
leria está cifrada com uma senha que só existe na memória deste processo. Nada aqui registra em
log; mensagens de erro e ``repr`` nunca trazem conteúdo, chave nem senha.
"""

import fcntl
import os
import secrets
import ssl
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    pkcs12,
)

# Um .pfx típico (chave RSA 2048 e três ou quatro certificados) tem poucos kB; o mesmo limite de
# ``blatt.web.formulario.TAMANHO_MAXIMO_CERTIFICADO``.
TAMANHO_MAXIMO_PFX = 64 * 1024

ChavePrivada = RSAPrivateKey | EllipticCurvePrivateKey


class ErroCertificado(ValueError):
    """O ``.pfx`` não pôde ser usado. A mensagem nunca traz o conteúdo nem a senha."""


class ErroCertificadoForaDaValidade(ErroCertificado):
    """O certificado venceu ou ainda não começou a valer."""


class ErroSemMemoriaAnonima(RuntimeError):
    """O sistema não oferece arquivo anônimo em memória (``memfd_create`` e ``/proc``)."""


@dataclass(frozen=True, repr=False)
class CredencialA1:
    """Chave privada e certificado do titular (e a cadeia que veio no ``.pfx``), só em memória.

    ``chave`` e ``certificado`` são objetos do ``cryptography``, prontos para assinar. O
    ``repr`` mostra só a validade: nem chave, nem titular (o nome de um e-CPF é dado pessoal).
    """

    chave: ChavePrivada
    certificado: x509.Certificate
    cadeia: tuple[x509.Certificate, ...] = ()

    @property
    def inicio_validade(self) -> datetime:
        return self.certificado.not_valid_before_utc

    @property
    def fim_validade(self) -> datetime:
        return self.certificado.not_valid_after_utc

    def certificado_pem(self, *, com_cadeia: bool = False) -> bytes:
        """Certificado do titular em PEM; com ``com_cadeia``, seguido dos da cadeia do ``.pfx``."""
        certificados = (self.certificado, *self.cadeia) if com_cadeia else (self.certificado,)
        return b"".join(c.public_bytes(Encoding.PEM) for c in certificados)

    def __repr__(self) -> str:
        return (
            f"CredencialA1(válido de {self.inicio_validade:%Y-%m-%d} "
            f"a {self.fim_validade:%Y-%m-%d}, chave oculta)"
        )


def _mesma_chave_publica(chave: ChavePrivada, certificado: x509.Certificate) -> bool:
    formato = (Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    return chave.public_key().public_bytes(*formato) == certificado.public_key().public_bytes(
        *formato
    )


def abrir_pkcs12(
    conteudo: bytes,
    senha: str | bytes,
    *,
    agora: datetime | None = None,
    tamanho_maximo: int = TAMANHO_MAXIMO_PFX,
) -> CredencialA1:
    """Abre um ``.pfx``/``.p12`` em memória e confere a forma e a validade.

    Confere: tamanho (não vazio, até ``tamanho_maximo``); que é PKCS#12 e abre com a senha
    (o ``cryptography`` não distingue senha errada de arquivo que não é PKCS#12, e a mensagem
    também não); que traz chave RSA ou EC e o certificado do titular, e que a chave é a do
    certificado; que ``agora`` (padrão: o relógio, em UTC) está entre ``notBefore`` e
    ``notAfter``. Não confere CNPJ, cadeia nem revogação. Senha vazia abre ``.pfx`` sem senha.
    Levanta ``ErroCertificado`` ou ``ErroCertificadoForaDaValidade``.
    """
    if not conteudo:
        raise ErroCertificado("o arquivo do certificado está vazio")
    if len(conteudo) > tamanho_maximo:
        raise ErroCertificado(f"o certificado passou de {tamanho_maximo // 1024} KiB")
    senha_bytes = senha.encode("utf-8") if isinstance(senha, str) else senha
    try:
        chave, certificado, cadeia = pkcs12.load_key_and_certificates(conteudo, senha_bytes or None)
    except (ValueError, TypeError):
        raise ErroCertificado(
            "não foi possível abrir o certificado: senha incorreta ou arquivo que não é "
            "PKCS#12 (.pfx ou .p12)"
        ) from None
    if certificado is None or chave is None:
        raise ErroCertificado("o arquivo precisa conter a chave privada e o certificado")
    if not isinstance(chave, RSAPrivateKey | EllipticCurvePrivateKey):
        raise ErroCertificado("a chave do certificado precisa ser RSA ou de curva elíptica")
    if not _mesma_chave_publica(chave, certificado):
        raise ErroCertificado("a chave privada do arquivo não é a do certificado")
    credencial = CredencialA1(chave, certificado, tuple(cadeia))
    momento = agora if agora is not None else datetime.now(UTC)
    if momento.tzinfo is None:
        raise ValueError("agora precisa ter fuso horário")
    if momento < credencial.inicio_validade:
        raise ErroCertificadoForaDaValidade(
            f"o certificado só vale a partir de {credencial.inicio_validade:%d/%m/%Y %H:%M} UTC"
        )
    if momento > credencial.fim_validade:
        raise ErroCertificadoForaDaValidade(
            f"o certificado venceu em {credencial.fim_validade:%d/%m/%Y %H:%M} UTC"
        )
    return credencial


@dataclass(frozen=True, repr=False)
class PemEmMemoria:
    """Caminhos ``/proc/self/fd/N`` do certificado e da chave em PEM, válidos só dentro do
    ``with``. ``senha_chave`` decifra a chave (``None`` se ela foi pedida sem cifra)."""

    certificado: str
    chave: str
    senha_chave: bytes | None

    def __repr__(self) -> str:
        return f"PemEmMemoria({self.certificado!r}, {self.chave!r}, senha oculta)"


# Valores da interface do Linux com o programa (estáveis; ``include/uapi/linux/fcntl.h`` e
# ``include/uapi/linux/memfd.h`` do kernel; ``fcntl(2)`` e ``memfd_create(2)``). Servem quando o
# Python foi compilado com cabeçalhos antigos e não traz os nomes em ``fcntl`` e ``os``: sem
# eles, o selo seria pulado em silêncio.
_F_ADD_SEALS = 1033  # F_LINUX_SPECIFIC_BASE (1024) + 9
_SELOS = {"F_SEAL_SEAL": 0x1, "F_SEAL_SHRINK": 0x2, "F_SEAL_GROW": 0x4, "F_SEAL_WRITE": 0x8}
_MFD_CLOEXEC = 0x1
_MFD_ALLOW_SEALING = 0x2


def _selos() -> int:
    selos = 0
    for nome, valor in _SELOS.items():
        selos |= getattr(fcntl, nome, valor)
    return selos


def _arquivo_anonimo(nome: str, conteudo: bytes) -> int:
    """Arquivo anônimo em memória com ``conteudo``, selado contra escrita e fechado ao executar
    outro programa (``MFD_CLOEXEC``). Some quando o último descritor fecha."""
    criar = getattr(os, "memfd_create", None)
    if criar is None:
        raise ErroSemMemoriaAnonima(
            "este sistema não tem os.memfd_create (só Linux); o certificado não vai para "
            "arquivo temporário"
        )
    opcoes = getattr(os, "MFD_CLOEXEC", _MFD_CLOEXEC) | getattr(
        os, "MFD_ALLOW_SEALING", _MFD_ALLOW_SEALING
    )
    try:
        descritor: int = criar(nome, opcoes)
    except OSError as erro:
        raise ErroSemMemoriaAnonima(
            f"memfd_create recusado pelo sistema ({erro.strerror}); o certificado não vai "
            "para arquivo temporário"
        ) from None
    try:
        vista = memoryview(conteudo)
        escrito = 0
        while escrito < len(vista):
            escrito += os.write(descritor, vista[escrito:])
        try:
            fcntl.fcntl(descritor, getattr(fcntl, "F_ADD_SEALS", _F_ADD_SEALS), _selos())
        except OSError as erro:
            raise ErroSemMemoriaAnonima(
                f"o sistema recusou selar o arquivo anônimo ({erro.strerror}); o certificado "
                "não vai para arquivo temporário"
            ) from None
        caminho = f"/proc/self/fd/{descritor}"
        try:
            os.stat(caminho)
        except OSError:
            raise ErroSemMemoriaAnonima(
                "sem /proc/self/fd, o OpenSSL não alcança o arquivo anônimo; o certificado não "
                "vai para arquivo temporário"
            ) from None
    except BaseException:
        os.close(descritor)
        raise
    return descritor


@contextmanager
def pem_em_memoria(
    credencial: CredencialA1, *, com_cadeia: bool = False, cifrar_chave: bool = True
) -> Iterator[PemEmMemoria]:
    """Certificado e chave em PEM, em arquivos anônimos em memória, pelo tempo do ``with``.

    Para bibliotecas que só aceitam caminho (``ssl.SSLContext.load_cert_chain``,
    ``xmlsec.Key.from_file`` e afins). A chave vai em PKCS#8 cifrada com uma senha aleatória
    de 32 bytes (``senha_chave``); ``cifrar_chave=False`` só para quem não aceita senha. Na saída
    do ``with``, com ou sem erro, os descritores são fechados e os arquivos deixam de existir.
    Levanta ``ErroSemMemoriaAnonima`` fora do Linux, sem cair em arquivo temporário.
    """
    senha = secrets.token_bytes(32) if cifrar_chave else None
    cifra = BestAvailableEncryption(senha) if senha is not None else NoEncryption()
    chave_pem = credencial.chave.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, cifra)
    descritores: list[int] = []
    try:
        descritores.append(
            _arquivo_anonimo("blatt-certificado", credencial.certificado_pem(com_cadeia=com_cadeia))
        )
        descritores.append(_arquivo_anonimo("blatt-chave", chave_pem))
        del chave_pem
        yield PemEmMemoria(
            f"/proc/self/fd/{descritores[0]}", f"/proc/self/fd/{descritores[1]}", senha
        )
    finally:
        for descritor in descritores:
            os.close(descritor)


def contexto_tls_cliente(
    credencial: CredencialA1,
    *,
    cafile: str | os.PathLike[str] | None = None,
    versao_minima: ssl.TLSVersion = ssl.TLSVersion.TLSv1_2,
    com_cadeia: bool = False,
) -> ssl.SSLContext:
    """``SSLContext`` de cliente com TLS mútuo pelo A1, carregado sem arquivo em disco.

    Verificação do servidor sempre ligada (``ssl.create_default_context``: ``CERT_REQUIRED`` e
    ``check_hostname``). Com ``cafile``, só essas raízes valem, sem as do sistema (é o que a
    FOLHA-0013 usa para o eSocial); sem ele, as do sistema. Os arquivos anônimos fecham logo
    depois do ``load_cert_chain``: o contexto guarda a chave na memória do OpenSSL. Levanta
    ``ErroSemMemoriaAnonima`` fora do Linux e ``ssl.SSLError`` se o OpenSSL recusar a chave.
    """
    contexto = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=cafile)
    contexto.minimum_version = versao_minima
    with pem_em_memoria(credencial, com_cadeia=com_cadeia) as pem:
        contexto.load_cert_chain(pem.certificado, pem.chave, password=pem.senha_chave)
    return contexto
