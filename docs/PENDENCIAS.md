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
  da folha. O aceite de 03/11/2026 (P-57 da folha) foi expresso "com o faseamento dos itens 10
  e 11": antecipar o orquestrador muda uma decisão aceita e, por isso, exige ADR nova, que
  altera o item 11 sem reescrever a PLAT-0014. Em 03/11/2026 o Marcello decidiu começar o
  orquestrador (`marcellohalfeld/oper`). Hoje só o aspirador publica fatos, e ninguém os
  consome: o `fiscal.escrituracao` não existe e a folha não tem `outbox`.
- **Proposta:** etapa C7 do [plano de convergência](PLANO-CONVERGENCIA.md): ADR `PLAT-`
  antecipando o orquestrador, limitado a ler a `outbox` do aspirador, registrar e entregar a um
  consumidor de teste; a folha continua fora até a fase 2. Decisões só do orquestrador
  (agendamento, tabelas do banco `orquestrador`) ficam como `OPER-`. Quando começar é a
  decisão D3 do plano.
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

- PLAT-0001, 0002, 0003, 0004, 0005, 0006 e 0009 continuam **Proposta**, embora o código dos
  dois módulos já as siga. A PLAT-0014 foi aceita em 03/11/2026 (P-57 da folha). Na folha, o
  mesmo ponto está na P-02 (aceitar as ADRs 0001 a 0007 e 0009); como a 0007 ficou na folha
  (FOLHA-0007), a P-02 de lá passa a tratar só dela, e as demais são tratadas aqui.

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

### A-08. Operação: imagens por módulo e Compose por escritório

- **Contexto:** a PLAT-0006 fixa imagens OCI e a PLAT-0004, uma instância por escritório; não
  há decisão sobre como os módulos são montados juntos, nem sobre onde fica essa montagem.
- **Proposta:** etapa C2 do [plano](PLANO-CONVERGENCIA.md): ADR `PLAT-` com imagem por módulo
  (CLI e comando `migrar`), um projeto Docker Compose por escritório num repositório de
  distribuição que fixa a versão de cada módulo, um servidor PostgreSQL com um banco e um
  usuário por módulo (PLAT-0014, item 1), migrações que rodam uma vez antes dos serviços e
  backup por banco. No servidor, Docker Engine ou Podman.
- **Bloqueia:** C4, C6 e C7.

### A-09. APIs dos módulos e interface web

- **Contexto:** os módulos só têm linha de comando. A PLAT-0014 (item 3) diz que nenhum módulo
  tem interface remota e que, até ter, não há consulta síncrona entre módulos.
- **Proposta:** etapas C4 e C5 do [plano](PLANO-CONVERGENCIA.md): ADR `PLAT-` com API HTTP por
  módulo sobre os casos de uso existentes (adaptador de entrada, PLAT-0002), contrato publicado
  pelo módulo e listado no índice daqui, autenticação, e a interface como repositório próprio,
  sem regra de negócio e sem acesso a banco de módulo; a interface pode chamar os módulos, mas um
  módulo continua sem chamar outro.
- **Decisões abertas:** D1 (interface antes do piloto da folha) e D2 (adaptador novo na folha
  durante o MVP dela).
- **Bloqueia:** C5.

### A-10. Contrato do conteúdo normativo e wiki

- **Contexto:** o blatt já guarda as normas de forma estruturada (`parametros/tabelas/`, com
  vigência, base legal e hash; `docs/dominio/regras/`, com regra, interpretação adotada e
  casos-ouro), e o aspirador começou a fazer o mesmo (`regras/receita-bruta-simples.md`). Uma
  wiki escrita à mão seria mais uma cópia que diverge.
- **Proposta:** etapa C3 do [plano](PLANO-CONVERGENCIA.md): ADR `PLAT-` que faz desses formatos
  um contrato de todos os módulos e define a wiki como site gerado na montagem de cada versão da
  plataforma, separando norma (link oficial), parâmetro (valor, vigência, hash) e
  interpretação adotada (quem decidiu, quando, com que fonte); propostas não decididas ficam
  fora. Gerador e manual de uso no repositório da interface.
- **Decisão aberta:** D5 (publicação aberta da parte normativa).
- **Bloqueia:** C3.

### A-11. Criar os repositórios da interface e da distribuição

- **Contexto:** as sessões não criam repositórios (D4 do plano).
- **Proposta:** o Marcello cria os dois, vazios e privados, e informa os nomes; a sessão da
  etapa os anexa.
- **Bloqueia:** C2 (distribuição) e C3 (interface).

## Resolvidas

| Data | Decisão | Registro |
| --- | --- | --- |
| 2026-11-03 | **PLAT-0014 aceita** pelo Marcello ("adr 0014 aceita"), com o faseamento dos itens 10 e 11 e o dono de cada dado do item 9. Decidida no repositório da folha (P-57), no mesmo dia da transferência; o aceite foi trazido para cá depois, com as notas de alteração parcial nas PLAT-0005, 0006, 0009 e 0010. | [PLAT-0014](adr/PLAT-0014-banco-por-modulo-e-orquestrador.md); blatt `e4352fc` (PR #19) |
