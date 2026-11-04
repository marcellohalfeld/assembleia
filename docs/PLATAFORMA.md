# Plataforma Blatt: decisões compartilhadas e pontos de integração

Resumo das decisões que valem para todos os módulos da plataforma (folha, cadastro,
`fiscal.aspirador`, orquestrador e os que vierem), das fronteiras ("conectores") que cada um
expõe e do que um módulo novo precisa respeitar para ser integrado sem reescrita.

**Este arquivo vive só no repositório `marcellohalfeld/assembleia`** (PLAT-0015). Os módulos
não o copiam: apontam para cá no `CLAUDE.md` (trecho da seção 14). Quando este resumo e uma
ADR divergirem, vale a ADR.

Origem: o resumo foi escrito no repositório da folha (`marcellohalfeld/blatt`, `main` em
02/11/2026) e transferido em 03/11/2026, já com o aceite da PLAT-0014 (03/11/2026, P-57; blatt
`e4352fc`). Os caminhos de código citados nas seções 3 a 13 são do
repositório da folha, que continua sendo a implementação de referência.

**Numeração.** ADRs de plataforma: `PLAT-NNNN`, em `docs/adr/` deste repositório. ADRs de
módulo: `FOLHA-NNNN` (blatt), `ASP-NNNN` (aspirador), `OPER-NNNN` (orquestrador). As ADRs de
plataforma vindas da folha mantêm o número de origem (a ADR 0014 da folha é a PLAT-0014). A
tabela de correspondência está em [`docs/adr/README.md`](adr/README.md).

**Módulo com decisão diferente:** registra uma ADR própria dizendo qual regra `PLAT-` ela
altera e por quê, só para o seu escopo. Mudança que vale para todos é ADR nova aqui.

---

## 1. Produto e plataforma

- **Blatt** é a folha de pagamento com transmissão ao eSocial para MPEs do Simples Nacional.
  O usuário inicial é um pequeno escritório contábil que opera a carteira de clientes
  (`docs/visao.md`).
- A folha foi desenhada como **um componente de uma plataforma futura** (contábil, fiscal),
  coordenada por um orquestrador. Cada módulo publica fatos de domínio; nenhum chama outro
  diretamente (`docs/contratos/eventos-dominio.md`, rascunho).
- Quem decide interpretação normativa e regras de negócio é o **Marcello** (contador e
  administrador). O código segue a decisão dele, registrada com a fonte.

## 2. Decisões que valem para todos os módulos

| ADR | Decisão | O que significa para um módulo novo |
| --- | --- | --- |
| PLAT-0001 | Python ≥ 3.12, `mypy --strict`, `uv`. Só dependências MIT, BSD, Apache-2.0, ISC, PSF, MPL-2.0 ou PostgreSQL License; LGPL só com ADR; GPL/AGPL/SSPL/BSL proibidas. CI roda `pip-licenses`. | Mesma linguagem, mesma política de licenças, mesma checagem no CI. A licença do próprio Blatt está em aberto: sem `LICENSE`, o código é fechado. |
| PLAT-0002 | Arquitetura hexagonal: `dominio` ← `aplicacao` ← `adaptadores`, verificada pelo `import-linter`. | Mesmas três camadas dentro de `blatt.<modulo>` (seção 3). |
| PLAT-0003 | Parâmetros legais (tabelas, alíquotas, limites) fora do código, em JSON validado por JSON Schema, com vigência real, base legal, fonte, conferência e manifesto SHA-256; números como texto decimal; resolução pelo período de referência de cada tributo, nunca pela data de hoje; fórmulas em código revisado, nunca `eval`. | Tabelas fiscais e contábeis legais seguem o mesmo contrato (seção 8). |
| PLAT-0004 | Uma instância por escritório, mas **toda tabela de negócio tem `tenant_id`** desde a primeira migração, e toda consulta filtra por ele. O tenant é lido num único ponto. | Mesma regra. O `tenant_id` do escritório é o mesmo em todos os módulos da instância (seção 6). |
| PLAT-0005 | Cadastro (empresa, estabelecimento, lotação, pessoa) dentro do Blatt no MVP, **isolado para ser extraído**: pacote próprio, schema próprio, acessado pela folha só por um port, sem chave estrangeira entre schemas. | O módulo novo consome o cadastro **pelo seu próprio port**, nunca importando `blatt.cadastro` no domínio ou na aplicação (seção 5). |
| PLAT-0006 | Infraestrutura aberta: containers OCI, PostgreSQL, fila no próprio PostgreSQL no início, OpenBao para certificados, armazenamento compatível com S3 (sistema de arquivos no MVP; MinIO evitado por ser AGPL). | Mesmos componentes; nada que prenda a um fornecedor. |
| PLAT-0008 | Exceção LGPL nominal para o `psycopg` 3 (`psycopg[binary]`), sem modificação e atrás de adaptador; o CI ignora só ele. | Mesmo driver e mesma exceção, se usar PostgreSQL em Python. |
| PLAT-0009 | SQL explícito, sem ORM; migrações versionadas aplicadas numa transação com *advisory lock* e hash; **schema por módulo**; chaves estrangeiras com `tenant_id` dentro do schema; transação é de quem chama; dinheiro em `numeric(15,2)` lido como `Decimal`; testes contra PostgreSQL real. | Mesmo padrão de persistência (seção 6). |
| PLAT-0014 (aceita em 03/11/2026) | **Um banco PostgreSQL por módulo**, com usuário próprio e migrações próprias; nenhum módulo lê o banco de outro; fatos publicados numa `outbox` na mesma transação do dado e recebidos numa `inbox` com consumo idempotente; um orquestrador sem regra de negócio, com acesso só a `outbox` e `inbox`, entrega e registra. Dados pessoais dos trabalhadores só na folha, sem circular; empresa e quadro societário no cadastro, compartilhados. Fase 1 já (módulos novos); fase 2 depois do MVP da folha (separar folha e cadastro, orquestrador). | O módulo novo nasce com banco próprio, tabela de migrações própria, `outbox`/`inbox` e eventos no contrato da seção 9 (seção 6). Substitui, para módulos novos, o "schema por módulo" da PLAT-0009. |
| PLAT-0010, FOLHA-0011 | Dados pessoais no cadastro (`cadastro.pessoa`, `cadastro.pessoa_versao`), vínculo e contrato na folha; **versões por data de vigência, só acrescentadas** (retificação substitui a versão da mesma data guardando o recibo; nada é apagado). | Mesmo modelo de histórico para qualquer dado que mude no tempo. |

Decisões só da folha, úteis como referência se o módulo novo falar com webservices do
governo: FOLHA-0007 (assinatura XMLDSig implementada no Blatt, conferida pela libxmlsec1 nos
testes; SOAP com a biblioteca padrão; **travas**: só produção restrita, `tpAmb` conferido,
envio só com confirmação, registro local sem segredos; liberar produção exige ADR nova),
FOLHA-0012 (leitura de versões antigas do leiaute por conversão) e FOLHA-0013, proposta (a cadeia
TLS do servidor do eSocial é a GlobalSign Root R46, e não a ICP-Brasil; confiança só no
arquivo informado).

## 3. Estrutura de pacotes e camadas

Um único pacote raiz, `blatt`, com um subpacote por módulo:

```
src/blatt/
  comum/        núcleo compartilhado, sem regra de negócio (AnoMes, CPF/CNPJ, texto eSocial)
  infra/        configuração da instância e PostgreSQL (migrações)
  cadastro/     dominio / aplicacao (ports) / adaptadores (postgres)
  folha/        dominio / aplicacao (casos de uso e ports) / adaptadores (eSocial, postgres, CLI)
  <modulo>/     o módulo novo, com as mesmas três camadas
```

| Camada | Conteúdo | Pode importar |
| --- | --- | --- |
| `dominio` | Regras e cálculos; Python puro, sem I/O | Só a biblioteca padrão e `blatt.comum` |
| `aplicacao` | Casos de uso e **ports** (`typing.Protocol`) para tudo que vem de fora | `dominio`, `blatt.comum` |
| `adaptadores` | Implementações dos ports: banco, arquivos, webservices, CLI | Tudo acima e bibliotecas externas |

Contratos do `import-linter` em vigor na folha (`pyproject.toml`), a replicar para o módulo
novo trocando o nome:

1. camadas `adaptadores > aplicacao > dominio`;
2. o domínio não importa `sqlite3`, `socket`, `http`, `urllib`, `subprocess` nem `psycopg`;
3. domínio e aplicação **não importam outros módulos de negócio nem `blatt.infra`** (na folha:
   "Folha só conhece o cadastro pelo port; o adaptador local é a única ponte");
4. o cadastro não depende da folha;
5. `blatt.comum` e `blatt.infra` não dependem de nenhum módulo de negócio.

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
forbidden_modules = ["blatt.folha", "blatt.cadastro", "blatt.infra"]
```

## 4. Os "conectores": ports e adaptadores existentes

Cada dependência externa da folha entra por um port declarado em
`src/blatt/folha/aplicacao/portas.py`. O que existe hoje:

| Port | Para que serve | Adaptadores |
| --- | --- | --- |
| `FonteParametros` | Carrega as tabelas legais vigentes (PLAT-0003) | `ParametrosEmArquivo` (diretório `parametros/`, com schema e manifesto); `ParametrosFixos` (testes) |
| `FonteCadastro` | Empresa por inscrição, empregador, estabelecimentos e lotações | `cadastro_local` (lê `blatt.cadastro` no mesmo processo) |
| `DadosPessoais` | Pessoa por CPF e versões dos dados pessoais por data | `cadastro_local` |
| `RepositorioVinculos` | Vínculos, contratos, dependentes por vínculo, afastamentos e eventos aplicados, com versões por data | `vinculos_postgres` |
| `HistoricoPagamentos` | Pagamentos do mês da mesma fonte pagadora, para o IRRF somar | `historico_postgres`; `historico_memoria` (linha de comando sem banco) |

O cadastro tem o seu próprio port, `RepositorioCadastro` (`src/blatt/cadastro/aplicacao/portas.py`),
implementado em `src/blatt/cadastro/adaptadores/postgres.py`.

**A ponte entre módulos é um único adaptador.** `src/blatt/folha/adaptadores/cadastro_local.py`
é o único ponto da folha que importa `blatt.cadastro`, fora das linhas de comando que montam
os adaptadores. Se o cadastro virar serviço, troca-se esse adaptador (e a montagem) por um
cliente remoto, e nada mais muda na folha. **É o padrão a seguir no módulo novo**: o port é
definido na aplicação do consumidor, com os tipos que ele precisa (por exemplo,
`EmpregadorCadastrado`), e não com as entidades do fornecedor.

Adaptadores de borda da folha, para referência: eSocial (`adaptadores/esocial/`: XML, XSD,
assinatura, SOAP, download, totalizadores), arquivos JSON de entrada (leitura estrita, valores
monetários como texto), CLIs `blatt-esocial` e `blatt-banco`.

## 5. Cadastro compartilhado

É a primeira peça que outros módulos vão querer. Hoje vive em `blatt.cadastro`, schema
PostgreSQL `cadastro`:

| Entidade | Campos principais | Observação |
| --- | --- | --- |
| `Empresa` | `tenant_id`, tipo e número de inscrição (CNPJ base ou CPF), razão social, classificação tributária (Tabela 08 do eSocial), início de validade | Uma por empregador |
| `Estabelecimento` | `empresa_id`, CNPJ completo (ou CAEPF/CNO, fora do MVP), CNAE preponderante, início de validade | |
| `Lotacao` | `empresa_id`, código, tipo (Tabela 10), FPAS, código de terceiros | Conceito do eSocial |
| `Pessoa` | `tenant_id`, CPF, nome, nascimento | Identificador natural: CPF |
| `VersaoPessoa` | `pessoa_id`, `vigente_desde`, dados em `jsonb`, recibo e Id do evento | Histórico por data (PLAT-0010) |

Regras para quem consome:

- **Chaves naturais** (CNPJ, CPF) mais um **id interno** (UUID). Entre módulos, guarde o id
  interno e, quando fizer sentido, a chave natural; **nunca chave estrangeira entre schemas**
  (a integridade é conferida na aplicação).
- Hoje o cadastro guarda um registro por empresa, estabelecimento e lotação, com uma só
  validade (limite conhecido, P-27 do registro de pendências da folha). Alterações com nova
  vigência ainda não estão modeladas.
- Se o módulo novo precisar de cadastro **antes** da integração (outro repositório), defina
  no módulo novo um port com os campos de que precisa e uma cópia local no próprio banco
  (PLAT-0014, fase 1). Na fase 2, essa cópia passa a ser alimentada por eventos do cadastro;
  nenhum código de domínio deve mudar.
- **Dono de cada dado (PLAT-0014, item 9, decidido em 02/11/2026):** o cadastro passa a ser o
  módulo da **empresa e do quadro societário** (empresa, regime tributário, estabelecimentos,
  sócios e administradores com o mínimo de interesse comum), compartilhados por fatos. Os
  **dados pessoais dos trabalhadores e dependentes** (inclusive os sensíveis: raça/cor, saúde)
  ficam só na folha e não circulam; `Pessoa` e `VersaoPessoa` e a `Lotacao` (conceito do
  eSocial) vão para o banco da folha na fase 2. Um módulo novo guarda cópia só da empresa e dos
  sócios, nunca de trabalhadores.
- A extração do cadastro para banco próprio fica para a fase 2 da PLAT-0014, depois do MVP da
  folha.

## 6. Banco de dados, migrações e tenant

- **PLAT-0014 (aceita em 03/11/2026): um banco PostgreSQL por módulo** no mesmo servidor da
  instância, com usuário próprio, e um banco `orquestrador`. **Módulos novos já nascem assim** (fase 1). A
  folha continua, até depois do MVP dela, num banco com os schemas `cadastro` e `folha`
  (PLAT-0009); a separação é a fase 2.
- Dentro de cada banco, as regras abaixo continuam valendo.
- **Migrações** em `src/blatt/infra/postgres/sql/NNNN_nome.sql`, numeração contínua,
  aplicadas por `blatt.infra.postgres.migracoes`: uma transação, `pg_advisory_xact_lock`,
  registro de versão, nome e SHA-256 em `public.blatt_migracao`; recusa migração aplicada
  alterada e banco mais novo que o código. **Só avança**: migração aplicada nunca é editada.
- **`tenant_id` em toda tabela de negócio**; chaves estrangeiras compostas dentro do schema
  (`FOREIGN KEY (tenant_id, empresa_id) REFERENCES … (tenant_id, id)`); repositórios recebem o
  tenant no construtor, filtram toda consulta e recusam gravar entidade de outro tenant.
- **Configuração num único ponto** (`blatt.infra.configuracao`): `BLATT_TENANT_ID` (UUID do
  escritório) e `BLATT_DSN` (conexão libpq). Nenhum código de negócio lê variáveis de
  ambiente.
- Repositórios não fazem `commit`: a transação é de quem chama.
- Testes de persistência sobem um PostgreSQL temporário (`initdb` + `pg_ctl`, socket local);
  com `BLATT_EXIGIR_POSTGRES=1` (CI), a falta do PostgreSQL é falha, não teste pulado.

**Migrações por módulo (PLAT-0014, item 2):** cada módulo tem a sua sequência (`NNNN_nome.sql`
a partir de 0001) e a sua tabela de controle no próprio banco (`public.blatt_migracao` de cada
banco), com as mesmas garantias acima. Resolve o antigo ponto em aberto da numeração global.

**Tabelas de integração em todo banco de módulo** (PLAT-0014, itens 4 a 6): `outbox` (fatos
publicados, gravados na mesma transação do dado) e `inbox` (fatos recebidos, consumidos de
forma idempotente). O orquestrador tem, em cada banco, um papel com privilégio só de leitura
na `outbox` e de inserção na `inbox`.

## 7. Núcleo comum (`blatt.comum`)

Tipos sem regra de negócio de nenhum módulo, usados por mais de um:

- `AnoMes` (`periodo.py`): mês de um ano, `AAAA-MM`, ordenável. Na folha, especializado em
  `Competencia` e `MesPagamento`, tipos distintos de propósito (PLAT-0003, item 6).
- `cpf_valido`, `cnpj_valido`, `cnpj_base_valida` (`documentos.py`), já com o **CNPJ
  alfanumérico**.
- Regras de texto do eSocial para códigos e campos livres (`texto.py`).

**A fonte canônica é `comum/src/blatt/comum/` deste repositório**, com o hash de cada
arquivo em `comum/MANIFESTO.json` (PLAT-0015). Enquanto não houver distribuição como pacote
(pendência A-03), cada módulo copia os arquivos daqui sem alterar e confere com
`python scripts/conferir_comum.py <caminho do módulo>`. Mudança num deles é feita aqui
primeiro, com o manifesto atualizado, e depois copiada para os módulos.

## 8. Parâmetros legais (contrato da PLAT-0003)

Se o módulo novo usar tabelas legais (alíquotas, faixas, prazos, tabelas oficiais):

```
parametros/
  schemas/comum.schema.json, manifesto.schema.json, <tipo>.schema.json
  tabelas/<tipo>/AAAA-MM.json   (um registro por vigência; nome = vigencia_inicio)
  tabelas/<tipo>/MANIFESTO.json (arquivo → SHA-256)
```

- Envelope comum: `tipo`, `versao_schema`, `chave_vigencia` (`competencia` ou
  `mes_pagamento`), `vigencia_inicio`, `vigencia_fim`, `base_legal` (ato, número, data,
  dispositivo, URL oficial, valores que fundamenta), `fonte`, `conferencia`, `observacoes`,
  `valores` (números como texto decimal).
- Carregador recusa schema inválido, hash divergente, sobreposição ou lacuna de vigência e
  registro com conferência pendente.
- Depois de alterar um registro: `uv run python scripts/atualizar_manifestos.py`.
- Contrato detalhado: `docs/contratos/parametros.md`. Tabelas existentes: `inss_empregado`,
  `inss_contribuinte_individual`, `irrf_tabela`, `irrf_deducoes`, `irrf_redutor`, `fgts`,
  `salario_familia`, `salario_minimo`.

Se as mesmas tabelas forem usadas por mais de um módulo (por exemplo, salário mínimo), elas
ficam num só lugar na integração; até lá, copie o registro com o mesmo hash.

## 9. Integração por eventos de domínio (PLAT-0014; na folha, ainda não implementado)

`docs/contratos/eventos-dominio.md` e PLAT-0014, itens 3 a 7:

- Cada módulo **publica fatos** no passado; não chama os outros. Envelope: identificador único
  (UUID), tipo, versão do schema, `tenant_id`, módulo de origem, instante, identificador de
  correlação, causa (opcional) e conteúdo (dinheiro como texto decimal).
- O conteúdo de cada tipo tem JSON Schema versionado, mantido por quem publica, em
  `contratos/eventos/<tipo>/<versao>.schema.json`; mudança incompatível é versão nova.
- Publicação por `outbox` na mesma transação do dado; recebimento por `inbox`, idempotente.
- O orquestrador lê, roteia, entrega, tenta de novo e registra; **não tem regra de negócio**.
- Consulta síncrona a outro módulo só como exceção justificada, com comportamento definido
  para quando ele estiver fora do ar.
- **Fatos não levam dado pessoal de trabalhador** (PLAT-0014, item 9): informação agregada por
  empresa, competência e rubrica e, se preciso, um identificador opaco (UUID do vínculo), nunca
  o CPF. Dado pessoal que só um módulo usa fica nele.
- Eventos previstos da folha: `folha.competencia_calculada`, `folha.evento_esocial_aceito`,
  `folha.evento_esocial_rejeitado`, `folha.competencia_conciliada`,
  `folha.competencia_fechada` e `folha.lancamentos_contabeis` (partidas dobradas da folha,
  inclusive provisões de férias e 13º; mapeamento rubrica → conta configurável por empresa).

O último é a entrada natural de um **módulo contábil**. Um módulo novo que precise de dados da
folha deve especificar o evento que consome (campos, tipos, unidade monetária como texto
decimal) e propor a mudança neste contrato; não deve ler as tabelas do schema `folha`.

## 10. Convenções de código

- Dinheiro e alíquotas: `decimal.Decimal`, nunca `float`; arredondamento sempre explícito
  (`quantize` com o modo declarado e justificado). Na folha, o arredondamento de INSS e FGTS
  foi decidido pelo que o eSocial devolve (P-08 e P-18: INSS por faixa e FGTS truncados).
- Nunca `eval`/`exec`; fórmulas em código revisado.
- Períodos: o cálculo resolve parâmetros pelo período de referência, nunca pela data de hoje.
- Toda regra cita a base legal (lei, artigo, item do manual) na docstring e em
  `docs/dominio/regras/`.
- Nomes de domínio em português (competência, rubrica, incidência); termos técnicos genéricos
  podem ficar em inglês.
- Entradas em JSON com leitura estrita: chaves conhecidas, valores como texto, sem número
  JSON para dinheiro.
- Ferramentas: `ruff` (linha de 100, regras E, W, F, I, B, UP, S, SIM, RUF), `ruff format`,
  `mypy --strict`, `import-linter`, `pytest`. Sequência obrigatória antes de cada commit:

```bash
uv sync && uv run ruff check . && uv run ruff format --check . \
  && uv run mypy && uv run lint-imports && BLATT_EXIGIR_POSTGRES=1 uv run pytest
```

- CI (GitHub Actions, `.github/workflows/`): a mesma sequência, mais a checagem de licenças
  (`pip-licenses`, falha em GPL/AGPL, ignorando só `psycopg` e `psycopg-binary`).

## 11. Fluxo de trabalho e documentação

- `docs/ROADMAP.md`: etapas, "Onde paramos", histórico de sessões e **wishlist** pós-MVP.
- `docs/PENDENCIAS.md`: todo ponto que depende de decisão, revisão ou insumo do Marcello, com
  proposta e o que bloqueia; decidido, vai para "Resolvidos" com o lugar do registro.
- `docs/adr/`: decisão arquitetural nova ou alterada vira ADR (modelo em `0000-modelo.md`);
  ADR antiga nunca é apagada, é marcada como substituída; só o Marcello aceita. Decisão que
  vale para mais de um módulo é `PLAT-` e nasce no `assembleia`; a sessão de um módulo que
  precisar dela abre a proposta lá, em vez de redigi-la no próprio repositório.
- `docs/dominio/regras/`: cada regra de negócio com base legal citada literalmente e as
  decisões de interpretação, com data e fonte.
- **Casos-ouro**: o Marcello fornece entrada e resultado conferido; o código é escrito até
  bater centavo a centavo (`tests/casos_ouro/`).
- Uma etapa do ROADMAP por sessão; ao fim, ROADMAP e PENDENCIAS atualizados, commit e PR.
- Commits e PRs em português; PR com o que mudou, por quê e a verificação feita.

## 12. Segurança e dados

- Segredos, certificados (`.pfx`, `.p12`) e dados pessoais reais nunca entram no repositório
  (`.gitignore` e teste). Casos com dados reais são anonimizados antes do commit.
- O certificado A1 real **nunca passa pela sessão do Claude Code**: envios reais rodam no
  computador do Marcello, a partir do guia. Os testes usam certificados gerados na hora
  (`tests/pki_teste.py`).
- Webservices do governo: só ambiente de testes (produção restrita) até ADR que libere
  produção; verificação TLS sempre ligada, com confiança só no arquivo de cadeia informado.
- Registros locais de operação sem segredos (nada de senha, chave ou conteúdo assinado).

## 13. O que se aprendeu sobre o ambiente das sessões

Observado nas sessões da folha (outubro de 2026); pode mudar com a configuração do ambiente.

- **Rede da sessão na nuvem:** `www.gov.br`, Planalto, Senado, CONCLA/IBGE e sites de
  fornecedores não resolveram. A Câmara (`www2.camara.leg.br`, "norma atualizada") respondeu e
  foi a fonte dos textos legais conferidos. Quando a fonte primária está fora de alcance, o
  Marcello confere e manda o trecho; o código registra o que foi lido por quem.
- **GitHub:** pelo conector (ferramentas MCP do GitHub), não pela CLI `gh`. Cada sessão
  trabalha num branch designado; PR aberto ao fim, acompanhado até o CI passar.
- **Retomada depois do limite de uso:** a sessão agenda a própria retomada (tarefa
  agendada) com o objetivo e o estado, e apaga o agendamento ao concluir.
- **macOS do Marcello:** zsh não aceita `#` como comentário em comandos colados (os guias não
  põem comentários dentro dos blocos de comando); `.venv` dentro de pasta sincronizada pode
  receber a marca de oculto e quebrar a instalação editável (`chflags -R nohidden .venv`).

## 14. Trecho para o `CLAUDE.md` de cada módulo

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
  `import-linter`; domínio sem I/O.
- Outros módulos só por ports definidos na aplicação deste módulo; nunca importar outro
  módulo no domínio ou na aplicação; nunca ler o banco de outro módulo.
- PostgreSQL com **banco próprio** (PLAT-0014), usuário próprio, `tenant_id` em toda tabela,
  SQL explícito, migrações próprias só para a frente; configuração só em
  `blatt.infra.configuracao`.
- Integração por fatos: `outbox` na mesma transação do dado, `inbox` idempotente; os schemas
  dos fatos que este módulo publica ficam aqui, em `contratos/eventos/`, e são listados no
  índice do `assembleia`.
- Dado pessoal fica só no módulo que o usa e não vai nos fatos publicados; do cadastro, guardar
  só empresa e quadro societário (PLAT-0014, item 9).
- `blatt.comum` é cópia sem alteração do `assembleia` (`comum/`), conferida pelo manifesto.
- Parâmetros legais em `parametros/` com o contrato da PLAT-0003.
- `Decimal` com arredondamento explícito, nunca `float`; nunca `eval`/`exec`; regra com base
  legal citada.
- Só dependências com licença permissiva (PLAT-0001); GPL/AGPL proibidas.
```

## 15. Checklist para a integração futura

- [ ] O módulo está em `blatt.<modulo>`, com os contratos do `import-linter` da seção 3.
- [ ] Nenhum import de `blatt.folha` ou `blatt.cadastro` fora de um adaptador-ponte.
- [ ] Dados de outros módulos chegam por ports próprios; cadastro, pelo port do módulo.
- [ ] Banco próprio com usuário próprio, `tenant_id` em toda tabela (PLAT-0014).
- [ ] Migrações próprias, a partir de 0001, com tabela de controle no próprio banco.
- [ ] `outbox` e `inbox` criadas; fatos publicados na mesma transação do dado; consumo
      idempotente; schemas dos eventos versionados no repositório do módulo.
- [ ] Nenhum dado pessoal de trabalhador no módulo nem nos fatos publicados; cópia do cadastro
      só com empresa e quadro societário.
- [ ] `blatt.comum` igual ao do `assembleia`, conferido com `scripts/conferir_comum.py`.
- [ ] Parâmetros legais no contrato da PLAT-0003; tabelas comuns com o mesmo hash.
- [ ] Integração com a folha especificada como eventos de domínio (seção 9), não como leitura
      direta do schema `folha`.
- [ ] Mesma sequência de checagens e mesma checagem de licenças no CI.

## Referências

Neste repositório:

- [ADRs de plataforma e tabela de correspondência](adr/README.md)
- [Índice dos contratos de eventos](contratos/README.md)
- [Pendências da plataforma](PENDENCIAS.md)

No repositório da folha (implementação de referência):


- [ADRs da folha](https://github.com/marcellohalfeld/blatt/blob/main/docs/adr/README.md)
- [Visão do produto](https://github.com/marcellohalfeld/blatt/blob/main/docs/visao.md)
- [Contrato dos parâmetros](https://github.com/marcellohalfeld/blatt/blob/main/docs/contratos/parametros.md)
- [Contrato dos eventos de domínio](https://github.com/marcellohalfeld/blatt/blob/main/docs/contratos/eventos-dominio.md)
- [Ports da folha](https://github.com/marcellohalfeld/blatt/blob/main/src/blatt/folha/aplicacao/portas.py),
  [port do cadastro](https://github.com/marcellohalfeld/blatt/blob/main/src/blatt/cadastro/aplicacao/portas.py) e
  [adaptador-ponte](https://github.com/marcellohalfeld/blatt/blob/main/src/blatt/folha/adaptadores/cadastro_local.py)
- [Contratos do import-linter e configuração das ferramentas](https://github.com/marcellohalfeld/blatt/blob/main/pyproject.toml)
- [Migrações](https://github.com/marcellohalfeld/blatt/tree/main/src/blatt/infra/postgres/sql)
- [CLAUDE.md](https://github.com/marcellohalfeld/blatt/blob/main/CLAUDE.md),
  [ROADMAP](https://github.com/marcellohalfeld/blatt/blob/main/docs/ROADMAP.md) e
  [PENDENCIAS](https://github.com/marcellohalfeld/blatt/blob/main/docs/PENDENCIAS.md)
