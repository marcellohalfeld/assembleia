"""Módulo fictício que usa a base web, só para os testes (``tests/test_web.py``)."""

from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from blatt.web.app import criar_app, renderizar
from blatt.web.formulario import CertificadoA1, formulario_certificado

PASTA = Path(__file__).parent
recebidos: list[CertificadoA1] = []

rotas = APIRouter()


@rotas.get("/")
async def inicio(request: Request) -> HTMLResponse:
    return renderizar(request, "inicio.html", {"valor": Decimal("1234.5")})


@rotas.post("/salvar")
async def salvar(nome: Annotated[str, Form()]) -> JSONResponse:
    return JSONResponse({"nome": nome})


@rotas.post("/certificado")
async def certificado(
    recebido: Annotated[
        CertificadoA1, Depends(formulario_certificado(tamanho_maximo=2 * 1024 * 1024))
    ],
) -> JSONResponse:
    recebidos.append(recebido)
    return JSONResponse({"bytes": len(recebido.conteudo), "campos": dict(recebido.campos)})


@rotas.post("/arquivo-comum")
async def arquivo_comum(arquivo: Annotated[UploadFile, File()]) -> JSONResponse:
    """Upload comum do Starlette (para comparar: este passa por SpooledTemporaryFile)."""
    return JSONResponse({"bytes": len(await arquivo.read())})


@rotas.get("/falha")
async def falha() -> HTMLResponse:
    raise RuntimeError("detalhe interno que não pode aparecer na página")


def app(saude_ok: bool = True, limite_corpo: int = 4 * 1024 * 1024) -> FastAPI:
    return criar_app(
        modulo="exemplo",
        titulo="Exemplo",
        prefixo="/exemplo",
        versao="1.2.3",
        rotas=[rotas],
        modelos=[PASTA / "modelos"],
        estaticos=PASTA / "estatico",
        navegacao=[("Início", "/"), ("Exemplo", "/exemplo/"), ("Folha", "/folha/")],
        saude=lambda: saude_ok,
        limite_corpo=limite_corpo,
    )
