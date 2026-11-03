# PLAT-0003: Contrato dos parâmetros externos

> Transferida de `marcellohalfeld/blatt` (`docs/adr/0003-contrato-dos-parametros-externos.md`, commit `2bcff8e`) em 2026-11-03, pela [PLAT-0015](PLAT-0015-governanca-no-assembleia.md). Texto sem alteração, salvo o título e os links, que passaram a apontar para cá ou para o repositório da folha. Nas referências do texto, "ADR NNNN" é o número de origem: ver a tabela de correspondência no [README](README.md).

- **Status:** Proposta
- **Data:** 2026-10-20 (revisada em 2026-10-21; ver Histórico)
- **Decisor:** Marcello

## Contexto

Tabelas e parâmetros legais (faixas e alíquotas do INSS, tabela do IRRF, desconto
simplificado, redutor da Lei 15.270/2025, salário mínimo, salário-família) mudam por ato
normativo, às vezes mais de uma vez por ano. A premissa é que **nada disso fica no código**:
uma rotina separada, fora do Blatt, mantém esses arquivos atualizados.

Isso transforma o formato dos arquivos numa interface entre dois sistemas. Uma tabela errada
calcula folha errada com aparência de certa; o contrato precisa impedir isso.

## Decisão

1. **Formato:** JSON, validado por JSON Schema (draft 2020-12). Um schema por tipo de tabela,
   em `parametros/schemas/`; os dados em `parametros/tabelas/<tipo>/`.
2. **Valores numéricos como texto decimal** (`"7.5"`, `"1621.00"`), nunca número JSON. Isso
   elimina qualquer passagem por `float`, inclusive na rotina de atualização, que pode ser
   escrita em outra linguagem. O schema valida o padrão.
3. **Cada registro carrega:**
   - identificador do tipo e versão do schema;
   - `chave_vigencia`: o que a vigência mede — `competencia` ou `mes_pagamento` (item 6);
   - `vigencia_inicio` e `vigencia_fim` (ou nulo), em `AAAA-MM`, na chave declarada. A
     vigência é a **real**, do ato normativo, e não a primeira competência atendida pelo
     Blatt: recálculos de períodos anteriores precisam achar a tabela da época;
   - `base_legal` (ato normativo: tipo, número, data, dispositivo, link oficial e quais
     valores do registro ele fundamenta);
   - `fonte` de onde o valor foi obtido e data da coleta;
   - `conferencia`: se os valores já foram conferidos contra o ato, por quem e quando;
   - os valores.
4. **Integridade:** um manifesto por diretório lista cada arquivo com seu hash SHA-256. O
   carregador recusa arquivo ausente do manifesto ou com hash divergente.
5. **Validação na carga:** schema, sobreposição de vigências do mesmo tipo e lacunas entre
   vigências são verificados quando os parâmetros são carregados. Tabela inválida nunca entra
   em uso; o sistema falha com mensagem clara em vez de calcular. Registro com conferência
   **pendente** também é recusado, exceto quando o carregador é usado pelos testes.
6. **Resolução pelo período de referência de cada tributo:** o cálculo pede "tabela X
   vigente no mês AAAA-MM", e o mês depende da chave de vigência do tipo. Nunca usa a data
   corrente.
   - **Competência** (mês a que a remuneração se refere): INSS, FGTS, salário-família,
     salário mínimo.
   - **Mês do pagamento ou crédito** (regime de caixa): tabelas do IRRF (`irrf_*`). O imposto
     da pessoa física é devido mensalmente, à medida que os rendimentos são percebidos
     (Lei 7.713/1988, art. 2º). Consequência: a folha de dezembro paga em janeiro usa a
     tabela, as deduções e o redutor vigentes em janeiro.
   - Uma mesma folha pode, portanto, resolver INSS por uma competência e IRRF por outro mês.
     Quem chama o cálculo informa as duas datas; o domínio não deduz uma da outra.
7. **Portão dos casos-ouro:** uma tabela nova só é aceita depois que a suíte de casos-ouro roda
   com ela. Casos de competências anteriores devem continuar dando o mesmo resultado.
8. **Fronteira parâmetro × regra (MVP):** números vão para arquivo; **fórmulas ficam em código
   Python revisado**. Fórmulas em arquivo exigiriam um avaliador de expressões restrito (nunca
   `eval`), o que adiciona superfície de erro sem ganho no MVP. Revisitar na Etapa 3, quando o
   catálogo de rubricas tornar a questão concreta.

O formato detalhado de cada tabela é definido na Etapa 1, em `docs/contratos/parametros.md`.

## Alternativas consideradas

- **Resolver tudo pela competência** (redação original do item 6): mais simples, mas calcula
  IRRF errado sempre que competência e pagamento caem em meses com tabelas diferentes, como
  na virada 2025→2026 (redutor da Lei 15.270/2025 vale para pagamentos desde janeiro/2026).
- **Vigência a partir da primeira competência do Blatt** (proposta da Etapa 1a): evitava
  pesquisar datas antigas, mas impediria recálculo de períodos anteriores.

- **YAML:** mais legível, mas tem tipagem implícita ambígua (o mesmo valor pode ser lido como
  número, texto ou data dependendo da forma) e exige biblioteca externa para ler.
- **TOML:** bom para configuração, fraco para listas de faixas e sem padrão de schema tão
  difundido quanto o JSON Schema.
- **Tabelas no banco de dados:** acopla a rotina de atualização ao banco do Blatt e dificulta
  versionar e auditar as mudanças; arquivos versionados em Git dão histórico de graça.

## Consequências

- Cada valor legal passa a ser rastreável até o ato normativo, o que serve também como
  documentação para auditoria.
- A rotina de atualização pode ser outro sistema, em outra linguagem, desde que respeite o
  schema. No futuro, `parametros/` pode virar repositório próprio.
- Exige disciplina: toda mudança de tabela passa por validação e casos-ouro antes de valer.
- Recalcular um período exige que exista registro vigente para ele; sem registro, o
  carregador falha em vez de usar a tabela atual. Registros de anos anteriores entram
  conforme a necessidade de recálculo.
- A interface de cálculo recebe competência **e** data de pagamento.

## Histórico

- 2026-10-20: proposta inicial.
- 2026-10-21: decisões do Marcello na revisão da Etapa 1a — vigência real dos atos (item 3);
  IRRF resolvido pelo mês de pagamento (item 6); recusa de registro pendente (item 5).
  Alteração feita no próprio texto porque a ADR ainda estava como "Proposta"; depois de
  aceita, mudanças exigem nova ADR.

## Referências

- [JSON Schema — especificação 2020-12](https://json-schema.org/draft/2020-12)
- Lei 15.270/2025 (redutor do IRRF); Portaria Interministerial MPS/MF 13/2026 (INSS 2026)
- [Lei 7.713/1988, art. 2º](https://www.planalto.gov.br/ccivil_03/leis/L7713compilada.htm)
  (IRPF devido mensalmente, à medida que os rendimentos são percebidos)
