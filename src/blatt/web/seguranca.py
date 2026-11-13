"""Identidade, proteção contra CSRF e limite do corpo (PLAT-0021, itens 4 e 6).

São *middlewares* ASGI puros, aplicados por ``criar_app`` a toda requisição do módulo; uma
rota nova do módulo não precisa lembrar de nada. Contrato com o portal e o Caddy:
``docs/contratos/web.md``.

Identidade
    O Caddy faz ``forward_auth`` no portal e copia o usuário autenticado para o cabeçalho
    ``X-Blatt-Usuario`` (o Caddy 2.11.9 apaga o cabeçalho que vier do cliente antes de copiar
    o da resposta do portal). Sem o cabeçalho, ou com valor fora do formato, a requisição é
    recusada com 401; a rota de saúde é a única exceção. O módulo não faz login.

CSRF (formulários e htmx)
    Para POST, PUT, PATCH e DELETE, três conferências, todas obrigatórias quando aplicáveis:

    1. ``Sec-Fetch-Site``, se o navegador o mandar, tem de ser ``same-origin``;
    2. ``Origin``, se vier, tem de ter o mesmo endereço (``host[:porta]``) do ``Host``;
    3. o *token* do *cookie* ``__Host-blatt-csrf`` tem de ser igual ao enviado no cabeçalho
       ``X-Blatt-CSRF`` (o htmx o manda, pelo ``hx-headers`` do modelo base) ou no campo
       ``csrf`` do formulário (``csrf_campo()`` no modelo).

    O *cookie* é aleatório (32 bytes), ``Secure``, ``HttpOnly``, ``SameSite=Strict`` e com o
    prefixo ``__Host-`` (só desta origem, caminho ``/``, sem ``Domain``): outra origem não o lê
    nem o grava, então não consegue repetir o valor no formulário (*double submit*). Os itens 1
    e 2 barram o envio de outra origem já no navegador moderno; o item 3 cobre o navegador que
    não manda nenhum dos dois cabeçalhos. Não há segredo do servidor nem sessão no módulo.

Limite do corpo
    O corpo das requisições que gravam é lido para a memória, até ``limite_corpo`` (413 acima
    disso), para conferir o *token* do formulário sem gravar nada em disco, e repassado inteiro
    à aplicação.
"""

import hmac
import re
import secrets
from collections.abc import Awaitable, Callable, MutableMapping
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import parse_qs, urlsplit

from blatt.web.formulario import ErroFormulario, ler_multipart

type Escopo = MutableMapping[str, Any]
type Mensagem = MutableMapping[str, Any]
type Receber = Callable[[], Awaitable[Mensagem]]
type Enviar = Callable[[Mensagem], Awaitable[None]]
type Aplicacao = Callable[[Escopo, Receber, Enviar], Awaitable[None]]
type Cabecalhos = list[tuple[bytes, bytes]]
type ResponderErro = Callable[[Escopo, int, str], Awaitable[tuple[bytes, Cabecalhos]]]

CABECALHO_USUARIO = "x-blatt-usuario"
CABECALHO_CSRF = "x-blatt-csrf"
COOKIE_CSRF = "__Host-blatt-csrf"
CAMPO_CSRF = "csrf"
_ATRIBUTOS_COOKIE = "Path=/; Secure; HttpOnly; SameSite=Strict"
METODOS_QUE_GRAVAM = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Usuário como o portal o informa: texto imprimível curto, sem espaço nem controle.
_USUARIO = re.compile(r"^[A-Za-z0-9._@+-]{1,128}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")


def _cabecalho(escopo: Escopo, nome: str) -> str | None:
    alvo = nome.encode("latin-1")
    for chave, valor in escopo.get("headers", []):
        if chave.lower() == alvo:
            return bytes(valor).decode("latin-1")
    return None


def _estado(escopo: Escopo) -> MutableMapping[str, Any]:
    estado: MutableMapping[str, Any] = escopo.setdefault("state", {})
    return estado


def usuario_do_escopo(escopo: Escopo) -> str | None:
    valor = _estado(escopo).get("blatt_usuario")
    return valor if isinstance(valor, str) else None


def csrf_do_escopo(escopo: Escopo) -> str | None:
    valor = _estado(escopo).get("blatt_csrf")
    return valor if isinstance(valor, str) else None


async def _responder(enviar: Enviar, status: int, corpo: bytes, cabecalhos: Cabecalhos) -> None:
    await enviar({"type": "http.response.start", "status": status, "headers": cabecalhos})
    await enviar({"type": "http.response.body", "body": corpo})


# A página é toda servida pela própria aplicação: nada de CDN, script em linha nem eval
# (o htmx roda com allowEval=false, configurado no modelo base).
POLITICA_DE_CONTEUDO = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'"
)


class CabecalhosSeguranca:
    """Cabeçalhos de segurança em toda resposta; páginas e JSON sem cache (dado pessoal)."""

    def __init__(self, app: Aplicacao) -> None:
        self._app = app

    async def __call__(self, escopo: Escopo, receber: Receber, enviar: Enviar) -> None:
        if escopo["type"] != "http":
            await self._app(escopo, receber, enviar)
            return

        async def enviar_com_cabecalhos(mensagem: Mensagem) -> None:
            if mensagem["type"] == "http.response.start":
                cabecalhos = list(mensagem.get("headers", []))
                presentes = {bytes(chave).lower() for chave, _ in cabecalhos}
                tipos = [bytes(v) for k, v in cabecalhos if bytes(k).lower() == b"content-type"]
                tipo = tipos[0].decode("latin-1") if tipos else ""
                novos = [
                    (b"content-security-policy", POLITICA_DE_CONTEUDO.encode()),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                ]
                if tipo.startswith(("text/html", "application/json")) or not tipo:
                    novos.append((b"cache-control", b"no-store"))
                cabecalhos.extend((k, v) for k, v in novos if k not in presentes)
                mensagem["headers"] = cabecalhos
            await enviar(mensagem)

        await self._app(escopo, receber, enviar_com_cabecalhos)


class Identidade:
    """Exige ``X-Blatt-Usuario`` (posto pelo Caddy) em tudo, menos nas rotas ``livres``."""

    def __init__(self, app: Aplicacao, livres: frozenset[str], erro: ResponderErro) -> None:
        self._app = app
        self._livres = livres
        self._erro = erro

    async def __call__(self, escopo: Escopo, receber: Receber, enviar: Enviar) -> None:
        if escopo["type"] != "http" or escopo.get("path") in self._livres:
            await self._app(escopo, receber, enviar)
            return
        usuario = _cabecalho(escopo, CABECALHO_USUARIO)
        if usuario is None or not _USUARIO.fullmatch(usuario):
            corpo, cabecalhos = await self._erro(
                escopo, 401, "Acesso só pelo portal: a requisição chegou sem usuário autenticado."
            )
            await _responder(enviar, 401, corpo, cabecalhos)
            return
        _estado(escopo)["blatt_usuario"] = usuario
        await self._app(escopo, receber, enviar)


class LimiteECsrf:
    """Lê o corpo das requisições que gravam (até ``limite``) e confere o CSRF."""

    def __init__(self, app: Aplicacao, limite: int, erro: ResponderErro) -> None:
        self._app = app
        self._limite = limite
        self._erro = erro

    async def __call__(self, escopo: Escopo, receber: Receber, enviar: Enviar) -> None:
        if escopo["type"] != "http":
            await self._app(escopo, receber, enviar)
            return
        token_cookie = _token_do_cookie(escopo)
        token = token_cookie or secrets.token_urlsafe(32)
        _estado(escopo)["blatt_csrf"] = token

        async def enviar_com_cookie(mensagem: Mensagem) -> None:
            if mensagem["type"] == "http.response.start" and token_cookie is None:
                mensagem["headers"] = [
                    *mensagem.get("headers", []),
                    (b"set-cookie", f"{COOKIE_CSRF}={token}; {_ATRIBUTOS_COOKIE}".encode()),
                ]
            await enviar(mensagem)

        if escopo.get("method") not in METODOS_QUE_GRAVAM:
            await self._app(escopo, receber, enviar_com_cookie)
            return

        recusa = _origem_recusada(escopo)
        if recusa is not None:
            await self._recusar(escopo, enviar_com_cookie, 403, recusa)
            return
        corpo = await _ler_corpo(escopo, receber, self._limite)
        if corpo is None:
            mensagem = "O formulário passou do tamanho máximo aceito."
            await self._recusar(escopo, enviar_com_cookie, 413, mensagem)
            return
        recusa = _token_recusado(escopo, corpo, token_cookie)
        if recusa is not None:
            await self._recusar(escopo, enviar_com_cookie, 403, recusa)
            return

        entregue = False

        async def receber_de_novo() -> Mensagem:
            nonlocal entregue
            if not entregue:
                entregue = True
                return {"type": "http.request", "body": corpo, "more_body": False}
            return await receber()  # depois do corpo, só o aviso de desconexão

        await self._app(escopo, receber_de_novo, enviar_com_cookie)

    async def _recusar(self, escopo: Escopo, enviar: Enviar, status: int, mensagem: str) -> None:
        conteudo, cabecalhos = await self._erro(escopo, status, mensagem)
        await _responder(enviar, status, conteudo, cabecalhos)


def _token_do_cookie(escopo: Escopo) -> str | None:
    bruto = _cabecalho(escopo, "cookie")
    if not bruto:
        return None
    biscoitos: SimpleCookie = SimpleCookie()
    try:
        biscoitos.load(bruto)
    except Exception:  # cookie malformado é tratado como ausente
        return None
    morsel = biscoitos.get(COOKIE_CSRF)
    if morsel is None or not _TOKEN.fullmatch(morsel.value):
        return None
    return morsel.value


def _origem_recusada(escopo: Escopo) -> str | None:
    site = _cabecalho(escopo, "sec-fetch-site")
    if site is not None and site != "same-origin":
        return "Envio recusado: o formulário não veio desta página (Sec-Fetch-Site)."
    origem = _cabecalho(escopo, "origin")
    if origem is not None:
        host = _cabecalho(escopo, "host")
        if origem == "null" or host is None or urlsplit(origem).netloc != host:
            return "Envio recusado: o formulário veio de outro endereço (Origin)."
    return None


async def _ler_corpo(escopo: Escopo, receber: Receber, limite: int) -> bytes | None:
    """Corpo inteiro na memória, ou ``None`` se passar do ``limite``."""
    declarado = _cabecalho(escopo, "content-length")
    if declarado is not None and (not declarado.isdigit() or int(declarado) > limite):
        return None
    partes: list[bytes] = []
    total = 0
    while True:
        mensagem = await receber()
        if mensagem["type"] == "http.disconnect":
            break
        pedaco = mensagem.get("body", b"")
        total += len(pedaco)
        if total > limite:
            return None
        partes.append(pedaco)
        if not mensagem.get("more_body", False):
            break
    return b"".join(partes)


def _token_recusado(escopo: Escopo, corpo: bytes, token_cookie: str | None) -> str | None:
    if token_cookie is None:
        return "Envio recusado: sem o cookie de proteção do formulário. Abra a página de novo."
    enviado = _cabecalho(escopo, CABECALHO_CSRF)
    if enviado is None:
        enviado = _token_do_corpo(_cabecalho(escopo, "content-type") or "", corpo)
    if enviado is None or not hmac.compare_digest(enviado.encode(), token_cookie.encode()):
        return "Envio recusado: o formulário expirou ou não veio desta página. Abra-a de novo."
    return None


def _token_do_corpo(tipo: str, corpo: bytes) -> str | None:
    principal = tipo.split(";", 1)[0].strip().lower()
    if principal == "application/x-www-form-urlencoded":
        try:
            valores = parse_qs(corpo.decode("utf-8"), keep_blank_values=True, strict_parsing=False)
        except UnicodeDecodeError:
            return None
        lista = valores.get(CAMPO_CSRF, [])
        return lista[0] if len(lista) == 1 else None
    if principal == "multipart/form-data":
        try:
            partes = ler_multipart(corpo, tipo)
        except ErroFormulario:
            return None
        campos = [p for p in partes if p.nome == CAMPO_CSRF and p.nome_arquivo is None]
        if len(campos) != 1:
            return None
        try:
            return campos[0].conteudo.decode("utf-8")
        except UnicodeDecodeError:
            return None
    return None
