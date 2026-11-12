# PLAT-0016: Mapa de módulos, papel de cada repositório e código comum como pacote

- **Status:** Proposta
- **Data:** 2026-11-12
- **Decisor:** Marcello
- **Substitui:** [PLAT-0015](PLAT-0015-governanca-no-assembleia.md) (inteira) e o item 8 da
  [PLAT-0009](PLAT-0009-persistencia-postgresql.md) (núcleo comum). Traz para a plataforma a
  parte de plataforma da ASP-0006 do aspirador, que continua valendo para o escopo dele.
- **Resolve:** pendências A-01, A-03, A-04, A-05 e A-07 ([PENDENCIAS](../PENDENCIAS.md)).
- **Origem:** sessão de 12/11/2026 com o Marcello (reorganização da plataforma, etapa 0).

## Contexto

Em 12/11/2026 a plataforma tem dois módulos de negócio em uso (folha, no `blatt`, e
`fiscal.aspirador`, no `aspirador`), um repositório de governança (`assembleia`, PLAT-0015) e um
repositório vazio (`oper`), aberto em 03/11/2026 para o orquestrador da PLAT-0014. Conferido nos
repositórios nesse dia:

1. **Código comum copiado e já divergente.** O `blatt.comum` é copiado do `assembleia` para os
   módulos e conferido por manifesto (PLAT-0015, item 4; pendência A-03). O `blatt.infra`
   (configuração e executor de migrações) também foi copiado da folha para o aspirador, e as
   cópias diferem em dois arquivos: o aspirador acrescentou migrações por pacote e `dsn_modulo()`
   (pendência A-07; `src/blatt/infra/ORIGEM.md` do aspirador).
2. **Papéis sobrepostos.** O `oper` foi pensado como orquestrador com banco próprio, mas a
   instância também precisa de quem a opere: subir os serviços, provisionar os bancos, fazer
   backup, agendar coletas e oferecer uma interface. Nada disso tinha dono.
3. **Mapa de módulos fora da plataforma.** A ASP-0006 (aceita em 03/11/2026) criou o módulo
   `fiscal.escrituracao` e registrou o foco do primeiro MVP da plataforma; as duas coisas valem
   além do aspirador (pendência A-05).
4. **Objetivo do Marcello em 12/11/2026:** reduzir sobreposições, consolidar as ADRs e deixar a
   plataforma pronta para produção limitada: ele é o único usuário, num servidor doméstico com
   Docker Compose, acesso só pela rede local e backup como requisito absoluto. Próximos módulos:
   interface web (urgente), depois escrituração fiscal e escrituração contábil. Ele quer poder
   "matar ou substituir qualquer módulo sem grande impacto"; por isso os repositórios continuam
   separados.

O repositório `assembleia` passou a ser público em 12/11/2026 (a página respondeu sem
credencial nessa data), o que elimina o obstáculo da A-03 para instalar código dele por git.

## Decisão

### 1. Um papel por repositório

| Repositório | Papel | Contém | ADRs |
| --- | --- | --- | --- |
| `assembleia` | Regras da plataforma e código comum sem regra de negócio | ADRs `PLAT-`, resumo `docs/PLATAFORMA.md`, índice de contratos, pendências da plataforma e o pacote instalável `blatt-plataforma` (item 4) | `PLAT-` |
| `oper` | Operação da instância | Docker Compose, provisionamento dos bancos e papéis, entregador de fatos ([PLAT-0019](PLAT-0019-integracao-por-fatos-e-entregador.md)), backup ([PLAT-0022](PLAT-0022-backup-arquivo-imutavel-e-dossies.md)), agendamentos e o portal web ([PLAT-0021](PLAT-0021-interface-web.md)) | `OPER-` |
| `blatt` | Negócio: folha de pagamento + eSocial; o cadastro, até a etapa do cadastro ([PLAT-0018](PLAT-0018-dono-de-cada-dado-e-cadastro.md)) | `blatt.folha`, `blatt.cadastro` | `FOLHA-` |
| `aspirador` | Negócio: `fiscal.aspirador`, captura de documentos fiscais eletrônicos | `blatt.fiscal.aspirador` | `ASP-` |
| futuros | Negócio: `fiscal.escrituracao` e o módulo contábil, cada um no seu repositório | `blatt.<modulo>` | prefixo próprio, definido ao criar |

- O `oper` **deixa de ser "orquestrador"**: não tem banco de integração nem regra de negócio,
  e o que ele faz pela integração se limita ao entregador da PLAT-0019.
- Repositório de módulo de negócio contém só o módulo: domínio, aplicação, adaptadores
  (inclusive o adaptador web, PLAT-0021), migrações, contratos dos fatos que publica,
  parâmetros e documentação dele.
- Nenhum repositório guarda cópia de ADR ou do resumo de outro.

### 2. Mapa de módulos

| Módulo | Pacote | Banco | Repositório | Estado em 12/11/2026 |
| --- | --- | --- | --- | --- |
| Folha | `blatt.folha` | `folha` | `blatt` | Em desenvolvimento (MVP da folha); hoje num banco com os schemas `cadastro` e `folha` ([PLAT-0017](PLAT-0017-persistencia-postgresql.md), exceção datada) |
| Cadastro | `blatt.cadastro` | `cadastro` | `blatt` até a etapa do cadastro; depois, a decidir | Dentro da folha; desenho do cadastro geral pendente (PLAT-0018) |
| `fiscal.aspirador` | `blatt.fiscal.aspirador` | `fiscal_aspirador` | `aspirador` | Em uso: NFS-e pelo ADN, NF-e pela SEFAZ, importação de XML, publica fatos |
| `fiscal.escrituracao` | `blatt.fiscal.escrituracao` | `fiscal_escrituracao` | a criar | Previsto (ASP-0006) |
| Contábil | `blatt.contabil` | `contabil` | a criar | Previsto |

A operação (`oper`: portal, entregador, backup) não é módulo de negócio e não entra no mapa
acima; segue as mesmas regras de código (PLAT-0001, PLAT-0002) quando for Python.

**Divisão entre captura e tratamento** (da ASP-0006, itens 1 e 2, na parte que vale para a
plataforma): o `fiscal.aspirador` captura documentos fiscais eletrônicos (ADN, SEFAZ e
importação de XML), guarda os originais e é o único módulo que lê o XML deles; os demais
recebem os campos estruturados nos fatos. O `fiscal.escrituracao` trata: apuração, efeito dos
cancelamentos, conferências, livros e entrega ao contábil por fatos; aceita os fatos do
aspirador e lançamentos digitados de documentos sem XML. O detalhe do escopo do aspirador
continua na ASP-0006.

### 3. Escopo do primeiro MVP da plataforma

Empresas do Simples Nacional, com (ASP-0006, Contexto):

- folha de pagamento com transmissão ao eSocial;
- registro do faturamento (captura pelo aspirador, tratamento pelo `fiscal.escrituracao`);
- escrituração contábil básica.

Pronto para produção limitada: um único usuário (o Marcello), uma instância num servidor
doméstico ([PLAT-0020](PLAT-0020-infraestrutura-e-implantacao.md)), interface web
(PLAT-0021) e backup (PLAT-0022). Ordem declarada em 12/11/2026: interface web, depois
`fiscal.escrituracao`, depois o contábil.

### 4. Código comum: o pacote `blatt-plataforma`

1. **O código sem regra de negócio usado por mais de um módulo fica no `assembleia`**, num
   pacote Python instalável, `blatt-plataforma`, com:
   - `blatt.comum`: `AnoMes`, validação de CPF e CNPJ (inclusive alfanumérico), regras de texto
     do eSocial (o conteúdo atual de `comum/`);
   - `blatt.infra`: configuração da instância (`tenant_id`, conexão por módulo) e executor de
     migrações. A versão canônica é a **estendida do aspirador** (migrações por pacote,
     `dsn_modulo()`), compatível com a da folha, conferida contra os testes dos dois módulos ao
     ser trazida;
   - utilitários de fatos: gravar na `outbox` na transação de quem chama, validar o envelope,
     registrar e ler a `inbox` (PLAT-0019);
   - a base comum da interface web: modelo de página, estilo e utilitários dos adaptadores web
     (PLAT-0021).
   O pacote não importa nenhum módulo de negócio nem contém regra de negócio; o
   `import-linter` do próprio pacote verifica. Tem testes próprios.
2. **Distribuição por tag do git.** Cada módulo declara a dependência apontando para uma tag
   do `assembleia` (forma `blatt-plataforma @ git+https://github.com/marcellohalfeld/assembleia@<tag>#subdirectory=<pasta do pacote>`)
   e o `uv.lock` fixa o commit. O repositório é público: não há credencial no CI nem nas
   sessões. Mudança incompatível no pacote é versão maior nova; cada módulo sobe de versão no
   seu ritmo.
3. **`blatt` vira *namespace package*** (PEP 420): os módulos removem `src/blatt/__init__.py`, e
   o pacote `blatt-plataforma` também não o tem. Assim `blatt.comum` e `blatt.infra` vêm do
   pacote instalado, e `blatt.folha` ou `blatt.fiscal.aspirador`, do módulo.
4. **Acabam as cópias e os manifestos de conferência** (`comum/MANIFESTO.json`,
   `scripts/conferir_comum.py`, `src/blatt/infra/ORIGEM.md` do aspirador) assim que os módulos
   passarem a instalar o pacote.

### 5. Governança (mantida da PLAT-0015)

1. O `assembleia` é o dono das decisões de plataforma; uma decisão comum tem um só lugar.
2. **Prefixos:** `PLAT-` (assembleia), `FOLHA-` (blatt), `ASP-` (aspirador), `OPER-` (oper);
   módulo novo recebe prefixo próprio ao ser criado. Os números já usados não mudam; numeração
   sequencial, nunca reaproveitada. Nos módulos os nomes de arquivo não mudam; o prefixo vale
   nos índices e nas citações. "ADR NNNN" sem prefixo em texto anterior a 03/11/2026 é o número
   de origem no repositório onde foi escrito (tabela de correspondência em
   [`docs/adr/README.md`](README.md)).
3. **Como nasce uma decisão de plataforma:** a sessão de um módulo que precisar mudar uma regra
   `PLAT-` registra o ponto nas pendências do módulo e abre a proposta aqui, como ADR `PLAT-`
   em status Proposta. Divergência que vale só para um módulo é ADR do módulo, citando a regra
   `PLAT-` que altera. Uma ADR `PLAT-` que afete um módulo é acompanhada de pendência ou PR no
   repositório dele.
4. **Só o Marcello muda status para Aceita**, e o status de uma `PLAT-` muda só aqui; o módulo
   aponta para cá.
5. **Nada de cópia de decisão nos módulos:** os módulos apontam para o `assembleia` no
   `CLAUDE.md` (trecho-padrão no `PLATAFORMA.md`). A única forma de compartilhar código é o
   pacote do item 4.
6. ADR antiga nunca é apagada nem reescrita; ganha status "Substituída por PLAT-NNNN". A ADR
   nova é autocontida: quem a lê não precisa abrir a substituída para saber a regra vigente.

## Alternativas consideradas

- **Monorepo** (todos os módulos, o comum e a operação num repositório só). Considerado de novo
  em 12/11/2026: elimina as cópias e deixa uma sessão ver tudo. Descartado: o Marcello quer
  poder matar ou substituir um módulo sem grande impacto, e repositórios separados mantêm a
  fronteira visível (histórico, CI, permissões e dependências por módulo). O custo de
  coordenação entre repositórios fica com o pacote versionado do item 4.
- **Continuar com cópia e manifesto** (opção 2 da A-03). Não exige empacotamento, mas a
  divergência já aconteceu com o `blatt.infra` (A-07) e cresce com cada módulo novo.
- **Repositório próprio para o pacote comum.** Separa regras de código, mas acrescenta um
  repositório a mais para um pacote pequeno; o `assembleia` já guardava o `comum` canônico.
  Pode ser revisto se o pacote crescer.
- **Publicar o pacote num índice (PyPI ou índice privado).** Dá versões resolvidas por
  `pip`/`uv` sem git, mas exige conta, publicação e, no índice privado, infraestrutura. A tag
  do git dá o mesmo resultado para um único usuário.
- **`oper` como orquestrador com banco próprio** (PLAT-0014, item 6; PLAT-0015, item 6).
  Substituído pelo entregador da PLAT-0019 e pelo papel de operação deste item 1.
- **Governança no `oper`.** Descartada pela PLAT-0015 e mantida descartada: as regras não
  devem morar junto do código de operação.

## Consequências

- Uma etapa 1, depois do aceite: criar o pacote `blatt-plataforma` no `assembleia` (a partir de
  `comum/` e do `blatt.infra` do aspirador, com os testes que hoje estão na folha), marcar a
  primeira tag e, em PR de cada módulo, trocar as cópias pela dependência e remover
  `src/blatt/__init__.py`. Até lá, valem as cópias e o manifesto.
- **Limpeza nos módulos** (PR em cada um, depois do aceite): no `blatt`, os arquivos-aviso das
  ADRs transferidas (`docs/adr/0001` a `0006`, `0008`, `0009`, `0010` e `0014`) são removidos,
  e o índice `docs/adr/README.md` passa a redirecionar para cá; no `aspirador`, a cópia
  `docs/plataforma/adr/0014-banco-por-modulo-e-orquestrador.md` e o aviso `docs/PLATAFORMA.md`
  saem, e o índice `docs/adr/README.md` redireciona.
- O `CLAUDE.md` do `assembleia` passa a admitir código compartilhado sem regra de negócio
  (o pacote); continua sem código de módulo e sem código de operação.
- Instalar um módulo passa a depender de o GitHub estar acessível; o `uv.lock` fixa o commit,
  e o servidor constrói as imagens a partir de tags (PLAT-0020).
- Com *namespace package*, a configuração do `mypy` e do `import-linter` de cada módulo
  precisa reconhecer `blatt` sem `__init__.py`; a conferir na etapa 1, no primeiro módulo.
- Onde ADRs antigas falam em "orquestrador" (PLAT-0002, Consequências; PLAT-0014), leia
  "entregador e portal do `oper`", conforme a PLAT-0019 e a PLAT-0021.
- A ASP-0006 continua valendo para o escopo do aspirador; a lista de módulos e o escopo do MVP
  passam a ser citados por esta ADR (P-25 do aspirador).

## Referências

- [PLAT-0015](PLAT-0015-governanca-no-assembleia.md) (governança, substituída por esta),
  [PLAT-0014](PLAT-0014-banco-por-modulo-e-orquestrador.md) (orquestrador, itens 6 e 11) e
  [PLAT-0009](PLAT-0009-persistencia-postgresql.md), item 8 (núcleo comum).
- ASP-0006, escopo de captura (aspirador):
  [docs/adr/0006-escopo-de-captura.md](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/docs/adr/0006-escopo-de-captura.md).
- Extensões do `blatt.infra` no aspirador:
  [src/blatt/infra/ORIGEM.md](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/src/blatt/infra/ORIGEM.md).
- PEP 420, *Implicit Namespace Packages*: https://peps.python.org/pep-0420/ (citado de memória,
  a conferir; o site não abriu na sessão de 12/11/2026).
- uv, dependências de git com `subdirectory`:
  https://docs.astral.sh/uv/concepts/projects/dependencies/ (citado de memória, a conferir; o
  site não abriu na sessão de 12/11/2026).
- Repositório público do `assembleia`: https://github.com/marcellohalfeld/assembleia (respondeu
  sem credencial em 12/11/2026).
- Formato das ADRs: Michael Nygard, *Documenting Architecture Decisions* (2011),
  https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions (citado como nas ADRs
  anteriores; não abriu na sessão de 12/11/2026).
