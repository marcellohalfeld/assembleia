# Plataforma Blatt: regras comuns

> Este resumo reflete as ADRs aceitas, inclusive as PLAT-0016 a PLAT-0022, aceitas em
> 12/11/2026. Quando este resumo e uma ADR divergirem, vale a ADR.

Resumo, por tema, das regras que valem para todos os módulos da plataforma e do que um módulo
precisa respeitar para ser integrado sem reescrita. Cada item aponta para a ADR que o decide.
Este arquivo vive só no `assembleia`; os módulos não o copiam e apontam para cá no `CLAUDE.md`
(trecho na seção 11). Índice das ADRs e tabela de correspondência dos números antigos:
[`docs/adr/README.md`](adr/README.md).

Quem decide interpretação normativa e regras de negócio é o **Marcello** (contador). O código
segue a decisão dele, registrada com a fonte.

## 1. Repositórios e módulos

[PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md)

| Repositório | Papel | ADRs |
| --- | --- | --- |
| `assembleia` | Regras (ADRs, este resumo, índice de contratos, pendências) e o pacote `blatt-plataforma` | `PLAT-` |
| `oper` | Operação da instância: Docker Compose, provisionamento dos bancos, entregador de fatos, backup, agendamentos, portal web | `OPER-` |
| `blatt` | Folha de pagamento + eSocial (e o cadastro, até a etapa do cadastro) | `FOLHA-` |
| `aspirador` | `fiscal.aspirador`: captura de documentos fiscais eletrônicos | `ASP-` |
| futuros | `fiscal.escrituracao` (tratamento fiscal) e contábil | a definir |

- Repositório de módulo contém só o negócio do módulo. Os repositórios continuam separados
  para que qualquer módulo possa ser desligado ou substituído sem grande impacto.
- Primeiro MVP da plataforma: empresas do Simples Nacional, com folha (eSocial), registro do
  faturamento (aspirador captura, `fiscal.escrituracao` trata) e escrituração contábil básica;
  produção limitada, um usuário. Ordem: interface web, `fiscal.escrituracao`, contábil.
- **Governança:** decisão que vale para mais de um módulo é `PLAT-` e nasce aqui, como
  Proposta; só o Marcello aceita. Divergência só de um módulo é ADR do módulo citando a regra
  `PLAT-` que altera. ADR antiga nunca é apagada nem reescrita; ganha status "Substituída".
  Nenhuma cópia de ADR ou deste resumo nos módulos.

## 2. Regras por tema

| Tema | Regra | ADR |
| --- | --- | --- |
| Linguagem | Python ≥ 3.12, `mypy --strict`, `uv` | [PLAT-0001](adr/PLAT-0001-python-e-politica-de-licencas.md) |
| Licenças | Permitidas sem consulta: MIT, BSD (2 e 3 cláusulas), Apache-2.0, ISC, PSF, MPL-2.0, PostgreSQL License. LGPL só com ADR (exceção nominal: `psycopg`). Proibidas: GPL, AGPL, SSPL, BSL, *source available*, proprietário. CI roda `pip-licenses`. 0BSD tratada como permissiva (12/11/2026, A-13; htmx, PLAT-0021). A licença do próprio Blatt está em aberto: sem `LICENSE`, o código é fechado | [PLAT-0001](adr/PLAT-0001-python-e-politica-de-licencas.md), [PLAT-0008](adr/PLAT-0008-driver-postgresql-psycopg.md) |
| Arquitetura | Hexagonal: `dominio` ← `aplicacao` ← `adaptadores`, verificada pelo `import-linter`; domínio sem I/O | [PLAT-0002](adr/PLAT-0002-arquitetura-hexagonal.md) |
| Parâmetros legais | Fora do código, em JSON com JSON Schema, vigência real, base legal, fonte, conferência e manifesto SHA-256; números como texto decimal; resolução pelo período de referência de cada tributo (competência; mês de pagamento para IRRF), nunca pela data de hoje; fórmulas em código revisado | [PLAT-0003](adr/PLAT-0003-contrato-dos-parametros-externos.md) |
| Instância e tenant | Uma instância por escritório; `tenant_id` em toda tabela de negócio, lido num único ponto | [PLAT-0004](adr/PLAT-0004-instancia-por-escritorio.md) |
| Código comum | Pacote `blatt-plataforma` (0.2.0: `blatt.comum`; `blatt.infra` com configuração, arquivo imutável, migrações e fatos; `blatt.web` no extra `[web]`), instalado por tag do git do `assembleia`; `blatt` como *namespace package*; sem regra de negócio. Instalação, API e versões: [`src/blatt/README.md`](../src/blatt/README.md) | [PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md) |
| Persistência | PostgreSQL, um banco e um usuário por módulo; SQL explícito; migrações por módulo (transação, *advisory lock*, SHA-256, só avança); FKs compostas com `tenant_id`; transação de quem chama; `numeric(15,2)`/`Decimal`; testes contra PostgreSQL real. Exceção datada: a folha, num banco com schemas `cadastro` e `folha`, até a etapa do cadastro | [PLAT-0017](adr/PLAT-0017-persistencia-postgresql.md) |
| Dono de cada dado | Histórico por data de vigência, só acrescentado. Dado pessoal fica só no módulo que o usa e não vai nos fatos; dados pessoais dos trabalhadores só na folha; empresa e quadro societário num cadastro geral | [PLAT-0018](adr/PLAT-0018-dono-de-cada-dado-e-cadastro.md) |
| Integração | Fatos no passado, `outbox` na mesma transação do dado, `inbox` idempotente; envelope comum; JSON Schema versionado por quem publica; nenhum módulo lê tabela de negócio de outro; entregador sem regra de negócio e sem banco próprio, com cursor no destino | [PLAT-0019](adr/PLAT-0019-integracao-por-fatos-e-entregador.md) |
| Infraestrutura | Docker Compose num servidor doméstico; PostgreSQL, Caddy, um container por módulo, portal, entregador, backup; segredos em arquivos; acesso só pela rede local, TLS da CA interna do Caddy; containers não-root; imagens construídas a partir de tags. A1 pelo formulário, só em memória | [PLAT-0020](adr/PLAT-0020-infraestrutura-e-implantacao.md) |
| Interface web | Adaptador web em cada módulo, com os mesmos casos de uso da CLI, sob um prefixo; portal no `oper` com login; Caddy com `forward_auth`; FastAPI + Jinja2 + htmx, sem build de JavaScript | [PLAT-0021](adr/PLAT-0021-interface-web.md) |
| Backup | Arquivo imutável por SHA-256 para todo arquivo trocado com órgão público; `pg_dump -Fc` por banco toda noite e antes de cada migração (perda máxima de 24 horas); nada é apagado por padrão; dossiê legível por empresa e período; restic cifrado para disco local e Google Drive; teste de restauração mensal | [PLAT-0022](adr/PLAT-0022-backup-arquivo-imutavel-e-dossies.md) |

## 3. Estrutura de um módulo

```
src/blatt/            sem __init__.py (namespace package, PLAT-0016)
  <modulo>/
    dominio/          regras e cálculos; Python puro, sem I/O
    aplicacao/        casos de uso e ports (typing.Protocol) para tudo que vem de fora
    adaptadores/      banco, arquivos, webservices, CLI, web
contratos/eventos/    schemas dos fatos que o módulo publica
parametros/           tabelas legais (PLAT-0003), se houver
```

| Camada | Pode importar |
| --- | --- |
| `dominio` | Só a biblioteca padrão e `blatt.comum` |
| `aplicacao` | `dominio`, `blatt.comum` |
| `adaptadores` | Tudo acima, `blatt.infra`, a base web e bibliotecas externas |

Contratos mínimos do `import-linter`, trocando `<modulo>` pelo nome:

```toml
[[tool.importlinter.contracts]]
name = "Camadas do <modulo>: adaptadores > aplicacao > dominio"
type = "layers"
layers = ["blatt.<modulo>.adaptadores", "blatt.<modulo>.aplicacao", "blatt.<modulo>.dominio"]

[[tool.importlinter.contracts]]
name = "Domínio do <modulo> não faz I/O"
type = "forbidden"
source_modules = ["blatt.<modulo>.dominio"]
forbidden_modules = ["sqlite3", "socket", "http", "urllib", "subprocess", "psycopg"]

[[tool.importlinter.contracts]]
name = "<modulo> só conhece outros módulos por ports"
type = "forbidden"
source_modules = ["blatt.<modulo>.dominio", "blatt.<modulo>.aplicacao"]
forbidden_modules = ["blatt.folha", "blatt.cadastro", "blatt.fiscal", "blatt.infra"]
```

(No último contrato, tire da lista o próprio módulo; por exemplo, no aspirador, use
`blatt.fiscal.escrituracao` em vez de `blatt.fiscal`.)

Com `blatt` como *namespace package*, o `import-linter` usa `root_package = "blatt"` (o grafo
junta a parte instalada pelo `blatt-plataforma` e a do módulo) e o `mypy` precisa de
`explicit_package_bases = true`, com `mypy_path = "src"` e `packages = ["blatt.<modulo>"]`;
conferido num projeto mínimo (ver [`src/blatt/README.md`](../src/blatt/README.md)).

**Dados de outro módulo** entram por um port definido na aplicação de quem consome, com os
tipos de que ele precisa (não as entidades do fornecedor), e uma cópia local alimentada por
fatos. A folha tem o exemplo de adaptador-ponte enquanto o cadastro mora com ela
(`cadastro_local.py`, PLAT-0018, item 6).

## 4. Banco, integração e dados

- **Banco próprio** por módulo, usuário próprio, migrações `NNNN_nome.sql` a partir de 0001 no
  próprio pacote (diretório `sql/`), aplicadas por `blatt.infra.postgres.migracoes`, que recebe
  o nome desse pacote como parâmetro obrigatório (PLAT-0017).
- **Configuração num único ponto** (`blatt.infra.configuracao`): `BLATT_TENANT_ID`,
  `BLATT_DSN_<MODULO>`, `BLATT_DIR_ARQUIVO`, `BLATT_DIR_DADOS`, `BLATT_DIR_PARAMETROS` e
  `BLATT_WEB_NAVEGACAO`; a senha vem de arquivo de segredo (PLAT-0017, item 5; PLAT-0020).
- **Fatos** (PLAT-0019): o módulo que publica tem `outbox` (com `sequencia`) e o contrato em
  `contratos/eventos/`, listado no [índice de contratos](contratos/README.md); o que consome
  tem `inbox` e `entrega_cursor`. O entregador do `oper` copia da `outbox` para a `inbox`,
  com papel restrito a essas tabelas. Consulta síncrona a outro módulo só como exceção
  justificada. Envelope, SQL, DDL de referência (que o módulo copia para uma migração própria)
  e a função de entrega estão em `blatt.infra.fatos`.
- **Dados pessoais** (PLAT-0018): só no módulo que os usa; fatos levam informação agregada e,
  se preciso, um identificador opaco. Do cadastro, cada módulo guarda só empresa e quadro
  societário.
- **Arquivos crus** trocados com órgão público vão para o arquivo imutável, com o SHA-256 no
  banco; o fechamento de um período gera o dossiê legível (PLAT-0022). Gravação e leitura:
  `blatt.infra.arquivo.ArquivoImutavel`; o layout e o índice são de cada módulo.
- **Interface web** (PLAT-0021): o adaptador web usa `blatt.web.app.criar_app`, sob o prefixo
  do módulo, na porta 8000; usuário no cabeçalho `X-Blatt-Usuario`, CSRF e upload sensível em
  memória pela base. Contrato com o portal e o Caddy: [contratos/web.md](contratos/web.md).

## 5. Parâmetros legais

Se o módulo usar tabelas legais (PLAT-0003):

```
parametros/
  schemas/comum.schema.json, manifesto.schema.json, <tipo>.schema.json
  tabelas/<tipo>/AAAA-MM.json   (um registro por vigência; nome = vigencia_inicio)
  tabelas/<tipo>/MANIFESTO.json (arquivo → SHA-256)
```

Envelope: `tipo`, `versao_schema`, `chave_vigencia`, `vigencia_inicio`, `vigencia_fim`,
`base_legal`, `fonte`, `conferencia`, `observacoes`, `valores` (números como texto decimal). O
carregador recusa schema inválido, hash divergente, sobreposição ou lacuna de vigência e
registro com conferência pendente. A chave `mes_do_evento`, usada pelo aspirador, ainda não está
na PLAT-0003 (pendência A-15). Contrato detalhado de referência: `docs/contratos/parametros.md`
do `blatt`.

## 6. Convenções de código

- Dinheiro e alíquotas: `decimal.Decimal`, nunca `float`; arredondamento sempre explícito
  (`quantize` com o modo declarado e justificado).
- Nunca `eval`/`exec`; fórmulas em código revisado.
- Toda regra cita a base legal (lei, artigo, item do manual) na docstring e em
  `docs/dominio/regras/`.
- Nomes de domínio em português; termos técnicos genéricos podem ficar em inglês.
- Entradas em JSON com leitura estrita: chaves conhecidas, dinheiro como texto.
- Ferramentas: `ruff` (linha de 100), `ruff format`, `mypy --strict`, `import-linter`,
  `pytest`. Antes de cada commit:

```bash
uv sync && uv run ruff check . && uv run ruff format --check . \
  && uv run mypy && uv run lint-imports && BLATT_EXIGIR_POSTGRES=1 uv run pytest
```

- CI (GitHub Actions): a mesma sequência, mais a checagem de licenças (`pip-licenses`, falha em
  GPL/AGPL, ignorando só `psycopg` e `psycopg-binary`).

## 7. Fluxo de trabalho

- `docs/ROADMAP.md` (onde paramos), `docs/PENDENCIAS.md` (o que depende do Marcello, com
  proposta e o que bloqueia), `docs/adr/` (modelo em [0000-modelo.md](adr/0000-modelo.md)),
  `docs/dominio/regras/` (regra com base legal e decisões de interpretação, com data e fonte).
- Casos-ouro: o Marcello fornece entrada e resultado conferido; o código é escrito até bater
  centavo a centavo.
- Uma etapa por sessão; ao fim, ROADMAP e PENDENCIAS atualizados, commit e PR. Commits e PRs em
  português, com o que mudou, por quê e o que foi conferido.
- Ambiente das sessões do Claude Code (rede, GitHub, macOS): [ambiente-das-sessoes.md](ambiente-das-sessoes.md).

## 8. Segurança

- Segredos, certificados (`.pfx`, `.p12`) e dados pessoais reais nunca entram em repositório,
  imagem ou log. Casos com dados reais são anonimizados antes do commit.
- O certificado A1 real **nunca passa pela sessão do Claude Code**; os testes usam certificados
  gerados na hora. Na instância, o A1 vem pelo formulário e fica só em memória (PLAT-0020,
  item 5); guarda para coleta agendada em aberto (A-10).
- Webservices do governo: travas de cada módulo (só ambiente de testes até ADR que libere
  produção, verificação TLS sempre ligada, envio com confirmação).
- Acesso à instância só pela rede local, por HTTPS, com login no portal (PLAT-0020, PLAT-0021).

## 9. O que ainda está em aberto

Ver [PENDENCIAS](PENDENCIAS.md): aceite das PLAT-0001 a 0004 (A-06),
desenho do cadastro (A-09), guarda do A1 para coleta agendada (A-10), prazos legais de guarda
(A-12), licenças do software de sistema nas imagens (A-13), FOLHA-0016 (A-14), `mes_do_evento`
(A-15), branch padrão do aspirador (A-16), levar a reorganização aos módulos e adotar a 0.2.0
(A-17), tag `v0.2.0` do `blatt-plataforma` (A-19), `ON CONFLICT` da `inbox` e coluna
`ultimo_id` do cursor (A-20).

## 10. Implementação de referência

Os padrões acima foram implementados primeiro na folha e no aspirador. Para ver um exemplo,
leia o código deles; os caminhos podem mudar sem que a regra mude:

- folha: [ADRs](https://github.com/marcellohalfeld/blatt/blob/main/docs/adr/README.md),
  [ports](https://github.com/marcellohalfeld/blatt/blob/main/src/blatt/folha/aplicacao/portas.py),
  [adaptador-ponte do cadastro](https://github.com/marcellohalfeld/blatt/blob/main/src/blatt/folha/adaptadores/cadastro_local.py),
  [`pyproject.toml`](https://github.com/marcellohalfeld/blatt/blob/main/pyproject.toml),
  [contrato dos parâmetros](https://github.com/marcellohalfeld/blatt/blob/main/docs/contratos/parametros.md),
  [eventos previstos](https://github.com/marcellohalfeld/blatt/blob/main/docs/contratos/eventos-dominio.md);
- aspirador: [ADRs](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/docs/adr/README.md),
  [contratos dos fatos](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/contratos/eventos/README.md),
  [`outbox`](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/src/blatt/fiscal/aspirador/adaptadores/postgres/sql/0001_inicial.sql),
  [provisionamento do banco](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/scripts/sql/provisionar.sql).

## 11. Trecho para o `CLAUDE.md` de cada módulo

Até o módulo adotar o pacote `blatt-plataforma` (A-17), ele continua com a cópia de
`blatt.comum` e `blatt.infra` que já tem; o manifesto e o script de conferência saíram do
`assembleia`, então a cópia não deve ser editada no módulo.

```markdown
## Plataforma

Este módulo faz parte da plataforma Blatt. As decisões que valem para todos os módulos ficam no
repositório **marcellohalfeld/assembleia** (ADRs `PLAT-NNNN` e o resumo `docs/PLATAFORMA.md`).
Leia o resumo antes de qualquer decisão de arquitetura; não copie ADRs nem o resumo para cá.

- ADRs deste módulo ficam em `docs/adr/`, com o prefixo do módulo (`FOLHA-`, `ASP-`, `OPER-`)
  nos índices e citações. "ADR NNNN" sem prefixo em texto anterior a 03/11/2026 é o número de
  origem no repositório onde foi escrito (tabela de correspondência no `assembleia`).
- **Não altere decisão de plataforma neste repositório.** Se o trabalho daqui exigir mudar
  uma regra `PLAT-`, registre em `docs/PENDENCIAS.md` e abra a proposta no `assembleia`.
  Divergência só para este módulo é ADR própria, citando a regra `PLAT-` que altera.
- Pacote `blatt.<modulo>`, camadas `dominio` ← `aplicacao` ← `adaptadores`, verificadas pelo
  `import-linter`; domínio sem I/O. A interface web é um adaptador (`adaptadores/web`) que
  chama os mesmos casos de uso da CLI (PLAT-0021).
- `blatt.comum`, `blatt.infra` e `blatt.web` vêm do pacote `blatt-plataforma`, instalado por
  tag do `assembleia`; não há `src/blatt/__init__.py` (PLAT-0016).
- Outros módulos só por ports definidos na aplicação deste módulo; nunca importar outro
  módulo; nunca ler tabela de negócio de outro módulo.
- PostgreSQL com banco e usuário próprios, `tenant_id` em toda tabela, SQL explícito,
  migrações próprias só para a frente; configuração só em `blatt.infra.configuracao`
  (PLAT-0017).
- Integração por fatos: `outbox` na mesma transação do dado, `inbox` idempotente; os schemas
  dos fatos que este módulo publica ficam aqui, em `contratos/eventos/`, e são listados no
  índice do `assembleia` (PLAT-0019).
- Dado pessoal fica só no módulo que o usa e não vai nos fatos publicados; do cadastro, guardar
  só empresa e quadro societário (PLAT-0018).
- Arquivo recebido de órgão público ou enviado a ele vai para o arquivo imutável, com o SHA-256
  no banco (PLAT-0022).
- Parâmetros legais em `parametros/` com o contrato da PLAT-0003.
- `Decimal` com arredondamento explícito, nunca `float`; nunca `eval`/`exec`; regra com base
  legal citada.
- Só dependências com licença permissiva (PLAT-0001); GPL/AGPL proibidas.
```

## 12. Checklist de um módulo

- [ ] Está em `blatt.<modulo>`, com os contratos do `import-linter` da seção 3 e sem
      `src/blatt/__init__.py`.
- [ ] `blatt-plataforma` instalado por tag do `assembleia`; nenhuma cópia de `comum` ou `infra`.
- [ ] Dados de outros módulos chegam por ports próprios e por fatos; nenhum import de outro
      módulo.
- [ ] Banco e usuário próprios, `tenant_id` em toda tabela, migrações a partir de 0001.
- [ ] `outbox` (se publica) e `inbox` com `entrega_cursor` (se consome); fatos na mesma
      transação do dado; schemas versionados no repositório e listados no índice.
- [ ] Nenhum dado pessoal de trabalhador fora da folha nem nos fatos publicados.
- [ ] Arquivos trocados com órgão público no arquivo imutável, com hash no banco; dossiê no
      fechamento do período.
- [ ] Adaptador web sob o prefixo do módulo, sem regra de negócio, atrás do portal.
- [ ] Parâmetros legais no contrato da PLAT-0003.
- [ ] Mesma sequência de checagens e mesma checagem de licenças no CI.
