"""Formulários lidos só em memória, para uploads sensíveis (PLAT-0021, item 7; PLAT-0020, 5).

O certificado A1 e a senha chegam num formulário ``multipart/form-data`` e vão ao caso de uso
**só como bytes e texto na memória do processo**: sem arquivo temporário (o ``UploadFile`` do
Starlette usa ``SpooledTemporaryFile``, que vai para disco acima de 1 MiB), sem log, com limite
de tamanho. Uso na rota do módulo, que não declara parâmetros ``File``/``Form``::

    @rotas.post("/coletar")
    async def coletar(
        request: Request,
        certificado: Annotated[CertificadoA1, Depends(formulario_certificado())],
    ) -> HTMLResponse:
        resultado = caso_de_uso.coletar(certificado.conteudo, certificado.senha, ...)
        ...

O corpo já foi lido para a memória pelo *middleware* de CSRF (``blatt.web.seguranca``), dentro
do ``limite_corpo`` da aplicação; aqui ele é separado em partes com o analisador do
``python-multipart`` (o mesmo do Starlette), sem passar por arquivo. O Python não garante
apagar a memória; o certificado deixa de existir quando o objeto deixa de ser referenciado, ao
fim da requisição. O ``repr`` nunca mostra conteúdo nem senha.
"""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from python_multipart.multipart import MultipartParser, parse_options_header
from starlette.exceptions import HTTPException
from starlette.requests import Request

MAX_PARTES = 32
MAX_CAMPO_TEXTO = 4096  # bytes de um campo comum (a senha, por exemplo)
TAMANHO_MAXIMO_CERTIFICADO = 64 * 1024  # um .pfx típico tem poucos kB


class ErroFormulario(ValueError):
    """Formulário malformado ou fora dos limites. A mensagem nunca traz o conteúdo."""


@dataclass(frozen=True, repr=False)
class Parte:
    nome: str
    nome_arquivo: str | None  # None num campo comum
    tipo: str | None
    conteudo: bytes

    def __repr__(self) -> str:
        return f"Parte({self.nome!r}, {len(self.conteudo)} bytes)"


def ler_multipart(corpo: bytes, tipo_conteudo: str, max_partes: int = MAX_PARTES) -> list[Parte]:
    """Separa um corpo ``multipart/form-data`` em partes, tudo em memória."""
    principal, opcoes = parse_options_header(tipo_conteudo)
    fronteira = opcoes.get(b"boundary")
    if principal != b"multipart/form-data" or not fronteira:
        raise ErroFormulario("o formulário tem de ser multipart/form-data")
    partes: list[Parte] = []
    cabecalhos: dict[bytes, bytes] = {}
    campo = bytearray()
    valor = bytearray()
    dados = bytearray()

    def inicio() -> None:
        cabecalhos.clear()
        dados.clear()

    def dado(bruto: bytes, comeco: int, fim: int) -> None:
        dados.extend(bruto[comeco:fim])

    def nome_cabecalho(bruto: bytes, comeco: int, fim: int) -> None:
        campo.extend(bruto[comeco:fim])

    def valor_cabecalho(bruto: bytes, comeco: int, fim: int) -> None:
        valor.extend(bruto[comeco:fim])

    def fim_cabecalho() -> None:
        cabecalhos[bytes(campo).lower()] = bytes(valor)
        campo.clear()
        valor.clear()

    def fim_parte() -> None:
        if len(partes) >= max_partes:
            raise ErroFormulario("o formulário tem partes demais")
        disposicao, parametros = parse_options_header(cabecalhos.get(b"content-disposition"))
        nome = parametros.get(b"name")
        if disposicao != b"form-data" or nome is None:
            raise ErroFormulario("parte do formulário sem Content-Disposition: form-data")
        arquivo = parametros.get(b"filename")
        tipo = cabecalhos.get(b"content-type")
        partes.append(
            Parte(
                nome.decode("utf-8", "replace"),
                None if arquivo is None else arquivo.decode("utf-8", "replace"),
                None if tipo is None else tipo.decode("latin-1"),
                bytes(dados),
            )
        )
        dados.clear()

    chamadas: Any = {
        "on_part_begin": inicio,
        "on_part_data": dado,
        "on_header_field": nome_cabecalho,
        "on_header_value": valor_cabecalho,
        "on_header_end": fim_cabecalho,
        "on_part_end": fim_parte,
    }
    analisador = MultipartParser(fronteira, chamadas)
    try:
        analisador.write(corpo)
        analisador.finalize()
    except ErroFormulario:
        raise
    except Exception:
        raise ErroFormulario("formulário multipart malformado") from None
    return partes


@dataclass(frozen=True, repr=False)
class CertificadoA1:
    """Certificado A1 e senha, só em memória, e os demais campos do formulário."""

    conteudo: bytes
    senha: str
    nome_arquivo: str | None
    campos: Mapping[str, str] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"CertificadoA1({len(self.conteudo)} bytes, senha oculta)"


def _texto(parte: Parte) -> str:
    if len(parte.conteudo) > MAX_CAMPO_TEXTO:
        raise ErroFormulario(f"o campo {parte.nome!r} passou do tamanho máximo")
    try:
        return parte.conteudo.decode("utf-8")
    except UnicodeDecodeError:
        raise ErroFormulario(f"o campo {parte.nome!r} não é texto UTF-8") from None


def certificado_do_corpo(
    corpo: bytes,
    tipo_conteudo: str,
    *,
    campo_arquivo: str = "certificado",
    campo_senha: str = "senha",
    tamanho_maximo: int = TAMANHO_MAXIMO_CERTIFICADO,
) -> CertificadoA1:
    """``CertificadoA1`` a partir do corpo do formulário; recusa o que estiver fora da forma."""
    partes = ler_multipart(corpo, tipo_conteudo)
    arquivos = [p for p in partes if p.nome == campo_arquivo]
    senhas = [p for p in partes if p.nome == campo_senha and p.nome_arquivo is None]
    if len(arquivos) != 1 or arquivos[0].nome_arquivo is None:
        raise ErroFormulario("envie um arquivo de certificado (.pfx ou .p12)")
    if len(senhas) != 1:
        raise ErroFormulario("informe a senha do certificado")
    arquivo = arquivos[0]
    if not arquivo.conteudo:
        raise ErroFormulario("o arquivo do certificado está vazio")
    if len(arquivo.conteudo) > tamanho_maximo:
        raise ErroFormulario(f"o certificado passou de {tamanho_maximo // 1024} KiB")
    campos: dict[str, str] = {}
    for parte in partes:
        if parte.nome in (campo_arquivo, campo_senha, "csrf") or parte.nome_arquivo is not None:
            continue
        if parte.nome in campos:
            raise ErroFormulario(f"o campo {parte.nome!r} veio repetido")
        campos[parte.nome] = _texto(parte)
    return CertificadoA1(arquivo.conteudo, _texto(senhas[0]), arquivo.nome_arquivo, campos)


def formulario_certificado(
    *,
    campo_arquivo: str = "certificado",
    campo_senha: str = "senha",
    tamanho_maximo: int = TAMANHO_MAXIMO_CERTIFICADO,
) -> Callable[[Request], Awaitable[CertificadoA1]]:
    """Dependência do FastAPI que entrega o ``CertificadoA1`` lido em memória (400 se inválido)."""

    async def ler(request: Request) -> CertificadoA1:
        corpo = await request.body()
        try:
            return certificado_do_corpo(
                corpo,
                request.headers.get("content-type", ""),
                campo_arquivo=campo_arquivo,
                campo_senha=campo_senha,
                tamanho_maximo=tamanho_maximo,
            )
        except ErroFormulario as erro:
            raise HTTPException(400, str(erro)) from None

    return ler
