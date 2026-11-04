# PLAT-0006: Infraestrutura aberta

> Transferida de `marcellohalfeld/blatt` (`docs/adr/0006-infraestrutura-aberta.md`, commit `2bcff8e`; atualizada para `e4352fc`, com o aceite da PLAT-0014 em 03/11/2026, P-57) em 2026-11-03, pela [PLAT-0015](PLAT-0015-governanca-no-assembleia.md). Texto sem alteração, salvo o título e os links, que passaram a apontar para cá ou para o repositório da folha. Nas referências do texto, "ADR NNNN" é o número de origem: ver a tabela de correspondência no [README](README.md).

- **Status:** Proposta.
  Alterada em parte pela [ADR 0014](PLAT-0014-banco-por-modulo-e-orquestrador.md) (aceita em
  03/11/2026): linha "Fila de trabalho".
- **Data:** 2026-10-20
- **Decisor:** Marcello

## Contexto

Serviços gerenciados de nuvem (KMS, filas, bancos proprietários) são cômodos, mas prendem o
sistema ao provedor tanto quanto uma biblioteca proprietária. O modelo de instância por
escritório (ADR 0004) também pode exigir rodar no servidor do próprio cliente.

## Decisão

| Necessidade | Escolha | Licença | Observação |
| --- | --- | --- | --- |
| Empacotamento | Imagens OCI (containers) | — | Rodam em Docker, Podman ou Kubernetes |
| Banco de dados | PostgreSQL | PostgreSQL License | Inclui tabelas de vigência e histórico |
| Fila de trabalho | Começar com fila no próprio PostgreSQL; RabbitMQ se o volume exigir | RabbitMQ: MPL 2.0 | Decisão final na Etapa 4 |
| Cofre de certificados A1 | OpenBao | MPL 2.0 | Fork do Vault sob a Linux Foundation |
| XMLs e PDFs | Interface compatível com S3, implementação a escolher; sistema de arquivos no MVP | — | Evitar MinIO (AGPLv3 desde 2021) |

Princípio: o Blatt fala com cada componente por um adaptador (ADR 0002). Trocar PostgreSQL
por outro banco ou OpenBao por um KMS de nuvem, se um cliente exigir, é trocar adaptador.

## Consequências

- O sistema roda em qualquer nuvem ou servidor que execute containers, o que também é
  argumento comercial para escritórios que preferem manter os dados consigo.
- Operar OpenBao e PostgreSQL por conta própria exige rotina de backup, atualização e
  monitoramento que um serviço gerenciado faria; o custo é aceito em troca da portabilidade.
- Começar a fila no PostgreSQL evita um componente a mais no MVP.

## Referências

- [PostgreSQL — licença](https://www.postgresql.org/about/licence/)
- [RabbitMQ (Wikipedia) — licença MPL 2.0](https://en.wikipedia.org/wiki/RabbitMQ)
- [The New Stack — OpenBao](https://thenewstack.io/meet-openbao-an-open-source-fork-of-hashicorp-vault/)
- [MinIO — mudança para AGPLv3](https://blog.min.io/from-open-source-to-free-and-open-source-minio-is-now-fully-licensed-under-gnu-agplv3)
