# PLAT-0010: Vínculos e dados pessoais do trabalhador no banco, com histórico por data

> Transferida de `marcellohalfeld/blatt` (`docs/adr/0010-vinculos-e-dados-pessoais.md`, commit `2bcff8e`) em 2026-11-03, pela [PLAT-0015](PLAT-0015-governanca-no-assembleia.md). Texto sem alteração, salvo o título e os links, que passaram a apontar para cá ou para o repositório da folha. Nas referências do texto, "ADR NNNN" é o número de origem: ver a tabela de correspondência no [README](README.md).

- **Status:** Aceita (27/10/2026, P-42); complementada pela
  [ADR 0011](https://github.com/marcellohalfeld/blatt/blob/main/docs/adr/0011-dependentes-por-vinculo.md) (escolha dos dependentes por vínculo)
- **Data:** 2026-10-26
- **Decisor:** Marcello

## Contexto

A Etapa 5 já gera os eventos não periódicos (S-2200, S-2205, S-2206, S-2230, S-2300 e outros)
e a Etapa 6 lê os eventos baixados do eSocial de volta para os mesmos tipos do domínio. Tudo
isso funciona pela linha de comando, com arquivos JSON e sem memória entre execuções (P-32).
A carga inicial (pronto da Etapa 6: "empresa real importada sem redigitação") e a folha mensal
precisam guardar, por trabalhador:

- **dados pessoais**: nome, endereço, escolaridade, dependentes, deficiência, contato. Mudam
  pelo S-2205, "contendo todas as informações cadastrais" (MOS S-1.3, S-2205, item 1.2), e
  valem a partir da data da alteração;
- **vínculo**: matrícula, categoria, data de admissão, cadastramento inicial; e o **contrato**
  (salário, cargo, jornada, duração), que muda pelo S-2206 a partir da data da alteração;
- os **afastamentos** (S-2230) e o **desligamento**, que a folha precisa para calcular.

Hoje `cadastro.pessoa` só tem CPF, nome e nascimento. A ADR 0005 põe pessoa no cadastro
(extraível). O vínculo é da folha: só existe por causa do contrato de trabalho.

Há três pontos a decidir:

1. onde fica cada dado (cadastro × folha);
2. como guardar a evolução no tempo, porque a folha de uma competência passada precisa do
   salário e dos dependentes daquela data (o eSocial aceita alteração extemporânea: MOS S-1.3,
   16.1.6);
3. o formato no banco: colunas para cada campo ou o registro inteiro serializado.

## Decisão

1. **Dados pessoais no cadastro** (`cadastro.pessoa` e uma tabela nova
   `cadastro.pessoa_versao`), porque são da pessoa e não do vínculo (o S-2205 é por CPF, não
   por matrícula). **Vínculo e contrato na folha** (`folha.vinculo`, `folha.contrato_versao`,
   `folha.afastamento`), com a pessoa referida pelo id, sem chave estrangeira entre schemas
   (ADR 0005).
2. **Versões por data de vigência, só acrescentadas.** Cada S-2205 (ou a carga) cria uma
   versão dos dados pessoais com `vigente_desde`; cada S-2206, uma versão do contrato. A
   consulta "como estava em D" pega a versão de maior `vigente_desde` ≤ D. Retificação
   substitui a versão da mesma data, guardando o recibo; nada é apagado (o histórico serve à
   auditoria e à conciliação).
3. **Colunas para o que a folha consulta ou o banco precisa conferir** (CPF, matrícula,
   categoria, datas, salário, unidade do salário, tipo de contrato, término) e **`jsonb` para o
   restante do registro** (endereço, dependentes, horário, aprendiz), no mesmo formato dos
   arquivos JSON de hoje (`escrita_json` / `arquivo_nao_periodicos`), que já têm leitura estrita
   e testes de ida e volta. Dependentes ganham colunas próprias se a folha passar a consultá-los
   por SQL (hoje entram no IRRF pela quantidade).
4. **O recibo do eSocial acompanha cada versão** (`recibo`, `id_evento`), para retificar e
   excluir (S-3000) sem procurar o evento original.

## Alternativas consideradas

- **Tudo em colunas, normalizado.** Mais conferência no banco, mas dezenas de colunas e uma
  migração a cada campo do leiaute que o MVP passar a cobrir; o domínio já confere tudo antes
  de gravar.
- **Tudo em `jsonb`.** Menos migrações, mas a folha perderia consultas simples (quem estava
  ativo na competência, com que salário) e o banco não conferiria nada.
- **Guardar os XMLs dos eventos e reconstruir o estado na leitura** (*event sourcing*). Fiel
  ao eSocial, mas toda consulta da folha passaria a reprocessar eventos; e a carga inicial tem
  dados que não vêm de evento (planilha, P-41).
- **Dados pessoais na folha**, junto do vínculo. Mais simples hoje, mas contraria a ADR 0005:
  o cadastro de pessoas deixaria de ser extraível.

## Consequências

- A folha passa a ler pessoa e vínculo do banco, pela data da competência; a linha de comando
  pode ganhar memória entre execuções (resolve a P-32 para os não periódicos).
- `jsonb` com formato próprio exige versão do formato nos registros e cuidado nas mudanças;
  os testes de ida e volta (domínio → JSON → domínio) passam a cobrir também o banco.
- Integridade entre `cadastro.pessoa` e `folha.vinculo` fica na aplicação (como já previsto na
  ADR 0005).
- Dados pessoais ficam no banco do escritório: LGPD, cópia de segurança e acesso passam a ser
  requisitos da instalação (ADR 0004 e 0006).

## Implementação (Etapa 6c)

Detalhes que a decisão deixou em aberto, resolvidos na implementação (revisáveis sem nova ADR,
por não mudarem a decisão):

- **Tabelas** (migração `0004_vinculos.sql`): `cadastro.pessoa_versao`, `folha.vinculo`,
  `folha.contrato_versao`, `folha.afastamento`, `folha.vinculo_historico` e
  `folha.evento_aplicado`. A retificação marca a linha anterior com `substituida_em` e grava a
  nova; um índice único parcial garante uma só versão ativa por data.
- **Eventos aplicados:** todo evento aplicado fica em `folha.evento_aplicado`, pelo recibo,
  mesmo o que não mudou nada (S-2205 igual ao vigente). Isso torna a carga repetida inócua e
  restringe a retificação a um evento do mesmo tipo, da mesma pessoa e do mesmo vínculo, ainda
  não retificado.
- **Retificação do S-2200, do S-2300 e do S-2399** atualiza a linha do vínculo; a linha anterior
  vai inteira para `folha.vinculo_historico`.
- **Contrato no dia da admissão:** o S-2206 pode ter `dtAlteracao` igual à admissão ("igual ou
  posterior", leiaute do S-2206); no mesmo dia, a alteração prevalece sobre o contrato inicial
  (coluna `inicial`).
- **Retificação do início de um afastamento** mantém o término registrado por outro S-2230.
- **Versão de dados pessoais só quando os dados mudam:** a mesma pessoa admitida em duas
  empresas do escritório, ou um S-2205 igual ao vigente, não cria versão nova.
- **Formato do `jsonb`:** o dos arquivos JSON do Blatt (`registro_json`), versão 1 em cada linha.
  As colunas repetidas (salário, unidade, tipo e término do contrato; início e motivo do
  afastamento) são conferidas contra o `jsonb` na leitura; divergência é erro.
- **Aplicação** (`blatt.folha.aplicacao.vinculos`) confere o que o banco não confere: matrícula
  e CPF do evento contra o vínculo, data de admissão do evento contra a registrada.
- **Carga** (`blatt-banco importar-eventos`): S-2200, S-2300, S-2205, S-2206, S-2306, S-2230,
  S-2299, S-2399 e S-3000, um evento por transação, na ordem de geração (S-2299 e S-3000 desde
  a Etapa 6d, migração `0005`; S-2306 depois, sem migração nova). S-2231, S-2298 e S-2500 ainda
  não são aplicados e são listados. São lidos o S-1.0 a S-1.3; as versões 2.x, conforme a
  ADR 0012.

## Referências

- MOS S-1.3, orientações do S-2205 (itens 1.2, 1.3 e 1.6) e item 16.1.6 do Capítulo I:
  [MOS consolidado até a NO S-1.3 12.2026](https://www.gov.br/esocial/pt-br/documentacao-tecnica/manuais/mos-s-1-3-consolidada-ate-a-no-s-1-3-12-2026.pdf).
- [PostgreSQL 16, tipos JSON](https://www.postgresql.org/docs/16/datatype-json.html).
- ADR 0004, 0005 e 0009 deste repositório.
