# Pacote `blatt-plataforma`

Código comum da plataforma Blatt, sem regra de negócio, usado por mais de um módulo
([PLAT-0016](../../docs/adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md), item 4).
Os módulos instalam este pacote pelo git; não copiam `blatt.comum` nem `blatt.infra`.

## O que tem (versão 0.2.0)

| Pacote | Conteúdo |
| --- | --- |
| `blatt.comum` | `AnoMes` (`periodo.py`); validação de CPF e CNPJ, inclusive alfanumérico (`documentos.py`); regras de texto do eSocial (`texto.py`). Só biblioteca padrão; não importa `blatt.infra` nem `blatt.web`. |
| `blatt.infra` | Configuração, arquivo imutável, migrações e fatos, usados só pelos adaptadores dos módulos (detalhe abaixo). Não importa `blatt.web`. |
| `blatt.web` | Base da interface web (PLAT-0021), no extra `[web]`: fábrica de aplicação, modelo base, estilo, htmx, identidade, CSRF, upload sensível em memória, formatos de apresentação. Contrato com o portal e o Caddy: [`docs/contratos/web.md`](../../docs/contratos/web.md). |

Nenhum deles tem regra de negócio de módulo, nem importa módulo de negócio (`import-linter` e
`tests/test_fronteiras.py`).

### `blatt.infra`

- **`configuracao`** (PLAT-0017, item 5): `tenant_id()` (`BLATT_TENANT_ID`),
  `dsn_postgres()` (`BLATT_DSN`), `dsn_modulo(modulo)` (`BLATT_DSN_<MODULO>`), e, desde a 0.2.0,
  `dir_arquivo()` / `dir_arquivo_opcional()` (`BLATT_DIR_ARQUIVO`, caminho absoluto de pasta
  existente), `dir_dados()` / `dir_dados_opcional()` (`BLATT_DIR_DADOS`), `dir_parametros()`
  (`BLATT_DIR_PARAMETROS`, padrão `parametros`) e `navegacao_web()` (`BLATT_WEB_NAVEGACAO`,
  `Título=/caminho/;...`). Todas aceitam o ambiente como parâmetro (testes) e levantam
  `ErroConfiguracao` com o nome da variável.
- **`arquivo`** (PLAT-0022, item 1.2): `ArquivoImutavel(raiz)`, com
  `gravar(caminho_relativo, conteudo) -> ArquivoGravado(caminho, sha256, tamanho, novo)`,
  `ler(caminho_relativo, sha256_esperado) -> bytes` e `existe(caminho_relativo)`; `sha256(bytes)`;
  `ErroArquivoImutavel`. Temporário na mesma pasta, `fchmod 0640`, `fsync`, `os.link` (nunca
  sobrescreve), `fsync` da pasta; mesmo conteúdo é no-op (`novo=False`), conteúdo diferente é
  erro; a leitura confere o hash. O layout de pastas e o índice no banco são do módulo.
- **`postgres.migracoes`**: `disponiveis(pacote)`, `aplicar(conexao, pacote)` e, desde a 0.2.0,
  `conferir(conexao, pacote) -> list[int]`, só leitura: erro se uma migração aplicada mudou, se o
  banco tem migração desconhecida ou se nunca foi migrado; devolve as pendentes. É o que o
  comando de verificação do módulo chama no teste de restauração do `oper` (P-65 da folha).
- **`fatos`** (PLAT-0019), desde a 0.2.0:
  - `envelope`: `Envelope` (frozen; `Envelope.novo(...)`, `para_json`, `para_texto`,
    `de_json`, `de_texto`), `texto_decimal(Decimal) -> str`, `ErroEnvelope`. Conteúdo só JSON
    puro, sem `float` nem `Decimal`;
  - `postgres` (SQL explícito, transação de quem chama): `gravar_na_outbox(conexao, envelope) ->
    sequencia`, `ler_outbox(conexao, depois_de, limite)` (só para exibir), `inserir_na_inbox`,
    `proximos_da_inbox(conexao, limite, tipos)` (`FOR UPDATE SKIP LOCKED`),
    `marcar_processado(conexao, id) -> bool`, `ler_cursor`, `avancar_cursor`;
  - `ddl`: `ddl_outbox(origem)`, `ddl_inbox()`, `ddl_entrega_cursor()`, `ddl_consumidor()`: o
    texto que o módulo copia para uma migração própria, com as concessões a `blatt_entregador`
    e `blatt_portal` "se o papel existir". A `outbox` é a do aspirador, sem mudança;
  - `entrega`: `entregar(origem, destino, Inscricao.de(origem, tipos)) -> ResultadoEntrega`,
    `ErroOrigemRestaurada`. Técnica contra fato confirmado fora de ordem (PLAT-0019, item 7) e
    alternativas: docstring de `entrega.py`.

### `blatt.web` (extra `[web]`)

- `app.criar_app(modulo=, titulo=, prefixo=, versao=, rotas=, modelos=, estaticos=,
  navegacao=, saude=, limite_corpo=) -> FastAPI` e `app.renderizar(request, modelo, contexto)`;
  modelos do módulo estendem `blatt/base.html`;
- `seguranca`: `Identidade`, `LimiteECsrf`, `CabecalhosSeguranca` (aplicados pela
  `criar_app`), `usuario_do_escopo(scope)`;
- `formulario.formulario_certificado(...)` → dependência que entrega `CertificadoA1(conteudo,
  senha, nome_arquivo, campos)` só em memória;
- `apresentacao`: `moeda`, `numero`, `data`, `data_hora`, `competencia`, `cnpj`, `cpf`,
  `cpf_oculto` (também filtros nos modelos). Só biblioteca padrão: funciona sem o extra;
- `estatico/`: `blatt.css` e `htmx.min.js` 2.0.11 (origem, integridade e SHA-256 em
  [`web/estatico/README.md`](web/estatico/README.md)); `modelos/blatt/`: `base.html`, `erro.html`.

### Origem e dependências

- **Origem:** `blatt.comum` veio de `comum/` deste repositório (cópia da folha, `2bcff8e`), sem
  alteração. `blatt.infra` é a versão estendida do aspirador (`src/blatt/infra`, com
  `dsn_modulo()` e o pacote das migrações como parâmetro), compatível com a da folha;
  `arquivo.py` generaliza o `PastaImutavel` da folha.
- **Única mudança incompatível em relação às cópias dos módulos (0.1.0):** o pacote das
  migrações passou a ser **obrigatório** em `disponiveis()` e `aplicar()`, e `PACOTE_PADRAO`
  deixou de existir. Cada módulo guarda as suas migrações (`sql/NNNN_nome.sql`) no próprio
  pacote e informa o nome dele, por exemplo
  `aplicar(conexao, "blatt.fiscal.aspirador.adaptadores.postgres")`. A 0.2.0 só acrescenta.
- **Dependências:** `psycopg[binary]` (LGPL, com a exceção nominal da
  [PLAT-0008](../../docs/adr/PLAT-0008-driver-postgresql-psycopg.md)). No extra `[web]`, conferidas
  no PyPI em 13/11/2026: FastAPI 0.162.5 (MIT), Starlette 1.10.0 (BSD-3-Clause), Jinja2 3.1.6
  (BSD), Uvicorn 0.54.0 (BSD-3-Clause), python-multipart 0.0.33 (Apache-2.0); as transitivas
  (pydantic, anyio, opentelemetry-api e outras) passam pelo `pip-licenses` do CI. htmx 2.0.11,
  0BSD (A-13), versionado como arquivo. Desenvolvimento: httpx 0.28.1 (BSD-3-Clause), para o
  cliente de teste.

## `blatt` é *namespace package*

Não existe `src/blatt/__init__.py`, nem aqui nem nos módulos (PEP 420; PLAT-0016, item 4.3).
`blatt.comum`, `blatt.infra` e `blatt.web` vêm do pacote instalado; `blatt.folha`, `blatt.fiscal.aspirador` e
os demais, do repositório de cada módulo. Cada subpacote leva o seu `py.typed`.

## Como um módulo instala

O `pyproject.toml` do pacote fica na raiz deste repositório, então a dependência não precisa
de `#subdirectory=`. No repositório do módulo:

```bash
uv add "blatt-plataforma @ git+https://github.com/marcellohalfeld/assembleia@v0.2.0"
```

O `uv` grava `"blatt-plataforma"` em `dependencies` e a origem em `[tool.uv.sources]`
(`blatt-plataforma = { git = "https://github.com/marcellohalfeld/assembleia", rev = "v0.2.0" }`);
o `uv.lock` fixa o commit. Com
`uv add git+https://github.com/marcellohalfeld/assembleia --tag v0.2.0`, a origem fica
`tag = "v0.2.0"`, mais explícita; o efeito é o mesmo.

Módulo com adaptador web: pedir o extra, `uv add "blatt-plataforma[web] @
git+https://github.com/marcellohalfeld/assembleia@v0.2.0"` (no `pyproject.toml`,
`"blatt-plataforma[web]"` em `dependencies`; a origem em `[tool.uv.sources]` é a mesma).
Conferido com o wheel da 0.2.0 num ambiente isolado: sem o extra, `blatt.web.apresentacao` e
`blatt.infra.fatos` funcionam e `blatt.web.app` falha por falta do FastAPI; com o extra, o
Uvicorn serve a aplicação. (Conferido com o uv 0.11 contra um
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
uv sync --all-extras && uv run ruff check . && uv run ruff format --check . \
  && uv run mypy && uv run lint-imports && BLATT_EXIGIR_POSTGRES=1 uv run pytest
```

Os testes de banco sobem um PostgreSQL temporário (`tests/postgres_teste.py`) e usam
migrações fictícias (`tests/migracoes_teste/`); os de fatos criam dois bancos (origem e
destino) e o papel `blatt_entregador` com as concessões da PLAT-0019, item 9. Os da web usam o
módulo fictício `tests/web_exemplo`. O `import-linter` verifica que nenhum subpacote importa
módulo de negócio, que `blatt.comum` não importa `blatt.infra` nem `blatt.web`, que
`blatt.infra` não importa `blatt.web` nem a pilha web e que `blatt.web.apresentacao` funciona
sem o extra; a explicação do primeiro contrato está no `pyproject.toml`. O CI repete a
sequência com os extras, confere as licenças com `pip-licenses` e verifica o conteúdo do wheel
(sem `blatt/__init__.py`, com os `py.typed`, os estáticos e os modelos).
