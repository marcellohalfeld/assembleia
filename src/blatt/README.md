# Pacote `blatt-plataforma`

Código comum da plataforma Blatt, sem regra de negócio, usado por mais de um módulo
([PLAT-0016](../../docs/adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md), item 4).
Os módulos instalam este pacote pelo git; não copiam `blatt.comum` nem `blatt.infra`.

## O que tem (versão 0.1.0)

| Pacote | Conteúdo |
| --- | --- |
| `blatt.comum` | `AnoMes` (`periodo.py`); validação de CPF e CNPJ, inclusive alfanumérico (`documentos.py`); regras de texto do eSocial (`texto.py`). Só biblioteca padrão; não importa `blatt.infra`. |
| `blatt.infra` | `configuracao.py`: `tenant_id()`, `dsn_postgres()` (`BLATT_DSN`) e `dsn_modulo(modulo)` (`BLATT_DSN_<MODULO>`). `postgres/migracoes.py`: `disponiveis(pacote)` e `aplicar(conexao, pacote)`. Usado só pelos adaptadores dos módulos. |

- **Origem:** `blatt.comum` veio de `comum/` deste repositório (cópia da folha, `2bcff8e`), sem
  alteração. `blatt.infra` é a versão estendida do aspirador (`src/blatt/infra`, com
  `dsn_modulo()` e o pacote das migrações como parâmetro), compatível com a da folha.
- **Única mudança em relação ao aspirador:** o pacote das migrações passou a ser **obrigatório**
  em `disponiveis()` e `aplicar()`, e `PACOTE_PADRAO` deixou de existir. Este pacote não traz
  migração de módulo nenhum; um padrão apontaria para `blatt.infra.postgres`, que não tem `sql/`.
  Cada módulo guarda as suas migrações (`sql/NNNN_nome.sql`) no próprio pacote e informa o nome
  dele, por exemplo `aplicar(conexao, "blatt.fiscal.aspirador.adaptadores.postgres")`.
- **Ainda não tem:** utilitários de fatos (`outbox`/`inbox`, PLAT-0019) e a base da interface
  web (PLAT-0021). Entram depois do aceite dessas ADRs, numa versão nova.
- **Dependência:** `psycopg[binary]`, importado por `blatt.infra.postgres.migracoes` (LGPL, com
  a exceção nominal da [PLAT-0008](../../docs/adr/PLAT-0008-driver-postgresql-psycopg.md)).

## `blatt` é *namespace package*

Não existe `src/blatt/__init__.py`, nem aqui nem nos módulos (PEP 420; PLAT-0016, item 4.3).
`blatt.comum` e `blatt.infra` vêm do pacote instalado; `blatt.folha`, `blatt.fiscal.aspirador` e
os demais, do repositório de cada módulo. Cada subpacote leva o seu `py.typed`.

## Como um módulo instala

O `pyproject.toml` do pacote fica na raiz deste repositório, então a dependência não precisa
de `#subdirectory=`. No repositório do módulo:

```bash
uv add "blatt-plataforma @ git+https://github.com/marcellohalfeld/assembleia@v0.1.0"
```

O `uv` grava `"blatt-plataforma"` em `dependencies` e a origem em `[tool.uv.sources]`
(`blatt-plataforma = { git = "https://github.com/marcellohalfeld/assembleia", rev = "v0.1.0" }`);
o `uv.lock` fixa o commit. Com
`uv add git+https://github.com/marcellohalfeld/assembleia --tag v0.1.0`, a origem fica
`tag = "v0.1.0"`, mais explícita; o efeito é o mesmo. (Conferido com o uv 0.11 contra um
clone local, com branch no lugar da tag: `@<ref>` grava `rev`, `--branch` grava `branch`.)

Configuração do módulo, conferida num projeto mínimo com `src/blatt/exemplo/`:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
mypy_path = "src"
explicit_package_bases = true   # sem src/blatt/__init__.py
packages = ["blatt.<modulo>"]

[tool.importlinter]
root_package = "blatt"          # o grimp junta a parte instalada e a do módulo
include_external_packages = true
```

Com `root_package = "blatt"`, `blatt.comum` e `blatt.infra` entram no grafo do módulo como
internos, e os contratos que proíbem `blatt.infra` no domínio e na aplicação continuam
funcionando.

## Como se publica uma versão nova

1. Mudar o código aqui, em PR, com testes; rodar a sequência completa.
2. Subir `version` no `pyproject.toml` (mudança incompatível é versão maior nova) e rodar
   `uv lock`.
3. Depois do merge, marcar a tag `vX.Y.Z` no commit de `main` e enviá-la (`git tag vX.Y.Z` e
   `git push origin vX.Y.Z`). Tags são marcadas pelo Marcello.
4. Em cada módulo, por PR, no ritmo dele: trocar a tag em `[tool.uv.sources]` (ou repetir o
   `uv add` com a tag nova), rodar `uv lock --upgrade-package blatt-plataforma` e as checagens.

## Checagens

```bash
uv sync && uv run ruff check . && uv run ruff format --check . \
  && uv run mypy && uv run lint-imports && BLATT_EXIGIR_POSTGRES=1 uv run pytest
```

Os testes de banco sobem um PostgreSQL temporário (`tests/postgres_teste.py`) e usam
migrações fictícias (`tests/migracoes_teste/`). O `import-linter` verifica que `blatt.comum` e
`blatt.infra` não importam módulo de negócio e que `blatt.comum` não importa `blatt.infra`; a
explicação do primeiro contrato está no `pyproject.toml`. O CI repete a sequência, confere as
licenças com `pip-licenses` e verifica o conteúdo do wheel.
