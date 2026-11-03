# PLAT-0014: Um banco de dados por módulo e integração por um orquestrador

> Transferida de `marcellohalfeld/blatt` (`docs/adr/0014-banco-por-modulo-e-orquestrador.md`, commit `2bcff8e`) em 2026-11-03, pela [PLAT-0015](PLAT-0015-governanca-no-assembleia.md). Texto sem alteração, salvo o título e os links, que passaram a apontar para cá ou para o repositório da folha. Nas referências do texto, "ADR NNNN" é o número de origem: ver a tabela de correspondência no [README](README.md).

- **Status:** Proposta
- **Data:** 2026-11-02
- **Decisor:** Marcello
- **Altera:** ADR 0005 (itens 1 a 3: o cadastro passa a ser o módulo da empresa e do quadro
  societário), ADR 0006 (linha "Fila de trabalho"), ADR 0009 (itens 2 e 3), ADR 0010 (item 1:
  os dados pessoais dos trabalhadores ficam na folha, a partir da fase 2) e o rascunho
  `docs/contratos/eventos-dominio.md`. A ADR 0004 continua valendo.
- **Origem:** proposta redigida no repositório `marcellohalfeld/aspirador` (módulo
  `fiscal.aspirador`) em 01/11/2026 e revista no `blatt` em 02/11/2026, a partir do estado do
  `blatt` em `main` 660979f. As ADRs que valem para toda a plataforma ficam no `blatt`; os
  outros repositórios as copiam e citam pelo número.

## Contexto

A plataforma terá vários módulos (folha, cadastro, fiscal, contábil) coordenados por um
orquestrador. Hoje a ADR 0009 põe todos num único banco PostgreSQL por instância, com um schema
por módulo (`cadastro`, `folha`). Isso tem três problemas:

- **O isolamento depende de disciplina.** Nada impede, no banco, que um módulo leia as tabelas
  de outro. A proibição existe só por convenção e pelo `import-linter`.
- **Os módulos não são independentes de fato.** Restaurar um backup, migrar ou substituir um
  módulo afeta o banco de todos.
- **A numeração de migrações fica sem dono.** Com módulos em repositórios separados, a
  sequência única e a tabela `public.blatt_migracao` deixam de funcionar (ponto em aberto da
  seção 6 do `PLATAFORMA.md`).

Objetivo declarado pelo Marcello em 01/11/2026: cada módulo deve poder cair, ser substituído ou
reescrito sem interferir no funcionamento dos outros, e quem junta as informações e as repassa
de um módulo a outro é o orquestrador.

Restrição de hoje, conferida no código da folha: **a folha não só lê o cadastro, ela grava
nele, na mesma transação.** Pela ADR 0010, os dados pessoais ficam no cadastro
(`cadastro.pessoa`, `cadastro.pessoa_versao`) e o vínculo na folha. Na carga dos eventos
baixados, um S-2200 cria a pessoa no cadastro e o vínculo na folha numa única transação por
evento (`folha/adaptadores/cli_banco.py`, com `PessoasLocal.criar_pessoa` e `registrar` em
`cadastro_local.py`). Separar os bancos acabaria com essa atomicidade; o item 9 resolve isso
definindo de quem é cada dado.

Os dois tipos de dado têm interesse diferente na plataforma:

- **Dados pessoais dos trabalhadores e dependentes** (endereço, dependentes, escolaridade,
  raça/cor, deficiência, CID, ASO, afastamentos) só servem à folha (eSocial e cálculo), e parte
  deles é dado pessoal sensível: origem racial e dado referente à saúde (LGPD, art. 5º, II). A
  LGPD manda limitar o tratamento ao mínimo necessário à finalidade (art. 6º, III) e proteger os
  dados (art. 46); cada cópia num banco a mais é mais um lugar a proteger e a responder a um
  pedido do titular.
- **Dados da empresa e do quadro societário** (CNPJ, razão social, regime tributário,
  estabelecimentos, sócios e administradores) interessam a todos os módulos: folha, fiscal,
  contábil.

## Decisão

### Regras da plataforma

1. **Um banco (*database*) PostgreSQL por módulo**, no mesmo servidor da instância: `cadastro`,
   `folha`, `fiscal_aspirador` e assim por diante, além de `orquestrador`.
   - Cada módulo conecta com usuário e senha próprios e só tem privilégio no seu banco. No
     PostgreSQL, uma conexão enxerga um único banco, então o isolamento é imposto pelo
     servidor, não por convenção.
   - Passar um módulo para servidor próprio no futuro é mudar só a configuração de conexão.
   - Continuam valendo, dentro de cada banco, as regras da ADR 0009: SQL explícito,
     `tenant_id` em toda tabela, transação de quem chama, `numeric(15,2)` e testes contra
     PostgreSQL real.
2. **Migrações por módulo.** Cada módulo tem a sua sequência (`NNNN_nome.sql` a partir de 0001)
   e a sua tabela de controle no próprio banco (`public.blatt_migracao` de cada banco), com as
   mesmas garantias do item 2 da ADR 0009: transação única, *advisory lock*, SHA-256, só avança.
3. **Nenhum módulo lê o banco de outro.** Dados de outro módulo chegam:
   - **como regra**, por eventos entregues pelo orquestrador e guardados como cópia local, só
     com os campos de que o módulo precisa;
   - **como exceção**, por consulta síncrona a um port cujo adaptador chama a interface do outro
     módulo (nunca o banco dele). A exceção precisa de justificativa registrada (ADR ou regra do
     módulo) e de comportamento definido para quando o outro módulo estiver fora do ar, porque
     ela faz um módulo depender da disponibilidade do outro. Hoje nenhum módulo tem interface
     remota; até ter, não há consulta síncrona entre módulos.
4. **Publicação por outbox.** Cada módulo grava os fatos que publica numa tabela `outbox` do
   próprio banco, **na mesma transação** do dado que os origina (padrão *transactional
   outbox*): não existe dado gravado sem o fato correspondente, nem fato sem o dado.
5. **Recebimento por inbox.** Cada módulo que consome fatos tem uma tabela `inbox` no próprio
   banco. O consumo é **idempotente**: o módulo processa cada fato uma vez, registra o
   identificador processado e ignora repetições (a entrega é "pelo menos uma vez").
6. **Orquestrador.** Tem banco próprio e, em cada banco de módulo, um papel (*role*) próprio
   com privilégio **só** nessas duas tabelas: leitura da `outbox` e inserção na `inbox`. Nenhuma
   outra tabela de módulo é visível a ele. O orquestrador:
   - lê a `outbox` de cada módulo, entrega cada fato na `inbox` dos módulos inscritos nele e
     registra no seu próprio banco o que foi entregue, a quem e quando (a `outbox` do módulo não
     é alterada por ele);
   - se um destino estiver fora do ar, guarda e tenta de novo depois, mantendo a ordem de
     publicação por módulo de origem;
   - **não contém regra de negócio**: lê, roteia, entrega, tenta de novo e registra. Juntar
     informações de vários módulos para produzir uma informação nova é trabalho de um módulo
     (por exemplo, o contábil), nunca do orquestrador. Esta regra é conferida em toda revisão.
7. **Contrato dos eventos** (torna definitivo o rascunho `eventos-dominio.md`):
   - cada evento é um **fato**, no passado (`fiscal.documento_coletado`, nunca "registre o
     documento");
   - envelope obrigatório: identificador único (UUID), tipo, versão do schema, `tenant_id`,
     módulo de origem, instante, **identificador de correlação** (o mesmo em todos os fatos de
     uma mesma operação, para rastrear de ponta a ponta), **causa** opcional (identificador do
     fato que provocou este) e o conteúdo; dinheiro como texto decimal; datas e competências
     como texto (`AAAA-MM-DD`, `AAAA-MM`);
   - o conteúdo de cada tipo é validado por JSON Schema versionado, mantido pelo **módulo que
     publica**, em `contratos/eventos/<tipo>/<versao>.schema.json` no repositório dele. Mudança
     incompatível é versão nova, publicada ao lado da antiga até os consumidores migrarem;
   - quem publica não sabe quem consome; a lista de inscrições fica no orquestrador.
8. **Fila.** A linha "Fila de trabalho" da ADR 0006 passa a ser: `outbox` e `inbox` em cada
   módulo, e controle de entrega no banco do orquestrador. RabbitMQ (MPL 2.0) continua como
   opção se o volume exigir ou se a plataforma migrar para coreografia (ver Consequências).

### Dono de cada dado (decidido pelo Marcello em 02/11/2026)

9. **Dados pessoais dos trabalhadores ficam só no módulo que os usa; dados da empresa e do
   quadro societário ficam no cadastro e são compartilhados.**
   - **Folha, dona exclusiva dos dados pessoais dos trabalhadores e dependentes**, inclusive
     os dados de eSocial dos sócios e diretores (endereço, dependentes, pró-labore, S-2300). Na
     fase 2, `cadastro.pessoa` e `cadastro.pessoa_versao` passam para o banco da folha, e a
     carga volta a ser atômica dentro dela. Esses dados **não são publicados**: os fatos da
     folha levam informação agregada (por empresa, competência e rubrica) e, quando precisarem
     se referir a um trabalhador, um identificador opaco (o UUID do vínculo), nunca o CPF nem
     outro dado pessoal.
   - **Cadastro, módulo da empresa e do quadro societário**: empresa (CNPJ, razão social,
     regime tributário e anexos do Simples), estabelecimentos (CNPJ completo, CNAE) e sócios e
     administradores, só com o mínimo de interesse comum (CPF, nome, qualificação, participação,
     entrada e saída). Publica fatos como `cadastro.empresa_alterada`,
     `cadastro.estabelecimento_incluido` e `cadastro.socio_incluido`; cada módulo guarda cópia
     local só do que usa.
   - **Conceitos só do eSocial ficam na folha**: a lotação (Tabela 10, FPAS, terceiros) sai do
     cadastro; o código de classificação tributária da Tabela 08 é derivado do regime e do
     anexo que o cadastro publica, ou guardado pela folha.
   - **A carga da folha deixa de gravar empresa e estabelecimento no cadastro**: confere o
     S-1000 e o S-1005 baixados contra a cópia local do cadastro e aponta divergências. Quem
     mantém os dados da empresa é o cadastro (pelo escritório ou por consulta à Receita).
   - **Mesma regra em todo módulo**: dado pessoal que só um módulo usa fica nele (por exemplo,
     o CPF do destinatário de uma nota fiscal fica no `fiscal.aspirador`).

### Faseamento

10. **Fase 1, já:**
    - os itens 1 a 8 são regra para todo módulo novo: o `fiscal.aspirador` nasce com banco
      próprio, tabela de migrações própria, `outbox`, `inbox` (se consumir algo) e contrato de
      eventos;
    - os dados de cadastro de que o aspirador precisa ficam numa cópia local, atrás de um port
      do próprio aspirador (`PLATAFORMA.md`, seção 5), **só com a empresa e o quadro
      societário** (nenhum dado de trabalhador); na fase 2, essa cópia passa a ser alimentada
      por eventos do cadastro, sem mudar o domínio;
    - **a folha não muda durante o MVP dela**: continua num banco com os schemas `cadastro` e
      `folha` (ADR 0009), e o escopo do MVP (só eSocial, sem outras integrações) se mantém.
11. **Fase 2, depois do MVP da folha:**
    - aplicar o item 9: `pessoa` e `pessoa_versao` e a lotação para o banco da folha; quadro
      societário no cadastro; a carga confere empresa e estabelecimento em vez de gravá-los (ADR
      de revisão das ADRs 0005 e 0010);
    - separar `cadastro` e `folha` em bancos próprios, com tabelas de migração próprias;
    - criar `outbox` e `inbox` na folha e no cadastro e publicar os fatos da folha
      (`eventos-dominio.md`);
    - implantar o orquestrador;
    - configuração com uma conexão por módulo em `blatt.infra.configuracao` (por exemplo,
      `BLATT_DSN_FOLHA`, `BLATT_DSN_CADASTRO`, `BLATT_DSN_FISCAL_ASPIRADOR`); `BLATT_TENANT_ID`
      é o mesmo em todos os bancos da instância.

## Alternativas consideradas

- **Schema por módulo num banco único (ADR 0009, situação atual).** Mais simples de operar e
  permite SQL entre módulos, mas o isolamento depende de disciplina, e backup, restauração e
  migração não são independentes. Descartada como alvo; continua na folha até a fase 2.
- **Um servidor PostgreSQL por módulo.** Isolamento máximo, inclusive contra queda do
  servidor, mas multiplica processos, backups e atualizações. Na escala de um escritório, não
  compensa. A decisão permite chegar lá depois mudando só a configuração.
- **Orquestrador lendo e escrevendo diretamente as tabelas dos módulos.** Dispensa `inbox`, mas
  dá ao orquestrador acesso a todo o banco de cada módulo e anula o isolamento do item 1.
  Descartada em favor dos papéis restritos do item 6.
- **Módulos empurrando os fatos ao orquestrador** (cada módulo com um processo que envia a sua
  `outbox`). Dispensa o papel de leitura, mas exige uma interface no orquestrador e um processo
  a mais em cada módulo. Pode substituir a leitura do item 6 depois, sem mudar o contrato.
- **Coreografia** (cada módulo publica numa fila e cada um assina o que quer, sem coordenador).
  Mais flexível, mas o fluxo fica espalhado e é mais difícil de auditar. Para poucos módulos e
  um único escritório, um ponto central que registra o que foi entregue é mais simples.
  Descartada **por agora**; ver abaixo o custo de mudar.
- **Cadastro como registro único de pessoas da plataforma**, alimentado por fatos da folha
  (`folha.dados_pessoais_informados`), ou como dono dos dados pessoais com a folha pedindo a
  gravação a ele (sequência com compensação, *saga*). Descartadas: os outros módulos não
  precisam desses dados, parte deles é sensível, e cada cópia a mais aumenta a exposição; a
  segunda ainda tornaria a carga dependente do cadastro estar no ar.
- **Extrair o cadastro já na fase 1**, porque o aspirador é um segundo consumidor. Exigiria
  resolver o item 9 e mexer na carga da folha no meio do MVP dela; a cópia local atrás de um
  port dá ao aspirador o que ele precisa sem isso.

## Consequências

- **Isolamento real.** Um módulo pode ser restaurado, migrado, reescrito ou substituído sem
  tocar nos outros. A queda de um módulo não derruba os demais; a queda do orquestrador só
  atrasa a troca de informações. A queda do servidor PostgreSQL ainda derruba todos; isso é
  aceito.
- **Sem transação entre módulos.** A consistência entre módulos é eventual: um fato chega ao
  destino segundos ou horas depois. Conferências entre módulos precisam considerar isso, e o
  identificador de correlação permite rastrear o que já chegou.
- **Relatórios cruzados** (folha + fiscal + contábil) não podem ser um SQL único. Passam por
  um módulo que mantenha uma base de leitura alimentada por eventos, ou pelo módulo que já
  agrega (o contábil). É o principal custo desta decisão.
- **Backups e rotinas** passam a ser por banco. No mesmo servidor, um `pg_dumpall` ou backup
  físico ainda cobre todos de uma vez.
- **Migração da folha (fase 2).** Os schemas `cadastro` e `folha` saem do banco atual para
  bancos separados, e as tabelas de pessoas e a lotação passam para o da folha (item 9). A
  leitura da empresa continua pelo port e pelo adaptador-ponte (`cadastro_local.py`), que passa
  a ler a cópia local; a escrita dos dados pessoais deixa de atravessar módulos. Como ainda não
  há dados reais em produção, a migração dos dados existentes é pequena.
- **Menos exposição de dados pessoais.** Os dados dos trabalhadores, inclusive os sensíveis,
  ficam num único banco, com um único dono; os fatos que circulam pela plataforma não os
  carregam.
- **Custo de migrar depois para coreografia:** baixo, **se** os itens 6 e 7 forem respeitados:
  quem publica não conhece o consumidor, eventos são fatos, consumidores são idempotentes e o
  orquestrador não tem regra de negócio. Nesse caso, a troca é de infraestrutura (o
  orquestrador dá lugar a uma fila com tópicos e assinaturas), sem mudança no código dos
  módulos. Se o orquestrador acumular regras de negócio, a mudança vira reescrita.

## Referências

- PostgreSQL, *Managing Databases — Overview*: cada conexão acessa um único banco.
  https://www.postgresql.org/docs/current/manage-ag-overview.html
- PostgreSQL, `GRANT`: privilégios por tabela para um papel.
  https://www.postgresql.org/docs/current/sql-grant.html
- C. Richardson, padrão *Database per service*.
  https://microservices.io/patterns/data/database-per-service.html
- C. Richardson, padrão *Transactional outbox*.
  https://microservices.io/patterns/data/transactional-outbox.html
- C. Richardson, padrão *Idempotent consumer*.
  https://microservices.io/patterns/communication-style/idempotent-consumer.html
- Lei 13.709/2018 (LGPD), arts. 5º, II, 6º, III, 11 e 46, citados de memória (o site do
  Planalto estava fora do alcance da sessão de 02/11/2026; conferir no texto oficial):
  https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- No `blatt`: ADRs 0004, 0005, 0006, 0009 e 0010; `docs/PLATAFORMA.md`, seções 2, 5, 6 e 9;
  `docs/contratos/eventos-dominio.md`; `src/blatt/folha/adaptadores/cli_banco.py` e
  `cadastro_local.py` (carga com cadastro e folha na mesma transação).
