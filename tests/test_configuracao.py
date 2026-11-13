"""Configuração da instância (``blatt.infra.configuracao``).

Os três primeiros testes vêm da folha (``tests/test_configuracao.py`` do ``blatt``); os de
``dsn_modulo`` cobrem a extensão do aspirador (PLAT-0016, item 4).
"""

import uuid
from collections.abc import Callable
from pathlib import Path

import pytest

from blatt.infra.configuracao import (
    ErroConfiguracao,
    dir_arquivo,
    dir_arquivo_opcional,
    dir_dados,
    dir_dados_opcional,
    dir_parametros,
    dsn_modulo,
    dsn_postgres,
    navegacao_web,
    tenant_id,
)


def test_tenant_id_lido_do_ambiente() -> None:
    valor = "00000000-0000-4000-8000-000000000001"
    assert tenant_id({"BLATT_TENANT_ID": valor}) == uuid.UUID(valor)


@pytest.mark.parametrize("ambiente", [{}, {"BLATT_TENANT_ID": ""}, {"BLATT_TENANT_ID": "1"}])
def test_tenant_id_ausente_ou_invalido(ambiente: dict[str, str]) -> None:
    with pytest.raises(ErroConfiguracao, match="BLATT_TENANT_ID"):
        tenant_id(ambiente)


def test_dsn_obrigatorio() -> None:
    with pytest.raises(ErroConfiguracao, match="BLATT_DSN"):
        dsn_postgres({})
    assert dsn_postgres({"BLATT_DSN": "dbname=blatt"}) == "dbname=blatt"


@pytest.mark.parametrize(
    ("modulo", "variavel"),
    [
        ("folha", "BLATT_DSN_FOLHA"),
        ("fiscal.aspirador", "BLATT_DSN_FISCAL_ASPIRADOR"),
        ("fiscal.escrituracao", "BLATT_DSN_FISCAL_ESCRITURACAO"),
    ],
)
def test_dsn_modulo_le_a_variavel_do_modulo(modulo: str, variavel: str) -> None:
    assert dsn_modulo(modulo, {variavel: "dbname=x", "BLATT_DSN": "dbname=y"}) == "dbname=x"


@pytest.mark.parametrize("ambiente", [{}, {"BLATT_DSN_FOLHA": ""}, {"BLATT_DSN": "dbname=y"}])
def test_dsn_modulo_ausente(ambiente: dict[str, str]) -> None:
    with pytest.raises(ErroConfiguracao, match="BLATT_DSN_FOLHA"):
        dsn_modulo("folha", ambiente)


def test_le_o_ambiente_do_processo_quando_nao_recebe_um(monkeypatch: pytest.MonkeyPatch) -> None:
    valor = "00000000-0000-4000-8000-000000000002"
    monkeypatch.setenv("BLATT_TENANT_ID", valor)
    monkeypatch.setenv("BLATT_DSN_FISCAL_ASPIRADOR", "dbname=fiscal_aspirador")
    assert tenant_id() == uuid.UUID(valor)
    assert dsn_modulo("fiscal.aspirador") == "dbname=fiscal_aspirador"


# --- pastas e navegação (0.2.0; P-65 da folha) -----------------------------------------------


def test_dir_arquivo(tmp_path: Path) -> None:
    ambiente = {"BLATT_DIR_ARQUIVO": str(tmp_path)}
    assert dir_arquivo(ambiente) == tmp_path
    assert dir_arquivo_opcional(ambiente) == tmp_path
    assert dir_arquivo_opcional({}) is None
    with pytest.raises(ErroConfiguracao, match="defina BLATT_DIR_ARQUIVO"):
        dir_arquivo({})


@pytest.mark.parametrize(
    ("funcao", "variavel"),
    [
        (dir_arquivo, "BLATT_DIR_ARQUIVO"),
        (dir_arquivo_opcional, "BLATT_DIR_ARQUIVO"),
        (dir_dados, "BLATT_DIR_DADOS"),
        (dir_dados_opcional, "BLATT_DIR_DADOS"),
    ],
)
def test_pastas_tem_de_ser_absolutas_e_existir(
    funcao: Callable[[dict[str, str]], Path | None], variavel: str, tmp_path: Path
) -> None:
    with pytest.raises(ErroConfiguracao, match=f"{variavel} tem de ser caminho absoluto"):
        funcao({variavel: "arquivo"})
    with pytest.raises(ErroConfiguracao, match=f"{variavel} não é uma pasta existente"):
        funcao({variavel: str(tmp_path / "nao-existe")})
    (tmp_path / "arquivo-comum").write_text("x")
    with pytest.raises(ErroConfiguracao, match=f"{variavel} não é uma pasta existente"):
        funcao({variavel: str(tmp_path / "arquivo-comum")})


def test_dir_dados(tmp_path: Path) -> None:
    assert dir_dados({"BLATT_DIR_DADOS": str(tmp_path)}) == tmp_path
    assert dir_dados_opcional({}) is None
    with pytest.raises(ErroConfiguracao, match="defina BLATT_DIR_DADOS"):
        dir_dados({})


def test_dir_parametros() -> None:
    assert dir_parametros({}) == Path("parametros")
    assert dir_parametros({"BLATT_DIR_PARAMETROS": "/app/parametros"}) == Path("/app/parametros")


def test_navegacao_web() -> None:
    assert navegacao_web({}) == ()
    assert navegacao_web({"BLATT_WEB_NAVEGACAO": "Início=/; Folha=/folha/ ;Fiscal=/fiscal/"}) == (
        ("Início", "/"),
        ("Folha", "/folha/"),
        ("Fiscal", "/fiscal/"),
    )


@pytest.mark.parametrize(
    "valor", ["Folha", "Folha=folha/", "=/folha/", "Folha=https://fora/", "A=/a;;B=/b"]
)
def test_navegacao_web_invalida(valor: str) -> None:
    with pytest.raises(ErroConfiguracao, match="BLATT_WEB_NAVEGACAO"):
        navegacao_web({"BLATT_WEB_NAVEGACAO": valor})
