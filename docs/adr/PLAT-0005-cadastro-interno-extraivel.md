# PLAT-0005: Cadastro interno, desenhado para extração

> Transferida de `marcellohalfeld/blatt` (`docs/adr/0005-cadastro-interno-extraivel.md`, commit `2bcff8e`; atualizada para `e4352fc`, com o aceite da PLAT-0014 em 03/11/2026, P-57) em 2026-11-03, pela [PLAT-0015](PLAT-0015-governanca-no-assembleia.md). Texto sem alteração, salvo o título e os links, que passaram a apontar para cá ou para o repositório da folha. Nas referências do texto, "ADR NNNN" é o número de origem: ver a tabela de correspondência no [README](README.md).

- **Status:** Substituída pela [PLAT-0018](PLAT-0018-dono-de-cada-dado-e-cadastro.md) (proposta; vale quando a nova for aceita). Antes: Proposta, alterada em parte pela [ADR 0014](PLAT-0014-banco-por-modulo-e-orquestrador.md) (aceita em 03/11/2026) nos itens 1 a 3.
- **Data:** 2026-10-20
- **Decisor:** Marcello

## Contexto

Empresa, estabelecimento e pessoa são dados mestres que os futuros módulos (contábil, fiscal)
também vão usar. O ideal seria um módulo de cadastro autônomo e compartilhado. Mas construí-lo
agora acrescenta um serviço, um contrato de API e sincronização ao MVP, contrariando a
diretriz de escopo enxuto.

## Decisão

1. **MVP:** o cadastro fica dentro do Blatt e é implementado na Etapa 3.
2. **Isolamento desde já**, para permitir o *spin-off* depois sem reescrever a folha:
   - código do cadastro num pacote próprio (`blatt.cadastro`), fora de `blatt.folha`;
   - a folha acessa o cadastro **só** por um port (Protocol) definido em
     `blatt.folha.aplicacao`, nunca importando o pacote de cadastro diretamente no domínio;
   - tabelas do cadastro num schema PostgreSQL próprio (`cadastro`), sem chaves estrangeiras
     vindas do schema da folha — a folha guarda identificadores;
   - identificadores estáveis e naturais quando existirem (CNPJ, CPF), mais um identificador
     interno.
3. **Extração futura:** quando outro módulo precisar do cadastro, o pacote vira serviço ou
   repositório próprio, e a folha troca o adaptador do port (de chamada local para chamada
   remota). Nenhuma regra de cálculo muda.

## Consequências

- O MVP não paga o custo de um serviço separado.
- A ausência de chaves estrangeiras entre schemas transfere para a aplicação a verificação de
  integridade referencial. Contrapartida aceita, e é o que torna a separação barata depois.
- O contrato `import-linter` será ampliado na Etapa 3 para proibir que `blatt.folha.dominio`
  importe `blatt.cadastro`.
