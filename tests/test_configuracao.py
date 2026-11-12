"""Configuração da instância (``blatt.infra.configuracao``).

Os três primeiros testes vêm da folha (``tests/test_configuracao.py`` do ``blatt``); os de
``dsn_modulo`` cobrem a extensão do aspirador (PLAT-0016, item 4).
"""

import uuid

import pytest

from blatt.infra.configuracao import ErroConfiguracao, dsn_modulo, dsn_postgres, tenant_id


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
