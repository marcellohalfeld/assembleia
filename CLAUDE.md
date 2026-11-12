# Assembleia — instruções para sessões do Claude Code

Repositório das **regras** da plataforma Blatt. Aqui ficam as decisões que valem para todos os
módulos e, pela PLAT-0016, o código comum sem regra de negócio; os módulos ficam nos
repositórios deles (tabela no `README.md`). Comece por `docs/PENDENCIAS.md` e
`docs/adr/README.md`.

> Os papéis abaixo seguem a PLAT-0016, aceita em 12/11/2026 (substitui a PLAT-0015). Os
> utilitários de fatos e a base da interface web só entram no pacote depois do aceite das
> PLAT-0019 e PLAT-0021, ainda propostas.

## O que entra aqui

- ADRs `PLAT-` (decisão que vale para mais de um módulo), no modelo `docs/adr/0000-modelo.md`.
- O resumo `docs/PLATAFORMA.md`, atualizado no mesmo PR que muda uma ADR `PLAT-`.
- O índice de contratos `docs/contratos/README.md` (os schemas ficam com quem publica).
- Pendências da plataforma em `docs/PENDENCIAS.md`.
- O pacote `blatt-plataforma`: `blatt.comum`, `blatt.infra`, utilitários de fatos
  (`outbox`/`inbox`) e a base comum da interface web. Só código sem regra de negócio, usado por
  mais de um módulo, com testes próprios; não importa nenhum módulo. Fica em `src/blatt/`
  (`blatt` sem `__init__.py`, *namespace package*), com `pyproject.toml` na raiz e testes em
  `tests/`; explicação em `src/blatt/README.md`. Hoje (0.1.0) tem só `blatt.comum` e
  `blatt.infra`.

## O que não entra

- Código de módulo de negócio ou de operação (Compose, entregador, portal, backup: são do
  `oper`). Regra de negócio não vai para o pacote comum nem para o `oper`.
- Decisões que valem para um módulo só: ficam no repositório dele, com o prefixo dele.
- Cópias de ADRs de módulos.

## Regras

- Numeração `PLAT-` sequencial, nunca reaproveitada; a próxima está no índice.
- ADR antiga nunca é apagada nem reescrita; ganha status "Substituída por PLAT-NNNN". A nova é
  autocontida.
- **Só o Marcello muda status para Aceita.** Sessões propõem.
- Toda ADR cita as fontes (lei, documentação oficial, ADR anterior) com link; o que não foi
  aberto fica marcado como "a conferir". Interpretação de norma legal é do Marcello: vira
  pendência, com proposta e fontes.
- Mudança no código comum: mudar o pacote por PR e subir a versão no `pyproject.toml`; depois
  do merge, a tag `vX.Y.Z` é marcada em `main` pelo Marcello; cada módulo sobe a versão por PR.
- Antes de cada commit:
  `uv sync && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports && BLATT_EXIGIR_POSTGRES=1 uv run pytest`.
- Uma ADR `PLAT-` que afete um módulo é acompanhada de pendência ou PR no repositório dele.

## Trabalhando com os módulos

Uma decisão de plataforma costuma exigir ler os módulos. A sessão que trabalha aqui deve ter
anexados os repositórios afetados; lê os módulos e escreve aqui. Alterações nos módulos vão
em PR no repositório de cada um.

Commits e PRs em português, com o que mudou, por quê e o que foi conferido.
