# Pendências da plataforma

Pontos que dependem de decisão, revisão ou insumo do Marcello e valem para mais de um módulo.
Cada um com proposta (quando houver) e o que bloqueia. Decidido, sai dos abertos e vai para
"Resolvidos", com o lugar onde a decisão ficou registrada. Pendências de um módulo só ficam no
repositório dele.

## Abertas

### A-06. Status das ADRs de plataforma ainda propostas

- PLAT-0001, 0002, 0003 e 0004 continuam **Proposta**, embora o código dos dois módulos já as
  siga. (As 0005, 0006 e 0009, também propostas, foram substituídas pelas PLAT-0018, 0020 e
  0017, aceitas em 12/11/2026; o aceite delas perdeu o objeto.) Na folha, a P-02
  trata só da FOLHA-0007 e da FOLHA-0013.

### A-09. Desenho do cadastro geral e da extração

- **Direção do Marcello (12/11/2026):** "um cadastro geral centralizado, e a folha com uma
  camada a mais de cadastro, com os dados sensíveis dos funcionários, que ficam somente lá"
  (PLAT-0018).
- **Falta decidir:** entidades e vigências do cadastro geral (hoje uma só validade por empresa,
  estabelecimento e lotação, P-27 da folha); fatos publicados; repositório do cadastro;
  quando extrair (depois do MVP da folha, como hoje previsto); como migrar `pessoa`,
  `pessoa_versao` e a lotação para o banco da folha; quem alimenta o cadastro (digitação,
  consulta à Receita).
- **Bloqueia:** a etapa do cadastro e o fim da exceção datada da PLAT-0017, item 9.

### A-10. Guarda do certificado A1 para coleta agendada (futura)

- **Decidido em 12/11/2026** (ver Resolvidas): por enquanto o A1 vai pelo formulário a cada
  operação e fica só na memória, sem guarda (PLAT-0020, item 5.1; ASP-0003).
- **Fica para quando houver coleta agendada:** como guardar o certificado. Opções: OpenBao
  (MPL-2.0); arquivo cifrado no servidor com a chave fora dele; alternativa mais simples a
  pesquisar. Cada uma muda o risco de o certificado ficar no servidor e exige revisar a ASP-0003.
- **Bloqueia:** qualquer coleta agendada que dependa do A1.

### A-12. Prazos legais de guarda

- **Decidido em 12/11/2026** (ver Resolvidas): a retenção padrão do backup não apaga nada.
- **Falta decidir:** por quanto tempo guardar cada tipo de documento (XML de NFS-e e NF-e,
  eventos e recibos do eSocial, folhas, dossiês) e, a partir disso, se e quando ligar uma
  política de retenção. A interpretação dos prazos legais é do Marcello; nenhum prazo foi
  afirmado até aqui.
- **Fontes a conferir** (lembradas de memória pela sessão de 12/11/2026, sem leitura do texto
  oficial e sem afirmar prazo): Código Tributário Nacional (Lei 5.172/1966), arts. 173, 174 e
  195, parágrafo único; Ajuste SINIEF 07/2005 (guarda do XML da NF-e); legislação do FGTS (Lei
  8.036/1990) e a decisão do STF sobre a prescrição do FGTS (ARE 709.212); Código Civil, art.
  1.194; manuais do eSocial e da NFS-e nacional sobre guarda.
- **Até decidir:** o backup não apaga nada (PLAT-0022, item 4.4).

### A-13. Licenças: software de sistema nas imagens de container

- **Decidido em 12/11/2026** (ver Resolvidas): a 0BSD do htmx é tratada como permissiva.
- **Falta decidir:** as imagens base (Debian, Python, PostgreSQL, Caddy) trazem software de
  sistema com licenças diversas, inclusive GPL. A PLAT-0001 trata das dependências do código.
  **Proposta:** registrar numa ADR que a política vale para as dependências do código e que
  componentes do sistema operacional da imagem, usados sem modificação, ficam fora dela (com o
  aviso de licenças na distribuição, como a PLAT-0008 já faz para o psycopg).
- **Bloqueia:** nada no código; esclarece a política de licenças para as imagens da PLAT-0020.

### A-14. FOLHA-0016: modelo de vínculo e contrato da folha

- **Contexto:** a parte da PLAT-0010 que é só da folha (vínculo, contrato, afastamento,
  formato `jsonb`, recibo do eSocial, seção "Implementação") não foi substituída pela
  PLAT-0018 e continua valendo na PLAT-0010.
- **Proposta:** uma sessão do `blatt` escreve a FOLHA-0016 com esse conteúdo, sem mudar o
  sentido, e a PLAT-0010 ganha o status "Substituída pela PLAT-0018 e pela FOLHA-0016".
- **Bloqueia:** nada; só a clareza de onde propor mudança no modelo de vínculo.

### A-15. `chave_vigencia: "mes_do_evento"` na PLAT-0003

- **Contexto:** a ASP-0008 (item 6) usa uma terceira chave de vigência, o mês em que o evento
  fiscal é registrado (prazos da manifestação do destinatário), e já a pôs no
  `comum.schema.json` do aspirador. A PLAT-0003 só prevê `competencia` e `mes_pagamento`
  (P-33 do aspirador).
- **Proposta:** ADR `PLAT-` que acrescente `mes_do_evento` ao item 3 e ao item 6 da PLAT-0003,
  com a definição do aspirador.
- **Bloqueia:** nada no aspirador (a divergência está registrada na ASP-0008); evita que outro
  módulo crie uma quarta chave por conta própria.

### A-16. Branch padrão do aspirador

- **Hoje:** o branch padrão do aspirador é `claude/admiring-mendel-vilgsf`; não há `main`. Os
  links para o aspirador nesta documentação apontam para ele.
- **Proposta:** criar `main` no aspirador a partir do branch atual e torná-lo o padrão; depois,
  trocar os links aqui.
- **Bloqueia:** nada; os links quebram se o branch atual for apagado.

### A-17. Levar a reorganização aos módulos

Em PR de cada repositório (as PLAT-0016 a 0022 foram aceitas em 12/11/2026):

- **todos** (PLAT-0016; passos conferidos num projeto mínimo, detalhe em
  [`src/blatt/README.md`](../src/blatt/README.md)):
  - `uv add "blatt-plataforma @ git+https://github.com/marcellohalfeld/assembleia@v0.1.0"`
    (tag já marcada) ou `@v0.2.0`; com adaptador web,
    `"blatt-plataforma[web] @ ...@v0.2.0"`;
  - apagar `src/blatt/comum/`, `src/blatt/infra/` e `src/blatt/__init__.py`; trocar
    `src/blatt/py.typed` por um `py.typed` em cada subpacote do módulo;
  - chamar `aplicar(conexao, <pacote>)` e `disponiveis(<pacote>)` sempre com o pacote das
    migrações do módulo: o parâmetro passou a ser obrigatório e `PACOTE_PADRAO` não existe mais;
  - `pyproject.toml`: no `mypy`, `explicit_package_bases = true` e `packages` com os pacotes do
    módulo (`blatt.<modulo>`) em vez de `blatt`; no `import-linter`, `root_package = "blatt"`
    continua valendo (junta a parte instalada e a do módulo), e os contratos sobre
    `blatt.comum`/`blatt.infra` podem sair, porque o pacote os verifica;
  - atualizar o trecho "Plataforma" do `CLAUDE.md` (trecho-padrão no
    [PLATAFORMA.md](PLATAFORMA.md)), que ainda cita o manifesto e o `scripts/conferir_comum.py`;
  - até adotar o pacote, não editar a cópia: o manifesto e o script de conferência já saíram
    daqui;
- **`blatt`:** mover as migrações de `src/blatt/infra/postgres/sql/` (0001 a 0006, sem mudar
  o conteúdo, para o hash registrado em `blatt_migracao` continuar valendo) para um pacote da
  folha, por exemplo `blatt.folha.adaptadores.postgres` (escolha da sessão da folha), e passar
  esse pacote em `cli_banco.py` (`aplicar(conexao)`), `tests/conftest.py` e
  `tests/test_migracoes.py` (inclusive o `monkeypatch` de `disponiveis`, que passa a receber o
  pacote); trocar `blatt.__version__` em `tests/test_estrutura.py` (deixa de existir com o
  `__init__.py`); `tests/test_configuracao.py` fica redundante com os testes do pacote; remover
  os arquivos-aviso das ADRs transferidas, com o índice redirecionando (PLAT-0016); FOLHA-0016 (A-14); gravar lotes e retornos do eSocial no arquivo imutável e
  gerar o dossiê da competência (PLAT-0022); extrair casos de uso das CLIs para o adaptador
  web (PLAT-0021);
- **`aspirador`:** as chamadas de migração já passam `PACOTE_MIGRACOES`; remover também
  `src/blatt/comum/ORIGEM.md` e `src/blatt/infra/ORIGEM.md` com as cópias; avaliar remover
  `src/blatt/fiscal/__init__.py`, para que `blatt.fiscal` também seja *namespace* e o
  `fiscal.escrituracao` possa viver noutro repositório; remover
  `docs/plataforma/adr/0014-banco-por-modulo-e-orquestrador.md` e o aviso `docs/PLATAFORMA.md`
  (PLAT-0016); renomear o papel
  `blatt_orquestrador` para `blatt_entregador` (PLAT-0019); decidir numa `ASP-` o endereço por
  hash do arquivo de originais (PLAT-0022);
- **`oper`:** ADRs `OPER-` de implantação, entregador, portal e backup (PLAT-0019 a 0022).

O que cada repositório faz para **adotar a 0.2.0** (tag marcada em 13/11/2026; API em
[`src/blatt/README.md`](../src/blatt/README.md)):

- **todos:** ler `BLATT_DIR_ARQUIVO`, `BLATT_DIR_DADOS` e `BLATT_DIR_PARAMETROS` só por
  `blatt.infra.configuracao` (`dir_arquivo`/`dir_arquivo_opcional`, `dir_dados`,
  `dir_parametros`); o comando de verificação do banco (contrato da imagem do `oper`, item 8)
  chama `blatt.infra.postgres.migracoes.conferir(conexao, pacote)` e sai com 1 se levantar
  `ErroMigracao`; o adaptador web nasce com `blatt.web.app.criar_app` sob o prefixo do módulo,
  seguindo [contratos/web.md](contratos/web.md); quem passar a consumir fatos copia
  `blatt.infra.fatos.ddl.ddl_consumidor()` para uma migração própria e consome com
  `proximos_da_inbox` e `marcar_processado`;
- **`blatt`** (P-65): trocar `configuracao_local.py` pelas funções do pacote (a
  `dir_arquivo` da folha equivale a `dir_arquivo_opcional`); trocar o `PastaImutavel` por
  `blatt.infra.arquivo.ArquivoImutavel` (mesma gravação; `gravar` devolve `ArquivoGravado`, com
  `novo`), mantendo layout e índice na folha; `blatt-banco conferir-migracoes` sobre `conferir()`;
  a `outbox` da folha, quando houver consumidor, com `ddl.ddl_outbox("folha")` e
  `gravar_na_outbox`;
- **`aspirador`:** a `outbox` dele já é a do DDL de referência (sem migração); trocar o
  `INSERT` de `publicar` por `blatt.infra.fatos.postgres.gravar_na_outbox(conexao,
  Envelope(...))` é opcional (o entregador não exige nada de quem grava), mas tira o SQL
  duplicado; o `SELECT` na `outbox` para `blatt_portal` (PLAT-0019, item 11) entra numa
  migração nova quando houver portal; a pasta de originais pode passar a gravar por
  `ArquivoImutavel` quando a `ASP-` do endereço por hash for decidida (PLAT-0022);
- **`oper`:** o entregador é um processo pequeno que, para cada inscrição do arquivo
  versionado, abre a origem em `autocommit` e o destino como `blatt_entregador` e chama
  `blatt.infra.fatos.entrega.entregar(origem, destino, Inscricao.de(origem, tipos))` até
  `lidos < lote` e `aguardando` falso; `ErroOrigemRestaurada` para a inscrição e vira alerta
  (procedimento de restauração). A ADR `OPER-` do entregador registra a técnica do item 7
  (docstring de `entrega.py`: espera pelas transações com bloqueio de escrita na `outbox` em
  `pg_locks` e relê até a maior sequência vista) e a A-20. O portal responde `GET /autenticar`
  como em [contratos/web.md](contratos/web.md), item 3, e não usa o nome de *cookie*
  `__Host-blatt-csrf`; ligar os encaixes do `Caddyfile`; `healthcheck` dos módulos em
  `http://localhost:8000/saude`; `BLATT_WEB_NAVEGACAO` no `environment` dos módulos; o
  provisionamento continua dando `CONNECT` e `USAGE` em `public` aos papéis de operação.

### A-21. Wiki normativa: publicar as regras e os parâmetros que os módulos já guardam

- **Origem:** etapa C3 e pendência A-10 do "plano de convergência" de 08/11/2026 (PR #2 deste
  repositório, fechado em 13/11/2026 por ter sido superado pelas PLAT-0016 a PLAT-0022). É a
  única parte daquele plano que as ADRs aceitas não cobrem.
- **Contexto:** a folha já guarda as normas de forma estruturada (`parametros/tabelas/`, com
  valor, vigência, base legal e hash; `docs/dominio/regras/`, com regra, interpretação adotada
  e casos-ouro), e o aspirador começou a fazer o mesmo. Uma wiki escrita à mão seria mais uma
  cópia que diverge.
- **Proposta (do plano de 08/11, a rever):** ADR `PLAT-` que faça desses formatos um contrato de
  todos os módulos e defina a wiki como páginas geradas a partir deles, separando norma (link
  oficial), parâmetro (valor, vigência, hash) e interpretação adotada (quem decidiu, quando, com
  que fonte). Com a PLAT-0021, o lugar natural é o portal ou uma página de cada módulo, com o
  mesmo login, em vez de um repositório novo.
- **Decisão aberta:** se a parte normativa pode ser publicada fora da instância (D5 do plano).
- **Bloqueia:** nada; é entrega nova, a priorizar pelo Marcello.

## Resolvidas

| Data | Decisão | Registro |
| --- | --- | --- |
| 2026-11-03 | **PLAT-0014 aceita** pelo Marcello ("adr 0014 aceita"), com o faseamento dos itens 10 e 11 e o dono de cada dado do item 9. Decidida no repositório da folha (P-57), no mesmo dia da transferência; o aceite foi trazido para cá depois, com as notas de alteração parcial nas PLAT-0005, 0006, 0009 e 0010. | [PLAT-0014](adr/PLAT-0014-banco-por-modulo-e-orquestrador.md); blatt `e4352fc` (PR #19) |
| 2026-11-12 | **PLAT-0016 aceita** pelo Marcello ("plat-0016 aprovada"): um papel por repositório, mapa de módulos, escopo do primeiro MVP, código comum no pacote `blatt-plataforma` instalado por tag do git, `blatt` como *namespace package*, governança mantida da PLAT-0015. A PLAT-0015 passa a substituída. | [PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md); A-08 |
| 2026-11-12 | **A-01** (aceitar a PLAT-0015): perde o objeto; a PLAT-0015 é substituída pela PLAT-0016, aceita, que mantém as regras de governança no item 5. | [PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md), item 5 |
| 2026-11-12 | **A-03** (distribuição do `blatt.comum`): pacote `blatt-plataforma` instalado por tag do git do `assembleia` (público desde 12/11/2026, sem credencial); `blatt` como *namespace package*; fim das cópias e do manifesto. | [PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md), item 4 |
| 2026-11-12 | **A-04, em parte** (antecipar o orquestrador): o `oper` deixa de ser orquestrador, sem banco de integração nem regra de negócio. O entregador que o substitui ficou à espera da PLAT-0019 (ver a linha seguinte). | [PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md), item 1 |
| 2026-11-12 | **A-05** (decisões de plataforma na ASP-0006): mapa de módulos, divisão captura/tratamento e escopo do primeiro MVP passam à plataforma, citando a ASP-0006 (P-25 do aspirador). | [PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md), itens 2 e 3 |
| 2026-11-12 | **A-07** (`blatt.infra` copiado e divergente): a versão canônica é a estendida do aspirador, dentro do `blatt-plataforma` (P-20 do aspirador). | [PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md), item 4 |
| 2026-11-12 | **A-08: PLAT-0017 a PLAT-0022 aceitas** pelo Marcello ("plat-0017 a 0022 aprovadas"): persistência (0017), dono de cada dado e cadastro geral (0018), integração por fatos com entregador sem banco próprio no lugar do orquestrador da PLAT-0014 (0019), infraestrutura e implantação (0020), interface web (0021) e backup (0022). Passam a substituídas as PLAT-0005, 0006, 0009 e 0014; a PLAT-0010, em parte, até existir a FOLHA-0016 (A-14). As pendências que essas ADRs deixam em aberto (A-09 a A-17) continuam abertas. | [PLAT-0017](adr/PLAT-0017-persistencia-postgresql.md) a [PLAT-0022](adr/PLAT-0022-backup-arquivo-imutavel-e-dossies.md) |
| 2026-11-12 | **A-04** (antecipar o orquestrador): o orquestrador dá lugar a um entregador sem banco próprio no `oper`, que entra em uso com o primeiro consumidor. | [PLAT-0019](adr/PLAT-0019-integracao-por-fatos-e-entregador.md) |
| 2026-11-12 | **A-02** (classificação das ADRs transferidas; a PLAT-0010 mistura regra comum e da folha): a regra comum passa à PLAT-0018, item 1; a parte da folha vai para a FOLHA-0016, ainda a escrever (A-14). As demais classificações de 03/11/2026 ficam como estavam. | [PLAT-0018](adr/PLAT-0018-dono-de-cada-dado-e-cadastro.md), item 1; A-14 |
| 2026-11-12 | **P-33 (b) do aspirador**: `fiscal.nfe_manifestada` no índice de contratos, com os demais fatos que o aspirador publica. A parte (a) é a A-15. | [índice de contratos](contratos/README.md) |
| 2026-11-12 | **A-11** (perda máxima do backup): cópia lógica dos bancos toda noite (e antes de cada migração), com perda de até 24 horas; sem arquivamento contínuo do WAL por ora. Marcello: "pode registrar essas pendências como aceitas conforme a sua proposta". | [PLAT-0022](adr/PLAT-0022-backup-arquivo-imutavel-e-dossies.md), item 2.3 |
| 2026-11-12 | **A-12, retenção padrão**: nada é apagado por padrão (sem política de `restic forget`). Os prazos legais de guarda continuam abertos na A-12. Marcello: "pode registrar essas pendências como aceitas conforme a sua proposta". | [PLAT-0022](adr/PLAT-0022-backup-arquivo-imutavel-e-dossies.md), item 4.4 |
| 2026-11-12 | **A-13, htmx**: a licença 0BSD é tratada como permissiva para os fins da PLAT-0001; o htmx pode entrar em código. A parte das imagens de container continua aberta na A-13. Marcello: "pode registrar essas pendências como aceitas conforme a sua proposta". | [PLAT-0021](adr/PLAT-0021-interface-web.md), seção "Licenças" |
| 2026-11-12 | **A-10, uso atual do A1**: enviado pelo formulário a cada operação e mantido só em memória, sem guarda. A guarda para coleta agendada continua aberta na A-10. Marcello: "pode registrar essas pendências como aceitas conforme a sua proposta". | [PLAT-0020](adr/PLAT-0020-infraestrutura-e-implantacao.md), item 5 |
| 2026-11-12 | **Direção da reorganização** dada pelo Marcello: repositórios separados (monorepo descartado), `oper` como operação da instância, entregador no lugar do orquestrador, servidor doméstico com Docker Compose e acesso só pela rede local, interface web, backup em três camadas com restic para disco local e Google Drive, cadastro geral centralizado com os dados sensíveis dos trabalhadores só na folha. | PLAT-0016 a PLAT-0022 (aceitas em 12/11/2026) |
| 2026-11-13 | **A-18** (tag `v0.1.0`): marcada pelo Marcello em `main` (`f05bdb6`) e enviada. | `git ls-remote --tags origin` (13/11/2026) |
| 2026-11-13 | **P-65 da folha, itens (a), (b) e (d)**, do lado do pacote: `dir_arquivo`, `dir_dados`, `dir_parametros` em `blatt.infra.configuracao`; `conferir()` nas migrações; `blatt.infra.arquivo.ArquivoImutavel`. A adoção na folha e o item (c), no `oper`, seguem na A-17. | [`src/blatt/README.md`](../src/blatt/README.md), versão 0.2.0 |
| 2026-11-13 | **A-19** (tag `v0.2.0`): marcada pelo Marcello em `main` (`5a3091d`, merge do PR #4) e enviada. | `git ls-remote --tags origin` (13/11/2026) |
| 2026-11-13 | **Plano de convergência de 08/11/2026 (PR #2) fechado sem merge**, a pedido do Marcello: as etapas C0, C1, C2, C4, C5 e C7 foram decididas de outra forma nas PLAT-0016 a PLAT-0022 (pacote no lugar das cópias, operação no `oper`, adaptador web por módulo no lugar de API e repositório de interface, entregador no lugar do orquestrador); a C6 é a A-10; a C8 é a A-09; a C3 (wiki normativa) virou a A-21. | A-21; PLAT-0016 a PLAT-0022 |
| 2026-11-13 | **A-20 confirmada** pelo Marcello ("a-20 confirmada como está no pacote"): (a) a entrega usa `ON CONFLICT DO NOTHING` sem alvo, sobre uma `inbox` cuja única chave única é o `id`, porque o alvo explícito do item 5 da PLAT-0019 exigiria `SELECT` na coluna e o item 9 dá ao entregador só `INSERT`; a `inbox` não ganha outra chave única; (b) a `entrega_cursor` guarda também o `ultimo_id`, que permite detectar a origem restaurada. | `blatt.infra.fatos` (`ddl.py`, `entrega.py`), tag `v0.2.0`; OPER-0006 do `oper` |
