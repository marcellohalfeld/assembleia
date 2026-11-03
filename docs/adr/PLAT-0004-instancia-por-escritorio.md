# PLAT-0004: Uma instância por escritório, com `tenant_id`

> Transferida de `marcellohalfeld/blatt` (`docs/adr/0004-instancia-por-escritorio.md`, commit `2bcff8e`) em 2026-11-03, pela [PLAT-0015](PLAT-0015-governanca-no-assembleia.md). Texto sem alteração, salvo o título e os links, que passaram a apontar para cá ou para o repositório da folha. Nas referências do texto, "ADR NNNN" é o número de origem: ver a tabela de correspondência no [README](README.md).

- **Status:** Proposta
- **Data:** 2026-10-20
- **Decisor:** Marcello

## Contexto

O MVP atende um escritório contábil. Um SaaS multi-tenant exige isolamento lógico rigoroso
entre clientes (controle de acesso por linha, testes de vazamento, cuidado em cada consulta),
o que é custo alto para um único cliente. Ao mesmo tempo, refazer o modelo de dados depois
para incluir o tenant é caro e arriscado.

O sistema guarda dados pessoais e dados de saúde de empregados (ASO, CAT, afastamentos), que
a LGPD trata como sensíveis (Lei 13.709/2018, art. 5º, II, e art. 11).

## Decisão

1. **MVP:** uma instância isolada por escritório: banco, armazenamento e cofre de
   certificados próprios. A instância pode rodar na nuvem ou no servidor do escritório.
2. **Preparação para escalar:** toda tabela de dados de negócio carrega `tenant_id` desde a
   primeira migração, e toda consulta filtra por ele. Na instância única o valor é constante,
   definido na configuração.
3. A identificação do tenant fica num único ponto (configuração + adaptador de persistência),
   para que a passagem a multi-tenant mude esse ponto, não o código de negócio.

## Consequências

- Isolamento físico simplifica a conversa de LGPD com o escritório (cada um sabe onde estão
  seus dados) e reduz o impacto de qualquer falha.
- Custo operacional cresce linearmente com o número de escritórios até a migração para
  multi-tenant; aceitável enquanto forem poucos.
- A coluna `tenant_id` é um custo pequeno e constante que evita uma migração grande depois.

## Referências

- [Lei 13.709/2018 (LGPD)](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
