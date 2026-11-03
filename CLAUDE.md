# Assembleia — instruções para sessões do Claude Code

Repositório de **governança** da plataforma Blatt (PLAT-0015). Aqui ficam as decisões que valem
para todos os módulos; os módulos ficam nos repositórios deles (tabela no `README.md`).
Comece por `docs/PENDENCIAS.md` e `docs/adr/README.md`.

## O que entra aqui

- ADRs `PLAT-` (decisão que vale para mais de um módulo), no modelo `docs/adr/0000-modelo.md`.
- O resumo `docs/PLATAFORMA.md`, atualizado no mesmo PR que muda uma ADR `PLAT-`.
- O índice de contratos `docs/contratos/README.md` (os schemas ficam com quem publica).
- O `blatt.comum` canônico em `comum/`, com `MANIFESTO.json`.
- Pendências da plataforma em `docs/PENDENCIAS.md`.

## O que não entra

- Código de módulo ou do orquestrador. Lógica comum entre módulos não vai para o orquestrador
  (PLAT-0014, item 8); se for comum de verdade, é candidata ao `comum`, sem regra de negócio.
- Decisões que valem para um módulo só: ficam no repositório dele, com o prefixo dele.
- Cópias de ADRs de módulos.

## Regras

- Numeração `PLAT-` sequencial, nunca reaproveitada; a próxima está no índice.
- ADR antiga nunca é apagada nem reescrita; ganha status "Substituída por PLAT-NNNN".
- **Só o Marcello muda status para Aceita.** Sessões propõem.
- Toda ADR cita as fontes (lei, documentação oficial, ADR anterior) com link.
- Mudança no `comum`: editar aqui, rodar `python scripts/conferir_comum.py --atualizar`,
  registrar a mudança no PR e depois levar aos módulos (cada módulo confere com o script).
- Uma ADR `PLAT-` que afete um módulo é acompanhada de pendência ou PR no repositório dele.

## Trabalhando com os módulos

Uma decisão de plataforma costuma exigir ler os módulos. A sessão que trabalha aqui deve ter
anexados os repositórios afetados; lê os módulos e escreve aqui. Alterações nos módulos vão
em PR no repositório de cada um.

Commits e PRs em português, com o que mudou, por quê e o que foi conferido.
