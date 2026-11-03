# Índice dos contratos de eventos

Pela PLAT-0014 (item 7), o schema de cada fato é mantido **por quem o publica**, no repositório
dele, em `contratos/eventos/<tipo>/<versao>.schema.json`. Este índice só lista o que existe e
onde, para que um consumidor (ou o orquestrador) encontre o contrato sem procurar em cada
repositório. Quem publica um tipo novo ou uma versão nova atualiza esta tabela no mesmo
momento.

Envelope comum (PLAT-0014, itens 3 a 7; resumo na seção 9 do `PLATAFORMA.md`): `id` (UUID),
`tipo`, `versao`, `tenant_id`, `origem`, `instante`, `correlacao`, `causa` (opcional) e
`conteudo`. Dinheiro como texto decimal. Nenhum dado pessoal de trabalhador.

| Tipo | Versão | Publicado por | Estado | Contrato |
| --- | --- | --- | --- | --- |
| `fiscal.documento_coletado` | 1 | `fiscal.aspirador` | Implementado (`outbox` do aspirador) | [aspirador: contratos/eventos](https://github.com/marcellohalfeld/aspirador/tree/claude/admiring-mendel-vilgsf/contratos/eventos/fiscal.documento_coletado) |
| `fiscal.documento_cancelado` | 1 | `fiscal.aspirador` | Implementado (`outbox` do aspirador) | [aspirador: contratos/eventos](https://github.com/marcellohalfeld/aspirador/tree/claude/admiring-mendel-vilgsf/contratos/eventos/fiscal.documento_cancelado) |
| `folha.competencia_calculada` | — | folha | Previsto (fase 2), sem schema | [blatt: eventos-dominio.md](https://github.com/marcellohalfeld/blatt/blob/main/docs/contratos/eventos-dominio.md) |
| `folha.evento_esocial_aceito` | — | folha | Previsto (fase 2), sem schema | idem |
| `folha.evento_esocial_rejeitado` | — | folha | Previsto (fase 2), sem schema | idem |
| `folha.competencia_conciliada` | — | folha | Previsto (fase 2), sem schema | idem |
| `folha.competencia_fechada` | — | folha | Previsto (fase 2), sem schema | idem |
| `folha.lancamentos_contabeis` | — | folha | Previsto (fase 2), sem schema | idem |

O branch padrão do aspirador é `claude/admiring-mendel-vilgsf` (conferido em 03/11/2026); os
links acima apontam para ele.

## Inscrições

A lista de quem consome cada tipo fica no orquestrador (PLAT-0014, item 7), no repositório
`marcellohalfeld/oper`. Ainda não há consumidores.
