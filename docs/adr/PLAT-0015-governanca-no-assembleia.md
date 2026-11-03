# PLAT-0015: Decisões de plataforma num repositório próprio, o `assembleia`

- **Status:** Proposta
- **Data:** 2026-11-03
- **Origem:** sessão de 03/11/2026, a pedido do Marcello ("criei o repositório assembleia, que
  vai ser responsável pela governança da plataforma"). Altera a forma de registro das ADRs
  0001 a 0006, 0008, 0009, 0010 e 0014 da folha, sem alterar o conteúdo de nenhuma.

## Contexto

As decisões que valem para todos os módulos nasceram no repositório da folha
(`marcellohalfeld/blatt`), que era o único. Com o segundo módulo (`fiscal.aspirador`, noutro
repositório) e o orquestrador a caminho (`marcellohalfeld/oper`), apareceram quatro problemas,
conferidos em 03/11/2026:

1. **A plataforma morava dentro de um módulo.** O aspirador copiava à mão o `PLATAFORMA.md`, a
   ADR 0014 e o `blatt.comum`. As cópias estavam iguais, mas o próprio resumo mandava "copiar
   sem alterar": cada módulo novo multiplica as cópias e as chances de divergência.
2. **Números de ADR em colisão.** O blatt tem ADRs 0001 a 0014 e o aspirador, 0001 a 0006:
   "ADR 0005" designava duas decisões diferentes.
3. **Decisão de plataforma redigida num módulo e guardada noutro.** A ADR 0014 foi escrita no
   aspirador e mora no blatt, e altera outras quatro ADRs.
4. **Sem dono para a próxima decisão comum.** O orquestrador vai exigir decisões que valem para
   todos (contrato do envelope, inscrições, antecipação da fase 2); nenhum dos repositórios
   existentes é o lugar natural delas.

Foi considerado guardar a governança no repositório do orquestrador. A PLAT-0014
(Consequências) prevê que o orquestrador possa ser trocado por uma fila com tópicos e
assinaturas, sem mudança nos módulos, desde que não acumule regra de negócio. Se as decisões
morassem nele, essa troca deixaria de ser só de infraestrutura, e a proximidade entre "o que é
comum" e o código do orquestrador incentivaria pôr lógica comum nele.

## Decisão

1. **O repositório `marcellohalfeld/assembleia` é o dono das decisões de plataforma.** Guarda:
   - as ADRs de plataforma, em `docs/adr/`, com o prefixo `PLAT-`;
   - o resumo `docs/PLATAFORMA.md`;
   - o índice dos contratos de eventos (`docs/contratos/README.md`), que aponta para os schemas
     nos repositórios de quem publica (os schemas continuam com quem publica, PLAT-0014, item 7);
   - a fonte canônica do `blatt.comum` (`comum/`), com manifesto SHA-256;
   - as pendências da plataforma (`docs/PENDENCIAS.md`).
   Não tem código de módulo nem do orquestrador.
2. **Prefixos de ADR.** `PLAT-` (assembleia), `FOLHA-` (blatt), `ASP-` (aspirador), `OPER-`
   (orquestrador). Os números já usados não mudam: as ADRs de plataforma vindas da folha
   mantêm o número de origem (a ADR 0014 da folha é a PLAT-0014), e as próximas `PLAT-`
   continuam a partir da 0015. Nos módulos, os nomes de arquivo não mudam (para não quebrar
   links nem gerar conflito com o trabalho em curso); o prefixo vale nos índices e nas citações
   novas. "ADR NNNN" sem prefixo em texto anterior a esta ADR é o número de origem no
   repositório onde foi escrito (tabela em `docs/adr/README.md`).
3. **Transferência das ADRs da folha.** Vão para cá, como `PLAT-`, as ADRs que o resumo da
   plataforma já tratava como comuns: 0001, 0002, 0003, 0004, 0005, 0006, 0008, 0009, 0010 e
   0014. Ficam na folha, como `FOLHA-`: 0007, 0011, 0012 e 0013. O texto é transferido sem
   alteração de conteúdo nem de status; só o título e os links mudam. No blatt, cada arquivo
   transferido fica como um aviso com o endereço novo, para que os links antigos continuem
   válidos; o texto anterior permanece no histórico do git.
4. **Nada de cópia de decisão nos módulos.** Os módulos apontam para o `assembleia` no
   `CLAUDE.md` (trecho da seção 14 do resumo) e não guardam cópias do resumo nem de ADRs
   `PLAT-`. A única cópia admitida é a do `blatt.comum`, enquanto não houver distribuição como
   pacote, conferida por `scripts/conferir_comum.py` contra o manifesto.
5. **Como uma decisão de plataforma nasce.** A sessão de um módulo que precisar mudar uma regra
   `PLAT-` registra o ponto nas pendências do módulo e abre a proposta aqui (ADR `PLAT-` em
   status Proposta, num PR deste repositório). Divergência que vale só para um módulo é ADR do
   módulo, citando a regra `PLAT-` que altera. Como nas ADRs da folha, só o Marcello muda o
   status para Aceita.
6. **O orquestrador (`oper`) é um módulo como os outros** quanto à governança: suas ADRs são
   `OPER-` e tratam só do que é dele; não guarda decisões de plataforma.

## Alternativas consideradas

- **Governança no repositório do orquestrador.** Um repositório a menos. Descartada pelos
  motivos do Contexto: acopla as decisões a um componente que a PLAT-0014 quer substituível e
  aproxima a lógica comum do lugar onde ela não pode estar.
- **Monorepo (todos os módulos, o comum e o orquestrador num repositório só).** Elimina as
  cópias de vez e deixa uma sessão ver tudo. Não conflita com a PLAT-0014, que trata de
  isolamento de banco, não de repositório. Descartada por ora pelo custo de migrar dois
  repositórios em desenvolvimento ativo; pode ser revista quando houver mais de três módulos.
- **Manter as ADRs de plataforma na folha e só prefixar.** Resolve a colisão de números, mas
  não os problemas 1, 3 e 4.
- **Renumerar as ADRs de plataforma a partir de PLAT-0001.** Dá uma sequência sem lacunas, mas
  obriga a traduzir cada citação existente nos módulos. Manter o número de origem com o prefixo
  deixa as citações antigas legíveis sem tabela.

## Consequências

- Uma decisão comum tem um só lugar; os módulos deixam de copiar o resumo e as ADRs.
- A sessão que trabalha numa decisão de plataforma precisa ter o `assembleia` e os módulos
  afetados anexados. Não é preciso uma sessão própria para a governança: a sessão do
  orquestrador, por exemplo, pode ler os módulos e escrever aqui.
- A numeração `PLAT-` tem lacunas (0007, 0011, 0012 e 0013 ficaram na folha). É aceitável: a
  regra é nunca reaproveitar número.
- A cópia do `blatt.comum` continua até haver pacote (pendência A-03); o manifesto torna a
  divergência detectável, mas não impossível. O ideal é que o CI de cada módulo rode a
  conferência.
- O `CLAUDE.md` da folha deixa de mandar "manter o `PLATAFORMA.md` atualizado"; essa
  obrigação passa para quem altera uma ADR `PLAT-`.

## Referências

- PLAT-0014, item 7 (contratos com quem publica) e Consequências (troca do orquestrador por
  fila): [PLAT-0014](PLAT-0014-banco-por-modulo-e-orquestrador.md).
- PLAT-0005, precedente de "junto agora, desenhado para separar":
  [PLAT-0005](PLAT-0005-cadastro-interno-extraivel.md).
- Formato das ADRs: Michael Nygard, *Documenting Architecture Decisions* (2011),
  https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions.
