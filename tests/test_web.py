"""Base da interface web (``blatt.web``; PLAT-0021, itens 4 a 7), com o cliente de teste do
Starlette contra o módulo fictício ``tests/web_exemplo``."""

import hashlib
import logging
import os
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from importlib.resources import files
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from blatt.web.app import criar_app
from blatt.web.formulario import CertificadoA1, ErroFormulario, certificado_do_corpo
from blatt.web.seguranca import COOKIE_CSRF
from tests import web_exemplo

ENDERECO = "https://blatt.casa"
USUARIO = {"X-Blatt-Usuario": "marcello"}
SHA256_HTMX = "d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717"


@pytest.fixture
def cliente() -> Iterator[TestClient]:
    with TestClient(web_exemplo.app(), base_url=ENDERECO) as cliente:
        yield cliente


def _token(cliente: TestClient) -> str:
    resposta = cliente.get("/exemplo/", headers=USUARIO)
    assert resposta.status_code == 200
    token = cliente.cookies.get(COOKIE_CSRF)
    assert token
    return token


# --- saúde, identidade e prefixo ---------------------------------------------------------------


def test_saude_sem_usuario(cliente: TestClient) -> None:
    for caminho in ("/saude", "/exemplo/saude"):
        resposta = cliente.get(caminho)
        assert resposta.status_code == 200
        assert resposta.json() == {"estado": "ok", "modulo": "exemplo", "versao": "1.2.3"}


def test_saude_com_falha() -> None:
    with TestClient(web_exemplo.app(saude_ok=False), base_url=ENDERECO) as cliente:
        resposta = cliente.get("/saude")
    assert resposta.status_code == 503
    assert resposta.json()["estado"] == "falha"


@pytest.mark.parametrize(
    "cabecalhos",
    [
        {},
        {"X-Blatt-Usuario": ""},
        {"X-Blatt-Usuario": "dois nomes"},
        {"X-Blatt-Usuario": "a" * 129},
    ],
)
def test_recusa_sem_usuario(cliente: TestClient, cabecalhos: dict[str, str]) -> None:
    for caminho in ("/exemplo/", "/exemplo/_blatt/blatt.css", "/exemplo/nao-existe"):
        resposta = cliente.get(caminho, headers=cabecalhos)
        assert resposta.status_code == 401
        assert "Acesso só pelo portal" in resposta.text
        assert resposta.headers["cache-control"] == "no-store"
    assert (
        cliente.post("/exemplo/salvar", data={"nome": "x"}, headers=cabecalhos).status_code == 401
    )


def test_pagina_do_modulo_com_o_modelo_base(cliente: TestClient) -> None:
    resposta = cliente.get("/exemplo/", headers=USUARIO)
    assert resposta.status_code == 200
    html = resposta.text
    assert '<html lang="pt-BR">' in html
    assert "<title>Início · Blatt</title>" in html
    assert '<span class="usuario">marcello</span>' in html
    assert '<a href="/exemplo/" aria-current="page">Exemplo</a>' in html
    assert '<a href="/folha/">Folha</a>' in html
    assert re.search(r"Exemplo 1\.2\.3 · blatt-plataforma \d+\.\d+\.\d+", html)
    assert 'href="/exemplo/_blatt/blatt.css?v=' in html
    assert 'src="/exemplo/_blatt/htmx.min.js?v=' in html
    assert '<p class="numero" id="valor">1.234,50</p>' in html
    assert '<p id="cnpj">12.345.678/0001-95</p>' in html
    assert '<p id="competencia">10/2026</p>' in html
    assert 'action="/exemplo/salvar"' in html
    token = cliente.cookies.get(COOKIE_CSRF)
    assert f'<input type="hidden" name="csrf" value="{token}">' in html
    assert f'hx-headers=\'{{"X-Blatt-CSRF": "{token}"}}\'' in html


def test_cabecalhos_de_seguranca(cliente: TestClient) -> None:
    resposta = cliente.get("/exemplo/", headers=USUARIO)
    assert "script-src 'self'" in resposta.headers["content-security-policy"]
    assert resposta.headers["x-content-type-options"] == "nosniff"
    assert resposta.headers["referrer-policy"] == "no-referrer"
    assert resposta.headers["cache-control"] == "no-store"
    cookie = resposta.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE_CSRF}=")
    for atributo in ("Path=/", "Secure", "HttpOnly", "SameSite=Strict"):
        assert atributo in cookie
    # Com o cookie já presente, não é gravado de novo.
    assert "set-cookie" not in cliente.get("/exemplo/", headers=USUARIO).headers


def test_so_atende_sob_o_prefixo(cliente: TestClient) -> None:
    for caminho in ("/", "/salvar", "/_blatt/blatt.css"):
        resposta = cliente.get(caminho, headers=USUARIO)
        assert resposta.status_code == 404
        assert "Página não encontrada." in resposta.text


def test_estaticos_sob_o_prefixo(cliente: TestClient) -> None:
    htmx = cliente.get("/exemplo/_blatt/htmx.min.js", headers=USUARIO)
    assert htmx.status_code == 200
    assert hashlib.sha256(htmx.content).hexdigest() == SHA256_HTMX
    css = cliente.get("/exemplo/_blatt/blatt.css", headers=USUARIO)
    assert css.status_code == 200
    assert css.headers["content-type"].startswith("text/css")
    assert "cache-control" not in css.headers
    nota = cliente.get("/exemplo/estatico/nota.txt", headers=USUARIO)
    assert nota.text == "arquivo do módulo\n"


def test_htmx_versionado_confere_com_o_readme() -> None:
    pasta = files("blatt.web").joinpath("estatico")
    conteudo = pasta.joinpath("htmx.min.js").read_bytes()
    assert hashlib.sha256(conteudo).hexdigest() == SHA256_HTMX
    assert SHA256_HTMX in pasta.joinpath("README.md").read_text("utf-8")
    assert pasta.joinpath("htmx.LICENSE.txt").read_text("utf-8").startswith("Zero-Clause BSD")


# --- páginas de erro ---------------------------------------------------------------------------


def test_erro_interno_nao_mostra_o_detalhe(caplog: pytest.LogCaptureFixture) -> None:
    with TestClient(web_exemplo.app(), base_url=ENDERECO, raise_server_exceptions=False) as cliente:
        resposta = cliente.get("/exemplo/falha", headers=USUARIO)
    assert resposta.status_code == 500
    assert "Erro interno do módulo" in resposta.text
    assert "detalhe interno" not in resposta.text
    assert resposta.headers["cache-control"] == "no-store"
    assert "erro não tratado em GET /exemplo/falha" in caplog.text


def test_erro_de_validacao_nao_ecoa_o_que_veio(cliente: TestClient) -> None:
    token = _token(cliente)
    resposta = cliente.post(
        "/exemplo/salvar", data={"csrf": token, "outro": "segredo-123"}, headers=USUARIO
    )
    assert resposta.status_code == 422
    assert "não estão na forma esperada" in resposta.text
    assert "segredo-123" not in resposta.text


def test_metodo_nao_permitido(cliente: TestClient) -> None:
    resposta = cliente.get("/exemplo/salvar", headers=USUARIO)
    assert resposta.status_code == 405
    assert "Operação não permitida aqui." in resposta.text


# --- CSRF --------------------------------------------------------------------------------------


def test_formulario_com_o_token(cliente: TestClient) -> None:
    token = _token(cliente)
    resposta = cliente.post("/exemplo/salvar", data={"csrf": token, "nome": "Ana"}, headers=USUARIO)
    assert resposta.status_code == 200
    assert resposta.json() == {"nome": "Ana"}


def test_htmx_com_o_token_no_cabecalho(cliente: TestClient) -> None:
    token = _token(cliente)
    resposta = cliente.post(
        "/exemplo/salvar", data={"nome": "Ana"}, headers={**USUARIO, "X-Blatt-CSRF": token}
    )
    assert resposta.status_code == 200


def test_sem_cookie_e_recusado(cliente: TestClient) -> None:
    resposta = cliente.post(
        "/exemplo/salvar", data={"csrf": "x" * 43, "nome": "Ana"}, headers=USUARIO
    )
    assert resposta.status_code == 403
    assert "sem o cookie" in resposta.text
    # A resposta já entrega um cookie novo: recarregar a página resolve.
    assert COOKIE_CSRF in resposta.headers["set-cookie"]


@pytest.mark.parametrize("enviado", [None, "", "x" * 43])
def test_token_errado_ou_ausente_e_recusado(cliente: TestClient, enviado: str | None) -> None:
    _token(cliente)
    dados = {"nome": "Ana"} if enviado is None else {"nome": "Ana", "csrf": enviado}
    resposta = cliente.post("/exemplo/salvar", data=dados, headers=USUARIO)
    assert resposta.status_code == 403
    assert "expirou ou não veio desta página" in resposta.text


def test_token_repetido_no_formulario_e_recusado(cliente: TestClient) -> None:
    token = _token(cliente)
    resposta = cliente.post(
        "/exemplo/salvar",
        content=f"csrf={token}&csrf={token}&nome=Ana",
        headers={**USUARIO, "Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resposta.status_code == 403


@pytest.mark.parametrize(
    "cabecalhos",
    [
        {"Sec-Fetch-Site": "cross-site"},
        {"Sec-Fetch-Site": "same-site"},
        {"Sec-Fetch-Site": "none"},
        {"Origin": "https://outro.site"},
        {"Origin": "https://blatt.casa:8443"},
        {"Origin": "null"},
    ],
)
def test_outra_origem_e_recusada_mesmo_com_o_token(
    cliente: TestClient, cabecalhos: dict[str, str]
) -> None:
    token = _token(cliente)
    resposta = cliente.post(
        "/exemplo/salvar",
        data={"csrf": token, "nome": "Ana"},
        headers={**USUARIO, "X-Blatt-CSRF": token, **cabecalhos},
    )
    assert resposta.status_code == 403
    assert "Envio recusado" in resposta.text


def test_mesma_origem_e_aceita(cliente: TestClient) -> None:
    token = _token(cliente)
    resposta = cliente.post(
        "/exemplo/salvar",
        data={"csrf": token, "nome": "Ana"},
        headers={**USUARIO, "Origin": ENDERECO, "Sec-Fetch-Site": "same-origin"},
    )
    assert resposta.status_code == 200


def test_corpo_grande_demais(cliente: TestClient) -> None:
    token = _token(cliente)
    grande = "x" * (4 * 1024 * 1024 + 1)
    resposta = cliente.post(
        "/exemplo/salvar", data={"csrf": token, "nome": grande}, headers=USUARIO
    )
    assert resposta.status_code == 413
    assert "tamanho máximo" in resposta.text


# --- upload sensível, só em memória --------------------------------------------------------------

SENHA = "senha-do-certificado-9f3a"
CERTIFICADO = b"\x30\x82PFX-FICTICIO" + os.urandom(64)


def _enviar_certificado(
    cliente: TestClient,
    conteudo: bytes = CERTIFICADO,
    senha: str | None = SENHA,
    sem_disco: "SemDisco | None" = None,
    **campos: str,
) -> httpx.Response:
    token = _token(cliente)
    dados = {"csrf": token, **campos}
    if senha is not None:
        dados["senha"] = senha
    with sem_disco() if sem_disco is not None else nullcontext():
        return cliente.post(
            "/exemplo/certificado",
            data=dados,
            files={"certificado": ("empresa.pfx", conteudo, "application/x-pkcs12")},
            headers=USUARIO,
        )


class SemDisco:
    """Enquanto ativa, qualquer abertura de arquivo (evento de auditoria ``open`` do Python, que
    cobre ``open``, ``os.open``, ``tempfile`` e os temporários do Starlette) é registrada e
    recusada. O gancho de auditoria não pode ser removido; fica inerte fora do ``with``."""

    ativa: "SemDisco | None" = None
    instalado = False

    def __init__(self) -> None:
        self.tentativas: list[str] = []
        if not SemDisco.instalado:
            sys.addaudithook(SemDisco._gancho)
            SemDisco.instalado = True

    @staticmethod
    def _gancho(evento: str, argumentos: tuple[object, ...]) -> None:
        atual = SemDisco.ativa
        if atual is None or evento != "open":
            return
        atual.tentativas.append(str(argumentos[0]))
        raise AssertionError(f"tentou usar o disco: {argumentos[0]}")

    @contextmanager
    def __call__(self) -> Iterator[None]:
        SemDisco.ativa = self
        try:
            yield
        finally:
            SemDisco.ativa = None


@pytest.fixture
def sem_disco() -> SemDisco:
    return SemDisco()


def test_certificado_vai_ao_caso_de_uso_so_em_memoria(
    cliente: TestClient, caplog: pytest.LogCaptureFixture, sem_disco: SemDisco
) -> None:
    web_exemplo.recebidos.clear()
    caplog.set_level(logging.DEBUG)
    # Maior que o limite de 1 MiB em que o SpooledTemporaryFile do Starlette iria para disco.
    grande = CERTIFICADO + os.urandom(1536 * 1024)
    resposta = _enviar_certificado(cliente, grande, sem_disco=sem_disco, empresa="12345678000195")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == {"bytes": len(grande), "campos": {"empresa": "12345678000195"}}
    assert sem_disco.tentativas == []
    recebido = web_exemplo.recebidos[-1]
    assert (recebido.conteudo, recebido.senha, recebido.nome_arquivo) == (
        grande,
        SENHA,
        "empresa.pfx",
    )
    assert repr(recebido) == f"CertificadoA1({len(grande)} bytes, senha oculta)"
    assert SENHA not in caplog.text
    assert SENHA not in str(recebido)
    assert "PFX-FICTICIO" not in caplog.text


def test_o_upload_comum_usaria_o_disco(cliente: TestClient, sem_disco: SemDisco) -> None:
    """Contraprova: o UploadFile do Starlette passa por SpooledTemporaryFile, que vai para disco
    acima de 1 MiB; a interceptação do teste anterior pegaria isso."""
    token = _token(cliente)
    grande = os.urandom(1536 * 1024)
    with pytest.raises(AssertionError, match="tentou usar o disco"), sem_disco():
        cliente.post(
            "/exemplo/arquivo-comum",
            data={"csrf": token},
            files={"arquivo": ("a.bin", grande, "application/octet-stream")},
            headers=USUARIO,
        )
    assert sem_disco.tentativas


@pytest.mark.parametrize(
    ("argumentos", "mensagem"),
    [
        ({"senha": None}, "informe a senha"),
        ({"conteudo": b""}, "está vazio"),
        ({"conteudo": b"x" * (2 * 1024 * 1024 + 1)}, "passou de 2048 KiB"),
    ],
)
def test_certificado_fora_da_forma(
    cliente: TestClient, argumentos: dict[str, object], mensagem: str
) -> None:
    resposta = _enviar_certificado(cliente, **argumentos)  # type: ignore[arg-type]
    assert resposta.status_code == 400
    assert mensagem in resposta.text
    assert SENHA not in resposta.text


def test_certificado_do_corpo_sem_multipart() -> None:
    with pytest.raises(ErroFormulario, match="multipart/form-data"):
        certificado_do_corpo(b"senha=x", "application/x-www-form-urlencoded")
    with pytest.raises(ErroFormulario, match="malformado"):
        certificado_do_corpo(b"lixo sem fronteira", "multipart/form-data; boundary=abc")
    assert isinstance(
        certificado_do_corpo(
            b'--f\r\nContent-Disposition: form-data; name="certificado"; filename="c.pfx"\r\n\r\n'
            b'PFX\r\n--f\r\nContent-Disposition: form-data; name="senha"\r\n\r\nabc\r\n--f--\r\n',
            "multipart/form-data; boundary=f",
        ),
        CertificadoA1,
    )


def test_multipart_com_o_token_no_campo(cliente: TestClient) -> None:
    resposta = _enviar_certificado(cliente)
    assert resposta.status_code == 200


# --- parâmetros da fábrica ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "argumentos",
    [
        {"prefixo": "folha"},
        {"prefixo": "/Folha"},
        {"prefixo": "/folha/"},
        {"prefixo": "/_blatt"},
        {"modulo": "Folha"},
        {"modelos": [Path("/nao/existe")]},
        {"estaticos": Path("/nao/existe")},
        {"limite_corpo": 0},
    ],
)
def test_parametros_invalidos(argumentos: dict[str, object]) -> None:
    padrao: dict[str, object] = {
        "modulo": "folha",
        "titulo": "Folha",
        "prefixo": "/folha",
        "versao": "0.1.0",
    }
    with pytest.raises(ValueError):
        criar_app(**{**padrao, **argumentos})  # type: ignore[arg-type]


def test_navegacao_do_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLATT_WEB_NAVEGACAO", "Início=/;Fiscal=/fiscal/")
    app = criar_app(modulo="fiscal.aspirador", titulo="Fiscal", prefixo="/fiscal", versao="1")
    assert app.state.blatt.navegacao == (("Início", "/"), ("Fiscal", "/fiscal/"))
    monkeypatch.delenv("BLATT_WEB_NAVEGACAO")
    app = criar_app(modulo="fiscal.aspirador", titulo="Fiscal", prefixo="/fiscal", versao="1")
    assert app.state.blatt.navegacao == (("Fiscal", "/fiscal/"),)
