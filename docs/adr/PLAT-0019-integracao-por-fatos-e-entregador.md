# PLAT-0019: Integração por fatos — outbox, inbox e um entregador sem banco próprio

> **Atenção: esta proposta altera uma ADR aceita.** Os itens 6 e 8 da
> [PLAT-0014](PLAT-0014-banco-por-modulo-e-orquestrador.md), aceita pelo Marcello em
> 03/11/2026 (P-57 da folha), previam um **orquestrador com banco próprio**, que registra cada
> entrega. Esta ADR troca o orquestrador por um **entregador** sem banco próprio. O resto da
> integração (outbox, inbox, envelope, contratos, dados pessoais fora dos fatos) é mantido sem
> mudança de sentido. Até o Marcello decidir, vale a PLAT-0014.

- **Status:** Proposta
- **Data:** 2026-11-12
- **Decisor:** Marcello
- **Substitui:** os itens 3 a 8, 10 e 11 da [PLAT-0014](PLAT-0014-banco-por-modulo-e-orquestrador.md)
  (as partes de persistência dos itens 10 e 11 estão na
  [PLAT-0017](PLAT-0017-persistencia-postgresql.md); as de cadastro, na
  [PLAT-0018](PLAT-0018-dono-de-cada-dado-e-cadastro.md)).
- **Resolve:** pendência A-04 (antecipar o orquestrador), trocando-o pelo entregador.
- **Origem:** sessão de 12/11/2026 com o Marcello (reorganização da plataforma).

## Contexto

A PLAT-0014 decidiu que os módulos trocam informação só por fatos: cada um publica numa
`outbox` do próprio banco, na mesma transação do dado, e recebe numa `inbox` idempotente. Um
orquestrador com banco próprio leria as `outbox`, entregaria nas `inbox` inscritas e
registraria cada entrega. A implantação dele ficou para a fase 2 (item 11); em 03/11/2026 o
Marcello decidiu começar o `oper` (pendência A-04).

Em 12/11/2026 a plataforma vai para produção limitada: um usuário, um servidor doméstico, poucos
módulos e volume pequeno (PLAT-0016). Conferido nos repositórios nesse dia:

- só o aspirador publica fatos; a `outbox` dele tem uma coluna `sequencia` (identidade
  crescente) além do envelope, e ele concede leitura dela a um papel `blatt_orquestrador`
  (`sql/0001_inicial.sql` e `scripts/sql/provisionar.sql` do aspirador);
- nenhum módulo consome fatos ainda; a folha não tem `outbox`.

Um orquestrador com banco próprio é mais um banco a migrar, a copiar e a restaurar, e o
registro central de entregas que ele manteria duplica o que cada `inbox` já pode registrar. O
objetivo é o mesmo da PLAT-0014: cada módulo pode cair, ser substituído ou reescrito sem
interferir nos outros, e a peça que leva os fatos não tem regra de negócio.

## Decisão

### Mantido da PLAT-0014

1. **Nenhum módulo lê as tabelas de negócio de outro.** Dados de outro módulo chegam:
   - **como regra**, por fatos recebidos na `inbox` e guardados como cópia local, só com os
     campos de que o módulo precisa;
   - **como exceção**, por consulta síncrona a um port cujo adaptador chama a interface do outro
     módulo (nunca o banco dele). A exceção precisa de justificativa registrada (ADR ou regra do
     módulo) e de comportamento definido para quando o outro módulo estiver fora do ar. Hoje
     nenhum módulo tem interface remota para isso; até ter, não há consulta síncrona.
2. **Publicação por `outbox`.** Cada módulo grava os fatos que publica numa tabela `outbox` do
   próprio banco, **na mesma transação** do dado que os origina (*transactional outbox*): não
   existe dado gravado sem o fato correspondente, nem fato sem o dado. A `outbox` tem, além do
   envelope, uma `sequencia` crescente (identidade), que dá a ordem de publicação. Linhas da
   `outbox` não são alteradas nem apagadas por ninguém de fora do módulo.
3. **Recebimento por `inbox`.** Só o módulo que consome fatos tem `inbox`, criada quando ele
   passa a consumir. O consumo é **idempotente**: o identificador do fato é chave única, o
   módulo processa cada fato uma vez e ignora repetições (a entrega é "pelo menos uma vez"). A
   `inbox` guarda o envelope, a origem, a `sequencia` na origem e o instante do recebimento;
   o estado do processamento é do módulo.
4. **Contrato dos fatos:**
   - cada fato está **no passado** (`fiscal.documento_coletado`, nunca "registre o documento");
   - **envelope obrigatório:** `id` (UUID), `tipo`, `versao` (do schema), `tenant_id`, `origem`
     (módulo que publica), `instante`, `correlacao` (o mesmo em todos os fatos de uma operação,
     para rastrear de ponta a ponta), `causa` opcional (o `id` do fato que provocou este) e
     `conteudo`;
   - no conteúdo, dinheiro como texto decimal; datas e competências como texto (`AAAA-MM-DD`,
     `AAAA-MM`);
   - o conteúdo de cada tipo é validado por **JSON Schema versionado, mantido por quem
     publica**, em `contratos/eventos/<tipo>/<versao>.schema.json` no repositório dele, e
     listado no [índice de contratos](../contratos/README.md). Mudança incompatível é versão
     nova, publicada ao lado da antiga até os consumidores migrarem;
   - **sem dado pessoal de trabalhador** (PLAT-0018): informação agregada e, se preciso, um
     identificador opaco;
   - quem publica não sabe quem consome.

### Muda: o entregador no lugar do orquestrador

5. **Um entregador pequeno, no `oper`, sem regra de negócio e sem banco próprio.** Para cada
   inscrição, ele:
   - lê a `outbox` da origem a partir do cursor, em ordem de `sequencia`;
   - insere na `inbox` do destino os fatos dos tipos inscritos, com
     `INSERT … ON CONFLICT (id) DO NOTHING`;
   - avança o cursor **na mesma transação** da inserção, no banco do destino.
   Não transforma, não junta nem filtra conteúdo: só copia o envelope, como veio. Juntar
   informações de vários módulos para produzir uma informação nova é trabalho de um módulo
   (por exemplo, o contábil), nunca do entregador. Esta regra é conferida em toda revisão.
6. **O cursor fica no banco do destino**, uma linha por origem (tabela `entrega_cursor`:
   origem, última `sequencia` entregue, instante). Como cursor e `inbox` mudam na mesma
   transação, uma queda no meio não perde nem duplica fato; e restaurar o banco de um módulo
   restaura junto o ponto até onde ele recebeu.
7. **Não pular fato confirmado fora de ordem.** Uma `sequencia` é reservada quando a linha é
   inserida, não quando a transação confirma; um fato de `sequencia` menor pode ficar visível
   depois de um de `sequencia` maior. O entregador precisa tratar isso (por exemplo, só avançar
   o cursor até a menor transação ainda em curso na origem, ou reler uma janela antes do
   cursor, o que o `ON CONFLICT` torna inócuo). A técnica é decisão `OPER-`, com teste.
8. **Inscrições num arquivo de configuração versionado no `oper`**: para cada destino, as
   origens e os tipos (e versões) que ele recebe. Mudar uma inscrição é commit no `oper`.
   Inscrição nova começa do cursor zero, ou de um ponto declarado na própria inscrição.
9. **Papel de banco restrito** (`blatt_entregador`, um só para a instância):
   - em cada banco de origem: `CONNECT` e `SELECT` só na `outbox`;
   - em cada banco de destino: `CONNECT`, `INSERT` só na `inbox` e `SELECT`, `INSERT` e
     `UPDATE` só na `entrega_cursor`.
   Nenhuma outra tabela de módulo é visível a ele. As concessões ficam nas migrações do módulo
   (quando o papel existe) e no provisionamento do `oper`.
10. **Não existe banco `orquestrador`.** Se um destino estiver fora do ar, o entregador tenta de
    novo depois; nada se perde, porque o cursor não avançou. A ordem de publicação é mantida por
    origem.
11. **Registro das entregas:** cada `inbox` registra o que recebeu e quando; a `outbox` da
    origem registra o que foi publicado. O portal ([PLAT-0021](PLAT-0021-interface-web.md))
    agrega essas tabelas para exibição, por um papel só de leitura nas tabelas de integração
    (`outbox`, `inbox`, `entrega_cursor`), nunca nas de negócio.

### Faseamento

12. **Já:** todo módulo que publica tem `outbox` e contrato; todo módulo que consome tem
    `inbox` e `entrega_cursor`. O aspirador já publica. O entregador entra em uso com o
    primeiro consumidor (provavelmente o `fiscal.escrituracao`).
13. **A `outbox` da folha é criada quando houver consumidor** dos fatos dela (rascunho em
    `docs/contratos/eventos-dominio.md` do `blatt`: `folha.competencia_calculada`,
    `folha.evento_esocial_aceito`, `folha.evento_esocial_rejeitado`,
    `folha.competencia_conciliada`, `folha.competencia_fechada`,
    `folha.lancamentos_contabeis`). A do cadastro, na etapa do cadastro (PLAT-0018).

## Alternativas consideradas

- **Manter o orquestrador da PLAT-0014** (banco próprio, registro central de entregas,
  repetição a partir do registro dele). Dá um lugar único para ver o que foi entregue a quem,
  mas acrescenta um banco a migrar, copiar e restaurar, e esse registro pode divergir do que as
  `inbox` de fato têm depois de uma restauração. Para um usuário e poucos módulos, o ganho não
  paga o custo.
- **Consumidor puxando direto a `outbox` do publicador.** Dispensa o entregador, mas cada
  módulo passaria a conectar no banco de outro, com credencial e endereço dele: o isolamento da
  PLAT-0017 deixaria de ser só um papel restrito numa peça de operação e passaria para dentro
  do código de cada módulo.
- **Fila externa (RabbitMQ, MPL 2.0, como na PLAT-0006).** Resolve entrega, repetição e
  inscrições com uma ferramenta pronta, e é o caminho se o volume crescer ou se a plataforma
  migrar para coreografia. Hoje é um serviço a mais para operar e copiar, sem necessidade de
  volume. A troca continua barata enquanto os itens 2 a 5 forem respeitados.
- **`LISTEN`/`NOTIFY` do PostgreSQL.** Avisa na hora, mas a notificação não é guardada (quem não
  estava escutando perde o aviso) e vale dentro de um banco. Pode servir depois como aviso
  para o entregador acordar, nunca como meio de entrega.
- **Módulos empurrando os fatos** (cada módulo com um processo que envia a sua `outbox`).
  Dispensa o papel de leitura, mas põe um processo a mais em cada módulo.

## Consequências

- **Some o registro central de entregas.** Para saber o que chegou a quem, consulta-se cada
  `inbox` (o portal agrega). É o custo declarado desta proposta.
- Um banco a menos para migrar, copiar e restaurar; o entregador pode ser parado, trocado ou
  reescrito sem migração de dados, porque o estado dele está nos destinos.
- **Sem transação entre módulos:** a consistência é eventual; um fato chega segundos ou horas
  depois. Conferências entre módulos consideram isso, e a `correlacao` permite rastrear o que
  já chegou.
- **Restauração de um módulo:** o destino restaurado volta ao cursor da cópia e recebe de novo
  o que veio depois (idempotente). A origem restaurada pode ter `sequencia` menor que a de um
  cursor já gravado num destino; o procedimento de restauração do `oper` precisa tratar esse
  caso (pendência para a ADR `OPER-` do entregador).
- **No aspirador:** o papel `blatt_orquestrador` passa a ser `blatt_entregador` (migração nova
  e ajuste em `scripts/sql/provisionar.sql`); PR lá, depois do aceite.
- No `oper`: ADRs `OPER-` para o entregador (processo, agendamento, formato do arquivo de
  inscrições, técnica do item 7, restauração).
- **Custo de migrar depois para fila externa ou coreografia:** baixo, se quem publica não
  conhece o consumidor, os fatos forem fatos, os consumidores forem idempotentes e o
  entregador não acumular regra de negócio. A troca é de infraestrutura, sem mudança no código
  dos módulos.

## Referências

- [PLAT-0014](PLAT-0014-banco-por-modulo-e-orquestrador.md), itens 3 a 8, 10 e 11 (substituídos
  por esta, quando aceita).
- Aspirador: `outbox` em
  [sql/0001_inicial.sql](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/src/blatt/fiscal/aspirador/adaptadores/postgres/sql/0001_inicial.sql)
  e papel de leitura em
  [scripts/sql/provisionar.sql](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/scripts/sql/provisionar.sql).
- C. Richardson, padrões *Transactional outbox*, *Polling publisher* e *Idempotent consumer*:
  https://microservices.io/patterns/data/transactional-outbox.html,
  https://microservices.io/patterns/data/polling-publisher.html,
  https://microservices.io/patterns/communication-style/idempotent-consumer.html (citados de
  memória; o site não abriu na sessão de 12/11/2026; a conferir).
- PostgreSQL, `INSERT … ON CONFLICT`: https://www.postgresql.org/docs/current/sql-insert.html;
  `GRANT`: https://www.postgresql.org/docs/current/sql-grant.html; funções de *snapshot*
  (`pg_current_snapshot`, `pg_snapshot_xmin`), para o item 7:
  https://www.postgresql.org/docs/current/functions-info.html; `NOTIFY`:
  https://www.postgresql.org/docs/current/sql-notify.html (citados de memória; o site não abriu
  na sessão de 12/11/2026; a conferir).
