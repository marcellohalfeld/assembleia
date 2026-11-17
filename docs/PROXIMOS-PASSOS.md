# Próximos passos da plataforma (plano de passagem, 17/11/2026)

Plano para as sessões que assumirem o trabalho depois da sessão de 12 a 15/11/2026, que
reorganizou a plataforma (PLAT-0016 a 0022) e levou a folha para a web. Não é ADR nem regra: é a
ordem proposta do que falta, com o que cada frente precisa ler e o que depende do Marcello.
Quem concluir uma frente atualiza este arquivo (ou o apaga, quando tudo estiver nos `ROADMAP.md`).

A fonte de verdade de cada repositório continua sendo o `docs/ROADMAP.md` ("onde paramos") e o
`docs/PENDENCIAS.md` dele. Se este plano divergir deles, vale o repositório.

## 1. Onde está cada repositório

| Repositório | Estado em 17/11/2026 | Em aberto |
| --- | --- | --- |
| `assembleia` | `main` com o pacote `blatt-plataforma` 0.3.0 (tag `v0.3.0`): `blatt.comum`, `blatt.infra` (configuração, arquivo imutável, migrações, fatos, certificado A1 em memória), `blatt.web`. PLAT-0016 a 0022 aceitas. | Branch `claude/elegant-lamport-wr5gbr` tem dois commits só de documentação fora do `main` (andamento da A-22 e este plano), sem PR. |
| `blatt` (folha) | [PR 28](https://github.com/marcellohalfeld/blatt/pull/28) aberto contra `main`: pacote v0.3.0, imagem, arquivo imutável, web completa dos periódicos (carga, conferir, transmitir, consultar, reenviar, fechar, reabrir, pagamentos da implantação), folha conferida (FOLHA-0021), dossiê, cálculo do 13º só no domínio. 1158 testes, 2 pulados. Migrações 0001 a 0010. | **[PR 27](https://github.com/marcellohalfeld/blatt/pull/27) também aberto contra `main`** (ver a frente A). FOLHA-0026 proposta (P-84). P-85 (13º). |
| `aspirador` | [PR 14](https://github.com/marcellohalfeld/aspirador/pull/14) aberto contra `claude/admiring-mendel-vilgsf` (o branch padrão; não há `main`): pacote v0.3.0, imagem, web `/fiscal`, dossiê, A1 pelo pacote (só Linux). 187 testes. | P-47 (ADR curta para a ASP-0009), P-29 (primeira execução real), A-16 (branch padrão). |
| `oper` | Só existe o branch `claude/elegant-lamport-wr5gbr` (não há `main`, logo não há PR possível): Compose, provisionamento, backup e restauração, entregador de fatos, portal. OPER-0001 a 0007 aceitas. | O-02 (montar o servidor), O-08, O-09, O-10. |

Nada foi testado contra o eSocial, o ADN ou a SEFAZ reais, nem em navegador real, nem no
servidor: tudo o que existe de web e de operação foi provado só por testes automatizados e em
containers dentro das sessões.

## 2. O que só o Marcello faz

Em ordem de quanto destrava:

1. **Decidir o PR 27 × PR 28 da folha** (frente A): os dois implementam o 13º, em arquivos de
   mesmo nome.
2. **Aceitar (ou ajustar) a FOLHA-0026** (P-84 da folha; três perguntas com proposta) e, com a
   frente A resolvida, fazer o merge do PR 28.
3. **Criar o branch `main` no `oper`** a partir de `claude/elegant-lamport-wr5gbr` e **decidir o
   branch padrão do `aspirador`** (A-16); fazer o merge do PR 14.
4. **Montar o servidor** pelo `oper/docs/guia-servidor.md` (O-02: Linux, Docker, rclone com o
   Google Drive, senha do portal O-08) e rodar o primeiro backup com `restaurar-teste`.
5. **Primeiro uso real da folha pela web**, na produção restrita, pelo
   `blatt/docs/esocial/guia-transmissao-web.md`. É o que valida a fase 3.
6. **Responder a P-85** (13º; onze perguntas) e fornecer **casos-ouro** (P-04 da folha; item 9 da
   P-85): sem eles, nenhum cálculo novo está validado.
7. Pendências de plataforma sem prazo: A-06 (aceite das PLAT-0001 a 0004), A-09 (cadastro geral),
   A-12 (prazos de guarda; o backup não apaga nada até lá), A-13 (GPL nas imagens base), A-21
   (wiki normativa), A-22 itens (b) e (c).

Regras que não mudam: só o Marcello muda status de ADR para Aceita, marca tags e faz merge; o
certificado A1 nunca passa por uma sessão; dados reais de clientes nunca entram no git;
interpretação de norma é dele.

## 3. Frentes de trabalho, em ordem

Cada frente é uma sessão (ou poucas), num repositório, com objetivo declarado. As frentes A e B
vêm primeiro; C a F podem andar em paralelo depois, em repositórios diferentes.

### A. Folha: conciliar o PR 27 com o PR 28 (bloqueia o 13º, as férias e a rescisão)

**Problema.** O PR 27 (`claude/kind-faraday-r242zf`, de 10/11/2026) implementa 13º, férias e
rescisão com S-2299 (P-37 a P-39): domínio, aplicação, eventos, rubricas no catálogo, folha a
partir do banco e um roteiro de testes; mais de 6 mil linhas, escritas sobre o `main` anterior
à reorganização. A sessão de 15/11/2026 não o viu e escreveu, no PR 28, outro
`dominio/decimo_terceiro.py` e outro `tests/test_decimo_terceiro.py`, só com o domínio do 13º.
São duas implementações da mesma regra, em arquivos de mesmo nome: os dois PRs não entram os
dois como estão.

**O que a sessão faz.**

1. Ler os dois: no PR 27, `dominio/{decimo_terceiro,ferias,rescisao,aviso_previo,verbas}.py`,
   `aplicacao/{decimo_terceiro,ferias,rescisao,eventos_ferias}.py`, as rubricas e
   `tests/test_roteiro_etapa5.py`; no PR 28, `dominio/decimo_terceiro.py`,
   `docs/dominio/regras/decimo-terceiro.md` e a P-85.
2. Comparar regra a regra o 13º das duas (avos, 1ª parcela, INSS em separado, IRRF exclusivo,
   FGTS, complemento, arredondamento, rubricas e incidências) e rodar os sete exemplos de
   `decimo-terceiro.md` na implementação do PR 27. Toda diferença de centavo ou de regra vira
   linha de uma tabela para o Marcello, com a fonte.
3. Propor ao Marcello uma de duas saídas, com a recomendação: **(i)** rebasear o PR 27 sobre o
   PR 28 e manter o 13º do PR 27 (mais completo: tem aplicação e eventos), trazendo do PR 28 o
   que ele tiver a mais (recusas explícitas, exemplos, formato de caso-ouro, perguntas da P-85);
   ou **(ii)** o inverso. A proposta inicial desta passagem é a (i), a confirmar pela comparação.
4. Só depois da decisão: fazer a junção num branch só, com a sequência completa passando, sem
   perder teste de nenhum dos dois lados.

**Cuidado.** O PR 27 mexe em `folha_do_banco.py`, `folha_mensal.py`, `eventos_periodicos.py` e
`rubricas.py`, que o PR 28 também mudou (folha conferida, transmissão). O conflito é real; a
prova de que nada mudou no cálculo mensal são os testes e a comparação de XML do PR 28.

### B. Folha: fechar o PR 28

Depende do aceite da FOLHA-0026 (P-84) e da decisão da frente A.

- Reconstruir a imagem e conferir migrações 0001 a 0010, `/saude` e as onze rotas que gravam
  (403 sem CSRF, 422 sem confirmação): não foi refeito depois da parte 3b.
- Registrar o aceite da FOLHA-0026 quando o Marcello der (linha de status, índice, P-84).
- Depois do merge: recomeçar o branch de trabalho a partir do `main`.

### C. Folha: portar o resto para a web

Diretriz do Marcello (P-79): a linha de comando era artifício do MVP; tudo vai para a web, em
ordem de uso, e "precisamos ser simples". A lista está em `blatt/docs/ROADMAP.md`, seção
"Portar para a web". Ordem proposta do que falta:

1. Admissão e alterações (S-2200, S-2205, S-2206).
2. Afastamentos (S-2230).
3. TSVE: sócio e diretor (S-2300, S-2306, S-2399).
4. 13º na folha conferida, no S-1200/S-1210 do período anual e no fechamento anual (depois da
   frente A e da P-85).
5. Férias e desligamento (S-2299), depois da frente A.
6. Retificação e exclusão (S-3000): antes, conferir no MOS (FOLHA-0021, pergunta 7).
7. Tabelas do empregador (S-1000, S-1005, S-1010, S-1020).
8. Consulta de identificadores e download (FOLHA-0023, parte 3c).
9. SST (S-2210, S-2220, S-2240).

Para cada item, o caminho já existe e deve ser reaproveitado: caso de uso na aplicação, o mesmo
"Transmitir" (gerar, assinar, guardar no arquivo imutável antes da rede, enviar), as travas da
FOLHA-0007 e as duas da FOLHA-0023, A1 só em memória. **Rota nova que grave exige ADR nova que
substitua a vigente com a lista inteira** (hoje a FOLHA-0026, proposta; regra herdada da
FOLHA-0022, item 3), aceita antes do merge. Para não repetir essa ADR a cada item, vale propor
ao Marcello uma ADR só para os não periódicos (itens 1 a 3), com a lista de rotas de uma vez.

Fora da lista, na wishlist do ROADMAP da folha: **registro consolidado de atividades** (quem fez
o quê, quando, em qual empresa). Hoje só a folha conferida guarda autor; cadastro e carga pela
web não guardam. O `docs/visao.md` promete trilha de auditoria completa.

### D. `oper`: servidor de pé

- Acompanhar o Marcello na montagem (O-02) e corrigir o que o guia errar.
- Conferir o limite de tempo do Caddy para a requisição longa de transmitir (P-82 da folha).
- O-09 (CA interna do Caddy fora do backup), O-10 (teste com os módulos no CI), O-03.
- Agendar a geração dos dossiês (P-72 da folha, P-44 do aspirador) quando o Marcello decidir.
- Depois que existir `main`: abrir o PR do que estiver no branch de trabalho.

### E. `aspirador`

- P-47: ADR curta (ASP-0011) alinhando a ASP-0009 ao A1 só no Linux, sem plano B em disco.
- Refazer `docs/guia-primeira-consulta-adn.md` e `docs/guia-nfe.md` para rodar no servidor
  (hoje mandam rodar no macOS, que deixou de funcionar com o A1 pelo pacote).
- P-29: primeira execução real do `baixar-nfe`, pelo guia refeito.
- Mesma diretriz da folha: levar as operações que restam na linha de comando para a web.

### F. `assembleia`

- Abrir PR com os commits de documentação do branch de trabalho (A-22 e este plano).
- A-22 (c): levar `cnpj_do_certificado` ao pacote (versão 0.4.0), se o Marcello concordar.
- Ajustar a redação "a web chama os mesmos casos de uso da CLI" (PLAT-0021, item 1, e os
  `CLAUDE.md` dos módulos), que pressupõe a linha de comando: proposta de ADR ou nota, à escolha
  do Marcello.
- A-09: desenho do cadastro geral centralizado, com os dados pessoais dos trabalhadores só na
  folha (PLAT-0018). É a maior decisão de arquitetura ainda em aberto; adiada pelo Marcello em
  12/11/2026.
- A-21: wiki normativa.

## 4. O que as sessões precisam saber

- **Ler primeiro:** o `CLAUDE.md` do repositório, o `docs/ROADMAP.md` e o `docs/PENDENCIAS.md`
  dele, e o [`PLATAFORMA.md`](PLATAFORMA.md) daqui. Para a web da folha, as FOLHA-0020 a 0026.
- **Antes de começar qualquer frente, listar os PRs e branches abertos do repositório** e ler os
  que tocam o assunto. A duplicação da frente A aconteceu por faltar esse passo.
- **Sequência de conferência antes de cada commit:** a do `CLAUDE.md` de cada repositório, com
  `BLATT_EXIGIR_POSTGRES=1`. Nunca pular, desligar ou editar teste para passar.
- **Nenhuma chamada real** a eSocial, ADN ou SEFAZ a partir de sessão; os testes usam servidor
  fictício local e certificado gerado no teste. Só produção restrita no eSocial; liberar a
  produção exige ADR nova (FOLHA-0007, item 7).
- **Fontes:** toda regra cita lei, manual ou leiaute com link; o que não foi aberto fica "a
  conferir". Em novembro de 2026, `www.gov.br/esocial` (MOS, Manual do Desenvolvedor, leiaute)
  abriu por `curl`, com o texto extraído por `pdftotext`; o Planalto não respondeu. O domínio
  `globalsign.com` foi liberado pelo Marcello.
- **Docker na sessão:** iniciar o `dockerd` à mão; `REGISTRO=mirror.gcr.io/library`; CA do
  proxy por `--secret id=ca_extra,src=/root/.ccr/ca-bundle.crt` e `--network host`; nunca
  desligar o TLS. Mais notas em [`ambiente-das-sessoes.md`](ambiente-das-sessoes.md).
- **Limite de uso:** sessões longas param no meio. Commit e push ao fim de cada passo, para
  nada ficar só no container.
- **Datas** nos registros de decisão: horário de Brasília.
- **Relato ao Marcello:** sempre com o que foi e o que não foi testado, e com as fontes; ele
  desconfia por método e decide com base nisso.
