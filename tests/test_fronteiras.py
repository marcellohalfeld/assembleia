"""Fronteiras e regras de código do pacote (PLAT-0016, item 4.1).

Repete, lendo os imports do código, os contratos do ``import-linter`` em ``pyproject.toml``:
de ``blatt``, só ``blatt.comum``, ``blatt.infra`` e ``blatt.web`` podem ser importados (nunca um
módulo de negócio); ``blatt.comum`` não importa ``blatt.infra`` nem ``blatt.web``;
``blatt.infra`` não importa ``blatt.web``; ``blatt.web.apresentacao`` não depende do extra
``[web]``. Também confere que ``blatt`` continua *namespace package* (sem
``src/blatt/__init__.py``).
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
PERMITIDOS = ("blatt.comum", "blatt.infra", "blatt.web")
EXTRA_WEB = ("fastapi", "starlette", "jinja2", "markupsafe", "uvicorn", "python_multipart")


def _importados(arquivo: Path) -> set[str]:
    nomes: set[str] = set()
    for no in ast.walk(ast.parse(arquivo.read_text("utf-8"))):
        if isinstance(no, ast.Import):
            nomes.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            nomes.add(no.module)
            nomes.update(f"{no.module}.{alias.name}" for alias in no.names)
    return nomes


def _arquivos() -> list[Path]:
    return sorted((SRC / "blatt").rglob("*.py"))


def test_blatt_e_namespace_package() -> None:
    assert not (SRC / "blatt" / "__init__.py").exists()
    for subpacote in PERMITIDOS:
        pasta = SRC.joinpath(*subpacote.split("."))
        assert (pasta / "__init__.py").is_file()
        assert (pasta / "py.typed").is_file()


@pytest.mark.parametrize("arquivo", _arquivos(), ids=lambda p: str(p.relative_to(SRC)))
def test_so_importa_comum_e_infra(arquivo: Path) -> None:
    proibidos = sorted(
        nome
        for nome in _importados(arquivo)
        if (nome == "blatt" or nome.startswith("blatt."))
        and not any(nome == p or nome.startswith(p + ".") for p in PERMITIDOS)
    )
    assert proibidos == []


@pytest.mark.parametrize(
    "arquivo",
    sorted((SRC / "blatt" / "comum").rglob("*.py")),
    ids=lambda p: str(p.relative_to(SRC)),
)
def test_comum_nao_importa_infra_nem_web(arquivo: Path) -> None:
    assert not any(n.startswith(("blatt.infra", "blatt.web")) for n in _importados(arquivo))


@pytest.mark.parametrize(
    "arquivo",
    sorted((SRC / "blatt" / "infra").rglob("*.py")),
    ids=lambda p: str(p.relative_to(SRC)),
)
def test_infra_nao_importa_web(arquivo: Path) -> None:
    importados = _importados(arquivo)
    assert not any(n.startswith("blatt.web") for n in importados)
    assert not any(n.split(".")[0] in EXTRA_WEB for n in importados)


@pytest.mark.parametrize(
    "arquivo",
    [SRC / "blatt" / "web" / "__init__.py", SRC / "blatt" / "web" / "apresentacao.py"],
    ids=lambda p: str(p.relative_to(SRC)),
)
def test_apresentacao_nao_depende_do_extra_web(arquivo: Path) -> None:
    assert not any(n.split(".")[0] in EXTRA_WEB for n in _importados(arquivo))


@pytest.mark.parametrize("arquivo", _arquivos(), ids=lambda p: str(p.relative_to(SRC)))
def test_sem_float_literal_nem_eval_exec(arquivo: Path) -> None:
    """Dinheiro e alíquotas são Decimal; nada de eval/exec (PLAT-0003; docs/PLATAFORMA.md, 6)."""
    ofensores = []
    for no in ast.walk(ast.parse(arquivo.read_text("utf-8"))):
        if isinstance(no, ast.Constant) and isinstance(no.value, float):
            ofensores.append(f"float na linha {no.lineno}")
        if (
            isinstance(no, ast.Call)
            and isinstance(no.func, ast.Name)
            and no.func.id in {"eval", "exec"}
        ):
            ofensores.append(f"{no.func.id} na linha {no.lineno}")
    assert ofensores == []
