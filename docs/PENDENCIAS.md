# Pendências da plataforma

Pontos que dependem de decisão, revisão ou insumo do Marcello e valem para mais de um módulo.
Cada um com proposta (quando houver) e o que bloqueia. Decidido, sai dos abertos e vai para
"Resolvidos", com o lugar onde a decisão ficou registrada. Pendências de um módulo só ficam no
repositório dele.

## Abertas

### A-08. Aceitar as PLAT-0016 a PLAT-0022 (reorganização de 12/11/2026)

- **Propostas:** [PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md)
  (repositórios, mapa de módulos, pacote `blatt-plataforma`, governança),
  [PLAT-0017](adr/PLAT-0017-persistencia-postgresql.md) (persistência),
  [PLAT-0018](adr/PLAT-0018-dono-de-cada-dado-e-cadastro.md) (dono de cada dado, cadastro),
  [PLAT-0019](adr/PLAT-0019-integracao-por-fatos-e-entregador.md) (integração por fatos,
  entregador), [PLAT-0020](adr/PLAT-0020-infraestrutura-e-implantacao.md) (infraestrutura e
  implantação), [PLAT-0021](adr/PLAT-0021-interface-web.md) (interface web) e
  [PLAT-0022](adr/PLAT-0022-backup-arquivo-imutavel-e-dossies.md) (backup).
- **Atenção à PLAT-0019:** altera a PLAT-0014, aceita em 03/11/2026, ao trocar o orquestrador
  com banco próprio por um entregador sem banco; o custo declarado é perder o registro central
  de entregas. As PLAT-0017 e 0018 só consolidam o que já estava aceito na PLAT-0014, sem mudar
  o sentido; a 0018 acrescenta a direção do cadastro geral dada em 12/11/2026.
- Podem ser aceitas separadamente. Cada aceite muda a linha de status da nova e confirma a
  substituição registrada nas antigas.
- **Bloqueia:** a etapa 1 (pacote `blatt-plataforma`, PLAT-0016), o código do `oper`
  (entregador, portal, backup) e o adaptador web dos módulos.

### A-06. Status das ADRs de plataforma ainda propostas

- PLAT-0001, 0002, 0003 e 0004 continuam **Proposta**, embora o código dos dois módulos já as
  siga. (As 0005, 0006 e 0009, também propostas, passam a ser substituídas pelas PLAT-0018,
  0020 e 0017; o aceite delas perde o objeto quando as novas forem aceitas.) Na folha, a P-02
  trata só da FOLHA-0007 e da FOLHA-0013.

### A-09. Desenho do cadastro geral e da extração

- **Direção do Marcello (12/11/2026):** "um cadastro geral centralizado, e a folha com uma
  camada a mais de cadastro, com os dados sensíveis dos funcionários, que ficam somente lá"
  (PLAT-0018).
- **Falta decidir:** entidades e vigências do cadastro geral (hoje uma só validade por empresa,
  estabelecimento e lotação, P-27 da folha); fatos publicados; repositório do cadastro;
  quando extrair (depois do MVP da folha, como hoje previsto); como migrar `pessoa`,
  `pessoa_versao` e a lotação para o banco da folha; quem alimenta o cadastro (digitação,
  consulta à Receita).
- **Bloqueia:** a etapa do cadastro e o fim da exceção datada da PLAT-0017, item 9.

### A-10. Guarda do certificado A1 para coleta agendada

- **Hoje:** o A1 é lido a cada execução e fica só na memória (ASP-0003); na web, enviado pelo
  formulário a cada operação (PLAT-0020, item 5).
- **Opções:** OpenBao (MPL-2.0); arquivo cifrado no servidor com a chave fora dele;
  alternativa mais simples a pesquisar. Cada uma muda o risco de o certificado ficar no
  servidor e exige revisar a ASP-0003.
- **Bloqueia:** qualquer coleta agendada que dependa do A1.

### A-11. Perda máxima aceitável no backup

- **Proposta:** 24 horas (cópia lógica dos bancos toda noite e antes de cada migração,
  PLAT-0022, item 2).
- **Alternativa:** arquivamento contínuo do WAL com cópia base, para voltar a qualquer instante,
  com um processo e mais espaço a mais.
- **Bloqueia:** nada para começar; define a rotina do serviço de backup no `oper`.

### A-12. Retenção do backup e prazos legais de guarda

- **Falta decidir:** quantas cópias guardar (diárias, semanais, mensais, anuais) e por quanto
  tempo guardar cada tipo de documento (XML de NFS-e e NF-e, eventos e recibos do eSocial,
  folhas, dossiês). A interpretação dos prazos legais é do Marcello.
- **Fontes a conferir** (lembradas de memória pela sessão de 12/11/2026, sem leitura do texto
  oficial e sem afirmar prazo): Código Tributário Nacional (Lei 5.172/1966), arts. 173, 174 e
  195, parágrafo único; Ajuste SINIEF 07/2005 (guarda do XML da NF-e); legislação do FGTS (Lei
  8.036/1990) e a decisão do STF sobre a prescrição do FGTS (ARE 709.212); Código Civil, art.
  1.194; manuais do eSocial e da NFS-e nacional sobre guarda.
- **Até decidir:** o backup não apaga nada (PLAT-0022, item 4.4).

### A-13. Licenças: 0BSD do htmx e software de sistema nas imagens

- **0BSD:** o htmx (2.0.11, conferido no npm em 12/11/2026) é *Zero-Clause BSD*, mais
  permissiva que a BSD de duas cláusulas, mas fora da lista nominal da PLAT-0001, item 2.
  **Proposta:** acrescentar a 0BSD à lista de licenças permitidas, numa ADR que altere esse
  item; alternativa: trocar o htmx. Até decidir, o htmx não entra em código (PLAT-0021).
- **Imagens de container:** as imagens base (Debian, Python, PostgreSQL, Caddy) trazem software
  de sistema com licenças diversas, inclusive GPL. A PLAT-0001 trata das dependências do código.
  **Proposta:** registrar, na mesma ADR, que a política vale para as dependências do código e
  que componentes do sistema operacional da imagem, usados sem modificação, ficam fora dela
  (com o aviso de licenças na distribuição, como a PLAT-0008 já faz para o psycopg).
- **Bloqueia:** o primeiro adaptador web com htmx.

### A-14. FOLHA-0016: modelo de vínculo e contrato da folha

- **Contexto:** a parte da PLAT-0010 que é só da folha (vínculo, contrato, afastamento,
  formato `jsonb`, recibo do eSocial, seção "Implementação") não foi substituída pela
  PLAT-0018 e continua valendo na PLAT-0010.
- **Proposta:** uma sessão do `blatt` escreve a FOLHA-0016 com esse conteúdo, sem mudar o
  sentido, e a PLAT-0010 ganha o status "Substituída pela PLAT-0018 e pela FOLHA-0016".
- **Bloqueia:** nada; só a clareza de onde propor mudança no modelo de vínculo.

### A-15. `chave_vigencia: "mes_do_evento"` na PLAT-0003

- **Contexto:** a ASP-0008 (item 6) usa uma terceira chave de vigência, o mês em que o evento
  fiscal é registrado (prazos da manifestação do destinatário), e já a pôs no
  `comum.schema.json` do aspirador. A PLAT-0003 só prevê `competencia` e `mes_pagamento`
  (P-33 do aspirador).
- **Proposta:** ADR `PLAT-` que acrescente `mes_do_evento` ao item 3 e ao item 6 da PLAT-0003,
  com a definição do aspirador.
- **Bloqueia:** nada no aspirador (a divergência está registrada na ASP-0008); evita que outro
  módulo crie uma quarta chave por conta própria.

### A-16. Branch padrão do aspirador

- **Hoje:** o branch padrão do aspirador é `claude/admiring-mendel-vilgsf`; não há `main`. Os
  links para o aspirador nesta documentação apontam para ele.
- **Proposta:** criar `main` no aspirador a partir do branch atual e torná-lo o padrão; depois,
  trocar os links aqui.
- **Bloqueia:** nada; os links quebram se o branch atual for apagado.

### A-17. Levar a reorganização aos módulos (depois do aceite)

Em PR de cada repositório, conforme cada ADR for aceita:

- **todos:** trocar as cópias de `blatt.comum` e `blatt.infra` pela dependência
  `blatt-plataforma` e remover `src/blatt/__init__.py` (PLAT-0016); atualizar o trecho
  "Plataforma" do `CLAUDE.md` (trecho-padrão no [PLATAFORMA.md](PLATAFORMA.md));
- **`blatt`:** remover os arquivos-aviso das ADRs transferidas, com o índice redirecionando
  (PLAT-0016); FOLHA-0016 (A-14); gravar lotes e retornos do eSocial no arquivo imutável e
  gerar o dossiê da competência (PLAT-0022); extrair casos de uso das CLIs para o adaptador
  web (PLAT-0021);
- **`aspirador`:** remover `docs/plataforma/adr/0014-banco-por-modulo-e-orquestrador.md`, o
  aviso `docs/PLATAFORMA.md` e `src/blatt/infra/ORIGEM.md` (PLAT-0016); renomear o papel
  `blatt_orquestrador` para `blatt_entregador` (PLAT-0019); decidir numa `ASP-` o endereço por
  hash do arquivo de originais (PLAT-0022);
- **`oper`:** ADRs `OPER-` de implantação, entregador, portal e backup (PLAT-0019 a 0022).

## Encaminhadas

Pendências para as quais as propostas de 12/11/2026 trazem a decisão. Saem daqui para
"Resolvidas" quando a ADR correspondente for aceita (A-08).

| Pendência | Encaminhamento |
| --- | --- |
| A-01. Aceitar a PLAT-0015 (governança no `assembleia`) | A PLAT-0015 é substituída pela [PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md), que mantém as regras de governança (item 5); o aceite passa à A-08. |
| A-02. Classificação das ADRs transferidas (a PLAT-0010 mistura regra comum e da folha) | Regra comum na [PLAT-0018](adr/PLAT-0018-dono-de-cada-dado-e-cadastro.md), item 1; parte da folha na FOLHA-0016 (A-14). As demais classificações de 03/11/2026 ficam como estavam. |
| A-03. Distribuição do `blatt.comum` | Pacote `blatt-plataforma` instalado por tag do git; `blatt` como *namespace package*; fim das cópias e do manifesto ([PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md), item 4). O obstáculo da credencial sumiu: o `assembleia` é público desde 12/11/2026. |
| A-04. Antecipar o orquestrador (fase 2 da PLAT-0014) | O orquestrador dá lugar a um entregador sem banco próprio no `oper`, que entra em uso com o primeiro consumidor ([PLAT-0019](adr/PLAT-0019-integracao-por-fatos-e-entregador.md)). |
| A-05. Decisões de plataforma na ASP-0006 | Mapa de módulos, divisão captura/tratamento e escopo do MVP da plataforma na [PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md), itens 2 e 3, citando a ASP-0006 (P-25 do aspirador). |
| A-07. `blatt.infra` copiado e divergente | Versão canônica = a estendida do aspirador, dentro do `blatt-plataforma` ([PLAT-0016](adr/PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md), item 4) (P-20 do aspirador). |
| P-33 (b) do aspirador: `fiscal.nfe_manifestada` no índice de contratos | Feito em 12/11/2026 no [índice de contratos](contratos/README.md), com os demais fatos que o aspirador publica. A parte (a) é a A-15. |

## Resolvidas

| Data | Decisão | Registro |
| --- | --- | --- |
| 2026-11-03 | **PLAT-0014 aceita** pelo Marcello ("adr 0014 aceita"), com o faseamento dos itens 10 e 11 e o dono de cada dado do item 9. Decidida no repositório da folha (P-57), no mesmo dia da transferência; o aceite foi trazido para cá depois, com as notas de alteração parcial nas PLAT-0005, 0006, 0009 e 0010. | [PLAT-0014](adr/PLAT-0014-banco-por-modulo-e-orquestrador.md); blatt `e4352fc` (PR #19) |
| 2026-11-12 | **Direção da reorganização** dada pelo Marcello: repositórios separados (monorepo descartado), `oper` como operação da instância, entregador no lugar do orquestrador, servidor doméstico com Docker Compose e acesso só pela rede local, interface web, backup em três camadas com restic para disco local e Google Drive, cadastro geral centralizado com os dados sensíveis dos trabalhadores só na folha. | Propostas PLAT-0016 a PLAT-0022 (aceite na A-08) |
