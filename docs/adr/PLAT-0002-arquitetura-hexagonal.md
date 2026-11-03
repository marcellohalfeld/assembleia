# PLAT-0002: Arquitetura hexagonal

> Transferida de `marcellohalfeld/blatt` (`docs/adr/0002-arquitetura-hexagonal.md`, commit `2bcff8e`) em 2026-11-03, pela [PLAT-0015](PLAT-0015-governanca-no-assembleia.md). Texto sem alteração, salvo o título e os links, que passaram a apontar para cá ou para o repositório da folha. Nas referências do texto, "ADR NNNN" é o número de origem: ver a tabela de correspondência no [README](README.md).

- **Status:** Proposta
- **Data:** 2026-10-20
- **Decisor:** Marcello

## Contexto

Duas exigências do projeto apontam para o mesmo desenho:

- partes devem ser trocáveis "sem que a lógica central se perca" (biblioteca de assinatura,
  cliente SOAP, banco, armazenamento de XML);
- o módulo de folha será um componente de uma plataforma maior, sob um orquestrador.

Além disso, o núcleo (cálculo e regras) é a parte que mais exige testes exaustivos com
casos-ouro, e testes são muito mais simples quando o núcleo não faz I/O.

## Decisão

Adotar arquitetura hexagonal (*ports and adapters*, de Alistair Cockburn), em três camadas
dentro de `src/blatt/folha/`:

| Camada | Conteúdo | Pode importar |
| --- | --- | --- |
| `dominio` | Cálculo, rubricas, regras, montagem lógica dos eventos. Python puro, sem I/O. | Só a biblioteca padrão (sem rede, banco ou processos) |
| `aplicacao` | Casos de uso (ex.: "fechar competência") e *ports*: interfaces `typing.Protocol` para o que o domínio precisa do mundo externo | `dominio` |
| `adaptadores` | Implementações dos ports: XML/XSD, assinatura, SOAP eSocial, PostgreSQL, arquivos de parâmetros, CLI | `aplicacao`, `dominio`, bibliotecas externas |

A regra é verificada no CI pelo `import-linter` (contratos em `pyproject.toml`): o domínio
não importa `aplicacao`, `adaptadores`, nem módulos de rede, banco ou processos.

O pacote raiz é `blatt`, e a folha fica em `blatt.folha`. Módulos futuros (contábil, fiscal,
cadastro compartilhado) entram como `blatt.<modulo>` ou como repositórios próprios; a fronteira
já fica marcada no nome do pacote.

## Alternativas consideradas

- **Camadas tradicionais (controller/service/repository):** mais conhecida, mas o domínio
  tende a depender do ORM e do banco, o que é exatamente o acoplamento que queremos evitar.
- **Microsserviços desde o início:** resolve modularidade à custa de infraestrutura e
  operação desproporcionais a um MVP com um escritório.

## Consequências

- Trocar uma biblioteca (ex.: assinatura) é escrever outro adaptador que satisfaça o mesmo
  Protocol; domínio e casos de uso não mudam.
- Mais arquivos e alguma indireção para quem lê o código pela primeira vez.
- O orquestrador futuro será apenas mais um adaptador de saída (publicação de eventos de
  domínio, ver `docs/contratos/eventos-dominio.md`).

## Referências

- [Alistair Cockburn — Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [import-linter — documentação](https://import-linter.readthedocs.io/)
