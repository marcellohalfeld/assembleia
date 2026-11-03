# Pendências da plataforma

Pontos que dependem de decisão, revisão ou insumo do Marcello e valem para mais de um módulo.
Cada um com proposta (quando houver) e o que bloqueia. Decidido, sai dos abertos e vai para
"Resolvidos", com o lugar onde a decisão ficou registrada. Pendências de um módulo só ficam no
repositório dele.

## Abertas

### A-01. Aceitar a PLAT-0015 (governança no `assembleia`)

- **Proposta:** [PLAT-0015](adr/PLAT-0015-governanca-no-assembleia.md).
- **Bloqueia:** nada no código; enquanto estiver Proposta, a organização feita em 03/11/2026
  (transferência das ADRs, prefixos, fim das cópias) vale como provisória.

### A-02. Confirmar a classificação das ADRs transferidas

- **Proposta:** plataforma = 0001, 0002, 0003, 0004, 0005, 0006, 0008, 0009, 0010, 0014;
  folha = 0007, 0011, 0012, 0013 (critério: o que a seção 2 do resumo já tratava como comum).
- **Ponto de dúvida:** a PLAT-0010 tem uma regra comum (histórico por data de vigência, só
  acrescentado) e uma parte só da folha (vínculo, contrato). A 0011, que a complementa, ficou na
  folha.
- **Bloqueia:** nada; só a clareza de onde propor uma mudança nessas regras.

### A-03. Distribuição do `blatt.comum`

- **Hoje:** cópia nos módulos, conferida contra `comum/MANIFESTO.json` por
  `scripts/conferir_comum.py`.
- **Opções:**
  1. pacote instalado por tag do git (`uv add "blatt-comum @ git+https://github.com/marcellohalfeld/assembleia@vX#subdirectory=comum"`).
     Exige credencial para repositório privado no CI e nas sessões, e um ajuste de empacotamento:
     os módulos têm `src/blatt/__init__.py`, o que impede `blatt.comum` de vir de outro pacote;
     `blatt` teria de virar *namespace package* nos módulos;
  2. continuar com a cópia, com a conferência rodando no CI de cada módulo (o script só usa a
     biblioteca padrão e precisa do `assembleia` disponível no CI);
  3. resolver junto com a decisão de monorepo, se ela vier.
- **Proposta:** 2 agora; 1 quando o terceiro módulo usar o comum.
- **Bloqueia:** nada; o risco é divergência silenciosa enquanto o CI não conferir.

### A-04. Antecipar o orquestrador (fase 2 da PLAT-0014)

- **Contexto:** a PLAT-0014 (item 11) põe "implantar o orquestrador" na fase 2, depois do MVP
  da folha. Em 03/11/2026 o Marcello decidiu começar o orquestrador (`marcellohalfeld/oper`).
  Hoje só o aspirador publica fatos; a folha não tem `outbox`.
- **Proposta:** ADR `PLAT-0016` antecipando a implantação do orquestrador, limitada na largada a
  ler a `outbox` do aspirador, registrar e entregar a um consumidor de teste; a folha continua
  fora até a fase 2, como a PLAT-0014 prevê. As decisões só do orquestrador (linguagem do
  processo, agendamento, tabelas do banco `orquestrador`) ficam como `OPER-`.
- **Bloqueia:** o início do código no `oper`.

### A-05. Decisões de plataforma que estão numa ADR do aspirador

- **Contexto:** a ASP-0006 (escopo de captura, aceita em 03/11/2026) cria um módulo novo
  (`fiscal.escrituracao`) e registra o foco do primeiro MVP **da plataforma** (Simples
  Nacional: folha, registro do faturamento e escrituração contábil básica). As duas coisas valem
  além do aspirador.
- **Proposta:** registrar o mapa de módulos e o escopo do MVP da plataforma numa ADR `PLAT-`,
  citando a ASP-0006 como origem; a ASP-0006 continua valendo para o escopo do aspirador.
- **Bloqueia:** nada imediato; evita que o próximo módulo (`fiscal.escrituracao`) nasça sem
  referência na plataforma.

### A-06. Status das ADRs de plataforma ainda propostas

- PLAT-0001, 0002, 0003, 0004, 0005, 0006, 0009 e 0014 continuam **Proposta**, embora o código
  dos dois módulos já as siga. Vale revisar quais podem ser aceitas, a começar pela PLAT-0014,
  de que dependem o aspirador (ASP-0005) e o orquestrador.

### A-07. `blatt.infra` também é copiado, e as cópias já divergem

- **Contexto:** além do `comum`, o aspirador copiou `src/blatt/infra/` da folha (commit
  `660979f`) e acrescentou duas extensões compatíveis: migrações por pacote
  (`postgres/migracoes.py`) e `dsn_modulo()` (`configuracao.py`). Em 03/11/2026, esses dois
  arquivos diferem entre os repositórios; os demais são iguais. O aspirador registra isso como a
  pendência P-20 dele.
- **Por que é de plataforma:** o executor de migrações e a leitura de configuração por módulo
  (PLAT-0014, itens 2 e 11) vão ser usados também pelo orquestrador, que tem banco próprio.
- **Proposta:** tratar como o `comum`: fonte canônica aqui (a versão estendida do aspirador,
  depois de conferida contra os testes da folha), manifesto e conferência; folha e aspirador
  passam a copiar daqui.
- **Bloqueia:** o banco do orquestrador, se ele for reaproveitar o executor de migrações.

## Resolvidas

Nenhuma ainda.
