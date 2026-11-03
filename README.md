# Assembleia

Governança da plataforma Blatt: as decisões que valem para todos os módulos, o resumo delas e
o núcleo comum. Não tem código de módulo nem do orquestrador
([PLAT-0015](docs/adr/PLAT-0015-governanca-no-assembleia.md)).

## Repositórios da plataforma

| Repositório | Papel | ADRs |
| --- | --- | --- |
| [assembleia](https://github.com/marcellohalfeld/assembleia) | Decisões de plataforma, resumo, índice de contratos, `blatt.comum` canônico | `PLAT-` |
| [blatt](https://github.com/marcellohalfeld/blatt) | Folha de pagamento + eSocial (e o cadastro, até a fase 2 da PLAT-0014) | `FOLHA-` |
| [aspirador](https://github.com/marcellohalfeld/aspirador) | `fiscal.aspirador`: captura de documentos fiscais eletrônicos | `ASP-` |
| [oper](https://github.com/marcellohalfeld/oper) | Orquestrador: lê `outbox`, roteia, entrega e registra; sem regra de negócio | `OPER-` |

## Onde está cada coisa

- [`docs/PLATAFORMA.md`](docs/PLATAFORMA.md): resumo das decisões comuns e do que um módulo
  precisa respeitar. É o ponto de entrada para qualquer sessão de qualquer módulo.
- [`docs/adr/`](docs/adr/README.md): ADRs `PLAT-` e a tabela de correspondência com os números
  antigos.
- [`docs/contratos/README.md`](docs/contratos/README.md): índice dos fatos publicados por cada
  módulo (os schemas ficam com quem publica).
- [`docs/PENDENCIAS.md`](docs/PENDENCIAS.md): pontos da plataforma que dependem do Marcello.
- [`comum/`](comum/README.md): fonte canônica do `blatt.comum` e o manifesto de hashes.
- [`scripts/conferir_comum.py`](scripts/conferir_comum.py): confere a cópia do comum num
  módulo.
