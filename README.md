# Assembleia

Regras da plataforma Blatt: as decisões que valem para todos os módulos, o resumo delas, o
índice de contratos e as pendências. Pela
[PLAT-0016](docs/adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md) (aceita em
12/11/2026), guarda também o pacote `blatt-plataforma`, com o código comum sem regra de
negócio. Não tem código de módulo nem de operação.

## Repositórios da plataforma

Papéis conforme a PLAT-0016 (aceita em 12/11/2026; substitui a
[PLAT-0015](docs/adr/PLAT-0015-governanca-no-assembleia.md)). O que o `oper` fará pela
integração, pelo portal e pelo backup depende das PLAT-0019, 0021 e 0022, ainda propostas; até o
aceite da PLAT-0019, a integração continua a da PLAT-0014.

| Repositório | Papel | ADRs |
| --- | --- | --- |
| [assembleia](https://github.com/marcellohalfeld/assembleia) | Regras: ADRs de plataforma, resumo, índice de contratos, pendências; pacote `blatt-plataforma` (`blatt.comum`, `blatt.infra`, utilitários de fatos, base da interface web) | `PLAT-` |
| [oper](https://github.com/marcellohalfeld/oper) | Operação da instância: Docker Compose, provisionamento dos bancos, entregador de fatos, backup, agendamentos, portal web; sem regra de negócio | `OPER-` |
| [blatt](https://github.com/marcellohalfeld/blatt) | Folha de pagamento + eSocial (e o cadastro, até a etapa do cadastro) | `FOLHA-` |
| [aspirador](https://github.com/marcellohalfeld/aspirador) | `fiscal.aspirador`: captura de documentos fiscais eletrônicos | `ASP-` |
| a criar | `fiscal.escrituracao` (tratamento fiscal) e contábil | a definir |

## Onde está cada coisa

- [`docs/PLATAFORMA.md`](docs/PLATAFORMA.md): resumo das regras comuns e do que um módulo
  precisa respeitar. É o ponto de entrada para qualquer sessão de qualquer módulo.
- [`docs/adr/`](docs/adr/README.md): ADRs `PLAT-`, o conjunto vigente e a tabela de
  correspondência com os números antigos.
- [`docs/contratos/README.md`](docs/contratos/README.md): índice dos fatos publicados por cada
  módulo (os schemas ficam com quem publica).
- [`docs/PENDENCIAS.md`](docs/PENDENCIAS.md): pontos da plataforma que dependem do Marcello.
- [`docs/ambiente-das-sessoes.md`](docs/ambiente-das-sessoes.md): notas práticas para as
  sessões do Claude Code.
- [`src/blatt/`](src/blatt/README.md): o pacote `blatt-plataforma` (hoje `blatt.comum` e
  `blatt.infra`), com `pyproject.toml` na raiz e testes em `tests/`. O README do pacote explica
  como um módulo o instala (`uv add "blatt-plataforma @ git+https://github.com/marcellohalfeld/assembleia@vX.Y.Z"`)
  e como se publica uma versão nova.
