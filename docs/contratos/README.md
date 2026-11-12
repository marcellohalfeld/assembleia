# Índice dos contratos de eventos

O schema de cada fato é mantido **por quem o publica**, no repositório dele, em
`contratos/eventos/<tipo>/<versao>.schema.json` (PLAT-0014, item 7; na proposta
[PLAT-0019](../adr/PLAT-0019-integracao-por-fatos-e-entregador.md), item 4, sem mudança). Este
índice só lista o que existe e onde, para que um consumidor encontre o contrato sem procurar em
cada repositório. Quem publica um tipo novo ou uma versão nova atualiza esta tabela no mesmo
momento.

Envelope comum: `id` (UUID), `tipo`, `versao`, `tenant_id`, `origem`, `instante`,
`correlacao`, `causa` (opcional) e `conteudo`. Dinheiro como texto decimal; datas e
competências como texto. Nenhum dado pessoal de trabalhador
([PLAT-0018](../adr/PLAT-0018-dono-de-cada-dado-e-cadastro.md)).

## Fatos

| Tipo | Versão | Publicado por | Estado | Contrato |
| --- | --- | --- | --- | --- |
| `fiscal.documento_coletado` | 2 | `fiscal.aspirador` | Implementado (`outbox` do aspirador); NFS-e por ADN ou importação, com `canal` | [aspirador: 2.schema.json](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/contratos/eventos/fiscal.documento_coletado/2.schema.json) |
| `fiscal.documento_coletado` | 1 | `fiscal.aspirador` | Não é mais emitida (publicada até 03/11/2026, só ADN); pode existir na `outbox` | [aspirador: 1.schema.json](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/contratos/eventos/fiscal.documento_coletado/1.schema.json) |
| `fiscal.documento_cancelado` | 1 | `fiscal.aspirador` | Implementado; cancelamento de NFS-e recebido do ADN | [aspirador: 1.schema.json](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/contratos/eventos/fiscal.documento_cancelado/1.schema.json) |
| `fiscal.nfe_coletada` | 1 | `fiscal.aspirador` | Implementado; NF-e completa pela SEFAZ ou por importação (resumos não são publicados) | [aspirador: 1.schema.json](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/contratos/eventos/fiscal.nfe_coletada/1.schema.json) |
| `fiscal.nfe_cancelada` | 1 | `fiscal.aspirador` | Implementado; cancelamento (110111/110112) de NF-e da empresa recebido da SEFAZ | [aspirador: 1.schema.json](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/contratos/eventos/fiscal.nfe_cancelada/1.schema.json) |
| `fiscal.nfe_manifestada` | 1 | `fiscal.aspirador` | Implementado; manifestação do destinatário aceita pela SEFAZ (ASP-0008) | [aspirador: 1.schema.json](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/contratos/eventos/fiscal.nfe_manifestada/1.schema.json) |
| `folha.competencia_calculada` | — | folha | Previsto, sem schema; a `outbox` da folha nasce com o primeiro consumidor | [blatt: eventos-dominio.md](https://github.com/marcellohalfeld/blatt/blob/main/docs/contratos/eventos-dominio.md) |
| `folha.evento_esocial_aceito` | — | folha | Previsto, sem schema | idem |
| `folha.evento_esocial_rejeitado` | — | folha | Previsto, sem schema | idem |
| `folha.competencia_conciliada` | — | folha | Previsto, sem schema | idem |
| `folha.competencia_fechada` | — | folha | Previsto, sem schema | idem |
| `folha.lancamentos_contabeis` | — | folha | Previsto, sem schema | idem |

Descrição de cada fato do aspirador:
[aspirador: contratos/eventos/README.md](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/contratos/eventos/README.md).
O branch padrão do aspirador é `claude/admiring-mendel-vilgsf` (conferido em 12/11/2026; não há
`main`, pendência A-16); os links acima apontam para ele.

## Inscrições

Quem recebe cada tipo é configurado num arquivo versionado no repositório
`marcellohalfeld/oper`, lido pelo entregador
([PLAT-0019](../adr/PLAT-0019-integracao-por-fatos-e-entregador.md), item 8): para cada destino,
as origens e os tipos (e versões) que ele recebe. Quem publica não sabe quem consome.

Em 12/11/2026 ainda não há consumidores; o primeiro previsto é o `fiscal.escrituracao`, com os
fatos `fiscal.*` do aspirador. Enquanto a PLAT-0019 não for aceita, vale a redação da PLAT-0014
(inscrições no orquestrador).
