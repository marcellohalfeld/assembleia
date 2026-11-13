"""Fábrica da aplicação web de um módulo (PLAT-0021, itens 2, 5 e 6).

Cada módulo monta a sua aplicação com ``criar_app`` no adaptador web
(``blatt.<modulo>.adaptadores.web``) e a serve com o Uvicorn na porta 8000::

    from fastapi import APIRouter, Request
    from blatt.web.app import criar_app, renderizar

    rotas = APIRouter()

    @rotas.get("/")
    async def inicio(request: Request) -> HTMLResponse:
        return renderizar(request, "inicio.html", {"empresas": casos_de_uso.listar()})

    app = criar_app(
        modulo="folha", titulo="Folha", prefixo="/folha", versao="0.9.0",
        rotas=[rotas], modelos=[Path(__file__).parent / "modelos"],
    )

    # uvicorn blatt.folha.adaptadores.web:app --host 0.0.0.0 --port 8000 --proxy-headers

As rotas do módulo ficam **sob o prefixo** (o Caddy repassa o caminho inteiro, com ``handle``,
não ``handle_path``). A base acrescenta: ``/saude`` e ``<prefixo>/saude`` (livres de
identidade), os arquivos da base em ``<prefixo>/_blatt/`` (``blatt.css``, ``htmx.min.js``), os
do módulo em ``<prefixo>/estatico/`` (se ``estaticos`` for dado), páginas de erro, os
*middlewares* de identidade e CSRF (``blatt.web.seguranca``) e cabeçalhos de segurança.

Modelos: os do módulo têm precedência sobre os da base; a página do módulo estende
``blatt/base.html`` e preenche os blocos ``titulo`` e ``conteudo``. Nos modelos ficam
disponíveis ``usuario``, ``csrf_token``, ``csrf_campo()``, ``estatico(caminho)``,
``estatico_modulo(caminho)``, ``url(caminho)`` (caminho dentro do prefixo), ``modulo``,
``titulo_modulo``, ``versao``, ``versao_plataforma``, ``navegacao`` e os filtros de
``blatt.web.apresentacao``.
"""

import logging
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as versao_instalada
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader, StrictUndefined
from markupsafe import Markup
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.templating import Jinja2Templates

from blatt.infra.configuracao import navegacao_web
from blatt.web import apresentacao
from blatt.web.seguranca import (
    CAMPO_CSRF,
    POLITICA_DE_CONTEUDO,
    CabecalhosSeguranca,
    Escopo,
    Identidade,
    LimiteECsrf,
    csrf_do_escopo,
    usuario_do_escopo,
)

_PREFIXO = re.compile(r"^/[a-z][a-z0-9-]*$")
_MODULO = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
LIMITE_CORPO = 5 * 1024 * 1024  # 5 MiB por requisição que grava, lida para a memória
_log = logging.getLogger("blatt.web")


def _versao_plataforma() -> str:
    try:
        return versao_instalada("blatt-plataforma")
    except PackageNotFoundError:  # pragma: no cover - só fora de uma instalação
        return "desconhecida"


@dataclass(frozen=True)
class Base:
    """O que a base guarda em ``app.state.blatt``."""

    modulo: str
    titulo: str
    prefixo: str
    versao: str
    versao_plataforma: str
    navegacao: tuple[tuple[str, str], ...]
    modelos: Jinja2Templates
    tem_estaticos: bool


def base_da_app(request: Request) -> Base:
    base = request.app.state.blatt
    if not isinstance(base, Base):  # pragma: no cover - só se a app não veio de criar_app
        raise RuntimeError("aplicação não criada por blatt.web.app.criar_app")
    return base


def renderizar(
    request: Request,
    modelo: str,
    contexto: dict[str, Any] | None = None,
    *,
    status: int = 200,
    cabecalhos: dict[str, str] | None = None,
) -> HTMLResponse:
    """Página ``modelo`` com o ``contexto`` do módulo e o contexto comum da base."""
    resposta = base_da_app(request).modelos.TemplateResponse(
        request, modelo, contexto or {}, status_code=status, headers=cabecalhos
    )
    if not isinstance(resposta, HTMLResponse):  # pragma: no cover - sempre _TemplateResponse
        raise RuntimeError("resposta de modelo inesperada")
    return resposta


def _contexto_comum(request: Request) -> dict[str, Any]:
    base = base_da_app(request)
    token = csrf_do_escopo(request.scope) or ""
    raiz_estatico = f"{base.prefixo}/_blatt/"
    return {
        "usuario": usuario_do_escopo(request.scope),
        "csrf_token": token,
        "csrf_campo": lambda: Markup('<input type="hidden" name="{}" value="{}">').format(
            CAMPO_CSRF, token
        ),
        "estatico": lambda caminho: f"{raiz_estatico}{caminho}?v={base.versao_plataforma}",
        "estatico_modulo": lambda caminho: f"{base.prefixo}/estatico/{caminho}?v={base.versao}",
        "url": lambda caminho="": f"{base.prefixo}/{caminho.lstrip('/')}",
        "modulo": base.modulo,
        "titulo_modulo": base.titulo,
        "versao": base.versao,
        "versao_plataforma": base.versao_plataforma,
        "navegacao": base.navegacao,
        "prefixo": base.prefixo,
        "caminho_atual": request.url.path,
    }


def _ambiente(modelos: Sequence[Path]) -> Environment:
    for pasta in modelos:
        if not pasta.is_dir():
            raise ValueError(f"pasta de modelos não existe: {pasta}")
    ambiente = Environment(
        loader=ChoiceLoader(
            [FileSystemLoader([str(p) for p in modelos]), PackageLoader("blatt.web", "modelos")]
        ),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    filtros: dict[str, Callable[..., str]] = {
        "moeda": apresentacao.moeda,
        "numero": apresentacao.numero,
        "data": apresentacao.data,
        "data_hora": apresentacao.data_hora,
        "competencia": apresentacao.competencia,
        "cnpj": apresentacao.cnpj,
        "cpf": apresentacao.cpf,
        "cpf_oculto": apresentacao.cpf_oculto,
    }
    ambiente.filters.update(filtros)
    return ambiente


def criar_app(
    *,
    modulo: str,
    titulo: str,
    prefixo: str,
    versao: str,
    rotas: Iterable[APIRouter] = (),
    modelos: Sequence[Path] = (),
    estaticos: Path | None = None,
    navegacao: Sequence[tuple[str, str]] | None = None,
    saude: Callable[[], bool] | None = None,
    limite_corpo: int = LIMITE_CORPO,
) -> FastAPI:
    """Aplicação FastAPI do ``modulo`` sob ``prefixo`` (``/folha``, ``/fiscal``).

    - ``rotas``: os ``APIRouter`` do módulo, com caminhos relativos ao prefixo (``"/"``,
      ``"/empresas"``); a base os inclui sob o prefixo;
    - ``modelos``: pastas de modelos Jinja2 do módulo (precedência sobre os da base);
    - ``estaticos``: pasta de arquivos do módulo, servida em ``<prefixo>/estatico/``;
    - ``navegacao``: menu entre módulos, pares (título, caminho); sem ele, o de
      ``BLATT_WEB_NAVEGACAO`` (``blatt.infra.configuracao.navegacao_web``) e, se vazio, só o
      próprio módulo;
    - ``saude``: conferência extra da rota de saúde (o banco responde, por exemplo); ``False``
      ou exceção dá 503;
    - ``limite_corpo``: tamanho máximo, em bytes, do corpo de uma requisição que grava.
    """
    if not _MODULO.fullmatch(modulo):
        raise ValueError(f"nome de módulo inválido: {modulo!r}")
    if not _PREFIXO.fullmatch(prefixo):
        raise ValueError(f"prefixo inválido (ex.: '/folha'): {prefixo!r}")
    if prefixo == "/_blatt" or limite_corpo < 1:
        raise ValueError("prefixo reservado ou limite_corpo inválido")
    if estaticos is not None and not estaticos.is_dir():
        raise ValueError(f"pasta de estáticos não existe: {estaticos}")
    itens = tuple(navegacao) if navegacao is not None else navegacao_web()
    if not itens:
        itens = ((titulo, f"{prefixo}/"),)

    app = FastAPI(title=titulo, docs_url=None, redoc_url=None, openapi_url=None)
    modelos_jinja = Jinja2Templates(env=_ambiente(modelos), context_processors=[_contexto_comum])
    base = Base(
        modulo=modulo,
        titulo=titulo,
        prefixo=prefixo,
        versao=versao,
        versao_plataforma=_versao_plataforma(),
        navegacao=itens,
        modelos=modelos_jinja,
        tem_estaticos=estaticos is not None,
    )
    app.state.blatt = base

    async def estado_de_saude() -> JSONResponse:
        corpo = {"estado": "ok", "modulo": modulo, "versao": versao}
        if saude is not None:
            try:
                bom = saude()
            except Exception:
                _log.exception("conferência de saúde do módulo %s falhou", modulo)
                bom = False
            if not bom:
                return JSONResponse({**corpo, "estado": "falha"}, status_code=503)
        return JSONResponse(corpo)

    for caminho in ("/saude", f"{prefixo}/saude"):
        app.add_api_route(caminho, estado_de_saude, methods=["GET"], include_in_schema=False)
    for roteador in rotas:
        app.include_router(roteador, prefix=prefixo)
    app.mount(
        f"{prefixo}/_blatt",
        StaticFiles(packages=[("blatt.web", "estatico")]),
        name="blatt_estatico",
    )
    if estaticos is not None:
        app.mount(f"{prefixo}/estatico", StaticFiles(directory=estaticos), name="estatico")

    async def pagina_de_erro(
        escopo: Escopo, status: int, mensagem: str
    ) -> tuple[bytes, list[tuple[bytes, bytes]]]:
        """Página de erro para os *middlewares* (que respondem antes do roteamento)."""
        request = Request(escopo)
        request.scope.setdefault("app", app)
        resposta = renderizar(
            request, "blatt/erro.html", {"status": status, "mensagem": mensagem}, status=status
        )
        return bytes(resposta.body), list(resposta.raw_headers)

    async def erro_http(request: Request, erro: Exception) -> Response:
        assert isinstance(erro, StarletteHTTPException)  # noqa: S101 - registrado só para ela
        mensagens = {404: "Página não encontrada.", 405: "Operação não permitida aqui."}
        mensagem = (
            erro.detail
            if isinstance(erro.detail, str) and erro.status_code not in mensagens
            else mensagens.get(erro.status_code, "Não foi possível atender a requisição.")
        )
        return renderizar(
            request,
            "blatt/erro.html",
            {"status": erro.status_code, "mensagem": mensagem},
            status=erro.status_code,
            cabecalhos=dict(erro.headers or {}),
        )

    async def erro_validacao(request: Request, erro: Exception) -> Response:
        # Não ecoa os valores recebidos: podem ter dado pessoal ou senha.
        return renderizar(
            request,
            "blatt/erro.html",
            {"status": 422, "mensagem": "Os dados do formulário não estão na forma esperada."},
            status=422,
        )

    async def erro_interno(request: Request, erro: Exception) -> Response:
        _log.error("erro não tratado em %s %s", request.method, request.url.path, exc_info=erro)
        # Fica fora dos middlewares do módulo (ServerErrorMiddleware): cabeçalhos aqui mesmo.
        return renderizar(
            request,
            "blatt/erro.html",
            {"status": 500, "mensagem": "Erro interno do módulo. Tente de novo mais tarde."},
            status=500,
            cabecalhos={
                "content-security-policy": POLITICA_DE_CONTEUDO,
                "x-content-type-options": "nosniff",
                "referrer-policy": "no-referrer",
                "cache-control": "no-store",
            },
        )

    app.add_exception_handler(StarletteHTTPException, erro_http)
    app.add_exception_handler(RequestValidationError, erro_validacao)
    app.add_exception_handler(Exception, erro_interno)

    livres = frozenset({"/saude", f"{prefixo}/saude"})
    app.add_middleware(LimiteECsrf, limite=limite_corpo, erro=pagina_de_erro)
    app.add_middleware(Identidade, livres=livres, erro=pagina_de_erro)
    # Por fora de tudo, menos do ServerErrorMiddleware do Starlette (página 500).
    app.add_middleware(CabecalhosSeguranca)
    return app
