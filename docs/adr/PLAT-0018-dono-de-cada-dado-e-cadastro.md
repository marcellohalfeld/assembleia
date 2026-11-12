# PLAT-0018: Dono de cada dado, histórico por vigência e cadastro geral

- **Status:** Proposta
- **Data:** 2026-11-12
- **Decisor:** Marcello
- **Substitui:** [PLAT-0005](PLAT-0005-cadastro-interno-extraivel.md) (inteira), a regra comum
  da [PLAT-0010](PLAT-0010-vinculos-e-dados-pessoais.md) (item 2, versões por data de
  vigência) e o item 9 da [PLAT-0014](PLAT-0014-banco-por-modulo-e-orquestrador.md), com as
  partes de cadastro dos itens 10 e 11 dela.
- **Não substitui:** a parte da PLAT-0010 que é só da folha (modelo de vínculo, contrato,
  afastamento, formato `jsonb`, recibo do eSocial e a seção "Implementação"). Ela continua
  valendo até virar a FOLHA-0016 no `blatt` (pendência em [PENDENCIAS](../PENDENCIAS.md)).
- **Origem:** consolidação de 12/11/2026 e direção dada pelo Marcello nesse dia para o cadastro.

## Contexto

Três ADRs tratavam de quem guarda o quê:

- a PLAT-0005 pôs o cadastro (empresa, estabelecimento, pessoa) dentro da folha no MVP,
  isolado para ser extraído depois;
- a PLAT-0010 (aceita em 27/10/2026) pôs os dados pessoais no cadastro e o vínculo na folha,
  com uma regra que vale para qualquer dado que mude no tempo: versões por data de vigência,
  só acrescentadas;
- a PLAT-0014, item 9 (aceita em 03/11/2026), corrigiu as duas: dados pessoais dos
  trabalhadores ficam só na folha; o cadastro fica com a empresa e o quadro societário.

Os dois tipos de dado têm interesse diferente na plataforma. **Dados pessoais dos trabalhadores
e dependentes** (endereço, dependentes, escolaridade, raça/cor, deficiência, CID, ASO,
afastamentos) só servem à folha, e parte deles é dado pessoal sensível (origem racial e dado
referente à saúde). A LGPD manda limitar o tratamento ao mínimo necessário à finalidade e
proteger os dados; cada cópia num banco a mais é mais um lugar a proteger e a responder a um
pedido do titular. **Dados da empresa e do quadro societário** (CNPJ, razão social, regime
tributário, estabelecimentos, sócios e administradores) interessam a todos os módulos.

Em 12/11/2026 o Marcello deu a direção para o cadastro: "um cadastro geral centralizado, e a
folha com uma camada a mais de cadastro, com os dados sensíveis dos funcionários, que ficam
somente lá". O desenho detalhado e a extração ficam para depois.

## Decisão

### Regra comum: histórico por data de vigência

1. **Dado que muda no tempo é guardado em versões por data de vigência, só acrescentadas.**
   Cada alteração cria uma versão com `vigente_desde`; a consulta "como estava em D" pega a
   versão de maior `vigente_desde` ≤ D. Retificação substitui a versão da mesma data guardando
   a referência do que a motivou (na folha, o recibo do eSocial); nada é apagado. O histórico
   serve à auditoria, à conciliação e ao recálculo de períodos passados.

### Dono de cada dado

2. **Dado pessoal fica só no módulo que o usa e não circula nos fatos.**
   - **A folha é a dona exclusiva dos dados pessoais dos trabalhadores e dependentes**,
     inclusive os dados de eSocial dos sócios e diretores (endereço, dependentes, pró-labore,
     S-2300). É a "camada a mais de cadastro" da folha.
   - Os fatos da folha levam informação agregada (por empresa, competência e rubrica) e,
     quando precisarem se referir a um trabalhador, um identificador opaco (o UUID do vínculo),
     nunca o CPF nem outro dado pessoal ([PLAT-0019](PLAT-0019-integracao-por-fatos-e-entregador.md)).
   - **Mesma regra em todo módulo:** dado pessoal que só um módulo usa fica nele (por exemplo,
     o CPF do destinatário de uma nota fiscal fica no `fiscal.aspirador`).
3. **Cadastro geral centralizado: empresa e quadro societário.** Um módulo de cadastro é o dono
   de empresa (CNPJ, razão social, regime tributário e anexos do Simples), estabelecimentos
   (CNPJ completo, CNAE) e sócios e administradores, só com o mínimo de interesse comum (CPF,
   nome, qualificação, participação, entrada e saída). Publica fatos (por exemplo,
   `cadastro.empresa_alterada`, `cadastro.estabelecimento_incluido`,
   `cadastro.socio_incluido`); cada módulo guarda cópia local só do que usa, atrás de um port
   definido na aplicação dele, com os tipos de que ele precisa.
4. **Conceitos só do eSocial ficam na folha:** a lotação (Tabela 10, FPAS, terceiros); o código
   de classificação tributária da Tabela 08 é derivado do regime e do anexo que o cadastro
   publica, ou guardado pela folha.
5. **Identificadores:** chaves naturais quando existirem (CNPJ, CPF) mais um identificador
   interno (UUID). Entre módulos, guarda-se o identificador interno e, quando fizer sentido, a
   chave natural; nunca chave estrangeira entre bancos.

### Situação até a etapa do cadastro

6. **A folha não muda durante o MVP dela.** O cadastro continua dentro do `blatt`, em
   `blatt.cadastro`, no schema `cadastro` do banco da folha, com as salvaguardas da PLAT-0005:
   pacote próprio, acesso da folha só por um port definido em `blatt.folha.aplicacao` (o
   adaptador-ponte `cadastro_local.py` é o único ponto que importa `blatt.cadastro`), sem chave
   estrangeira entre os schemas. Hoje `cadastro.pessoa` e `cadastro.pessoa_versao` guardam os
   dados pessoais (PLAT-0010, item 1) e a carga da folha grava pessoa e vínculo na mesma
   transação; isso fica assim até a etapa do cadastro ([PLAT-0017](PLAT-0017-persistencia-postgresql.md),
   item 9).
7. **Módulos novos** guardam cópia local só da empresa e do quadro societário, atrás de um port
   próprio, alimentada hoje pelo próprio módulo e, depois da etapa do cadastro, por fatos do
   cadastro, sem mudar o domínio. Nenhum dado de trabalhador.
8. **Etapa do cadastro** (desenho detalhado pendente; depois do MVP da folha): `pessoa`,
   `pessoa_versao` e a lotação passam para o banco da folha, e a carga volta a ser atômica
   dentro dela; o cadastro geral vira módulo com banco próprio, publica fatos e é extraído do
   `blatt` (repositório a decidir); a carga da folha deixa de gravar empresa e estabelecimento
   e passa a conferir o S-1000 e o S-1005 baixados contra a cópia local, apontando
   divergências. Quem mantém os dados da empresa é o cadastro (pelo escritório ou por consulta
   à Receita).

## Alternativas consideradas

- **Dados pessoais no cadastro** (PLAT-0010, item 1, e PLAT-0005). Mantinha um só registro de
  pessoas, mas expõe dado sensível a um módulo que os outros vão ler. Substituída pela
  PLAT-0014, item 9, e mantida descartada.
- **Cadastro como registro único de pessoas da plataforma**, alimentado por fatos da folha, ou
  dono dos dados pessoais com a folha pedindo a gravação a ele (sequência com compensação,
  *saga*). Descartadas: os outros módulos não precisam desses dados, parte deles é sensível, e
  cada cópia a mais aumenta a exposição; a segunda ainda tornaria a carga dependente do
  cadastro estar no ar.
- **Extrair o cadastro já**, porque o aspirador é um segundo consumidor. Exigiria mexer na
  carga da folha no meio do MVP dela; a cópia local atrás de um port dá ao aspirador o que ele
  precisa sem isso.
- **Cada módulo com seu cadastro de empresas, sem cadastro geral.** Dispensa um módulo, mas
  cada um mantém à mão os mesmos dados; contraria a direção de 12/11/2026.

## Consequências

- Os dados dos trabalhadores, inclusive os sensíveis, terão um só dono e um só banco; os fatos
  que circulam não os carregam.
- Integridade entre módulos (empresa no cadastro, vínculo na folha) fica na aplicação.
- A etapa do cadastro exige desenho próprio: entidades e vigências do cadastro geral (hoje há
  uma só validade por empresa, estabelecimento e lotação: P-27 da folha), fatos publicados,
  extração do pacote e migração dos dados da folha. Fica como pendência.
- A parte da PLAT-0010 que é só da folha vira FOLHA-0016 no `blatt` (pendência e PR lá); até
  lá, a PLAT-0010 continua sendo a referência para o modelo de vínculo.
- Dados pessoais ficam no banco do escritório: LGPD, cópia de segurança e controle de acesso
  são requisitos da instalação ([PLAT-0020](PLAT-0020-infraestrutura-e-implantacao.md) e
  [PLAT-0022](PLAT-0022-backup-arquivo-imutavel-e-dossies.md)).

## Referências

- [PLAT-0005](PLAT-0005-cadastro-interno-extraivel.md),
  [PLAT-0010](PLAT-0010-vinculos-e-dados-pessoais.md) e
  [PLAT-0014](PLAT-0014-banco-por-modulo-e-orquestrador.md), item 9 (substituídas nestes
  pontos).
- Lei 13.709/2018 (LGPD), arts. 5º, II (dado pessoal sensível), 6º, III (necessidade) e 46
  (segurança): https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm (citados
  de memória, como na PLAT-0014; o site não respondeu na sessão de 12/11/2026; a conferir).
- MOS S-1.3, orientações do S-2205 (dados cadastrais do trabalhador), citado na PLAT-0010:
  https://www.gov.br/esocial/pt-br/documentacao-tecnica/manuais/mos-s-1-3-consolidada-ate-a-no-s-1-3-12-2026.pdf
  (não aberto nesta sessão).
- Folha: `src/blatt/folha/adaptadores/cadastro_local.py` (adaptador-ponte),
  https://github.com/marcellohalfeld/blatt/blob/main/src/blatt/folha/adaptadores/cadastro_local.py
