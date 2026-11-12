# PLAT-0020: Infraestrutura aberta e implantação por Docker Compose num servidor da rede local

- **Status:** Proposta
- **Data:** 2026-11-12
- **Decisor:** Marcello
- **Substitui:** [PLAT-0006](PLAT-0006-infraestrutura-aberta.md) (inteira; a linha "Fila de
  trabalho" já tinha sido alterada pela PLAT-0014 e hoje está na
  [PLAT-0019](PLAT-0019-integracao-por-fatos-e-entregador.md)).
- **Origem:** sessão de 12/11/2026 com o Marcello (produção limitada num servidor doméstico).

## Contexto

A PLAT-0006 escolheu componentes abertos (containers OCI, PostgreSQL, OpenBao, sistema de
arquivos para XML e PDF, sem MinIO), mas não dizia como a instância é implantada. Em 12/11/2026 o
Marcello decidiu a primeira implantação real: ele é o único usuário, num servidor doméstico, com
Docker Compose, acesso só pela rede local e backup como requisito absoluto
([PLAT-0022](PLAT-0022-backup-arquivo-imutavel-e-dossies.md)).

Serviços gerenciados de nuvem (KMS, filas, bancos proprietários) prendem o sistema ao provedor
tanto quanto uma biblioteca proprietária, e o modelo de instância por escritório
([PLAT-0004](PLAT-0004-instancia-por-escritorio.md)) pode exigir rodar no servidor do próprio
cliente. A política de licenças é a da [PLAT-0001](PLAT-0001-python-e-politica-de-licencas.md).

## Decisão

### 1. Componentes

| Necessidade | Escolha | Licença (conferida em 12/11/2026) | Observação |
| --- | --- | --- | --- |
| Empacotamento | Imagens OCI | — | Rodam em Docker Engine ou Podman |
| Execução | Docker Engine + Docker Compose | Apache-2.0 (Moby v2.0.0-beta.29; Compose v5.7.1) | Docker Desktop não é usado (ver Referências) |
| Banco de dados | PostgreSQL | PostgreSQL License | Um servidor, um banco e um usuário por módulo ([PLAT-0017](PLAT-0017-persistencia-postgresql.md)) |
| Proxy reverso e TLS | Caddy | Apache-2.0 (v2.11.9) | CA interna; `forward_auth` para o portal ([PLAT-0021](PLAT-0021-interface-web.md)) |
| XMLs, PDFs e demais arquivos | Sistema de arquivos (volume do servidor) | — | Arquivo imutável da PLAT-0022; interface compatível com S3 só se um dia for preciso; evitar MinIO (AGPLv3 desde 2021) |
| Integração entre módulos | `outbox`/`inbox` no PostgreSQL e o entregador | — | PLAT-0019 |
| Cópia de segurança | restic + rclone | BSD-2-Clause; MIT | PLAT-0022 |
| Guarda de certificados A1 para coleta agendada | **Pendente** (OpenBao, MPL-2.0, ou alternativa mais simples) | — | Item 5 |

Princípio mantido: cada módulo fala com cada componente por um adaptador
([PLAT-0002](PLAT-0002-arquitetura-hexagonal.md)); trocar um componente é trocar adaptador.

### 2. Implantação

1. **Docker Compose num servidor doméstico**, definido no repositório `oper`. Serviços
   previstos:
   - `postgres`: um único servidor, com um banco e um usuário por módulo, e os papéis do
     entregador, do portal e do backup;
   - `caddy`: única porta publicada na rede local (HTTPS);
   - um container por módulo de negócio (folha, aspirador e os seguintes), cada um com a sua
     interface web e as suas linhas de comando;
   - `portal`, `entregador` e `backup`, do `oper`.
2. **Imagens construídas no próprio servidor a partir de tags** dos repositórios (módulos e
   `oper`); a dependência `blatt-plataforma` vem por tag do `assembleia`, com o commit fixado no
   `uv.lock` ([PLAT-0016](PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md)). Imagens base
   (Python, PostgreSQL, Caddy) com versão fixada. Atualizar é mudar a tag e reconstruir.
3. **Containers não-root:** cada imagem roda com usuário sem privilégio; volumes montados só
   onde o serviço precisa, e só leitura quando ele não grava.
4. **Segredos em arquivos, não em variáveis de ambiente:** senhas dos bancos, chave de sessão
   do portal e credenciais do backup são *secrets* do Compose, montados como arquivos. A
   configuração de conexão (`BLATT_DSN_<MODULO>`, PLAT-0017) não leva senha; a senha é lida do
   arquivo de segredo (por exemplo, pelo parâmetro `passfile` da libpq). Nenhum segredo entra
   em repositório, imagem ou log.

### 3. Rede

1. **Acesso só pela rede local, sem exposição à internet:** nenhuma porta aberta no roteador,
   nenhum túnel. O `caddy` é o único serviço com porta publicada; o `postgres` e os containers
   dos módulos só são alcançáveis pela rede interna do Compose.
2. **TLS pela CA interna do Caddy** (`tls internal`): o certificado raiz é instalado nos
   aparelhos do Marcello que acessam o portal. Nada de HTTP sem TLS na rede local.
3. **Saída para a internet** só para o que os módulos e o backup precisam (webservices do
   governo, destino remoto do backup).
4. Acesso de fora de casa (VPN, por exemplo) fica fora desta decisão; se vier, é ADR nova.

### 4. Ambientes

Uma instância de produção (o servidor doméstico). Desenvolvimento e testes continuam nas
máquinas de desenvolvimento e no CI, com PostgreSQL temporário (PLAT-0017, item 8). Webservices
do governo seguem as travas de cada módulo (por exemplo, FOLHA-0007 e ASP-0001).

### 5. Certificado A1

1. **No início, o certificado vai pelo formulário a cada operação** que precisar dele (coleta,
   envio), junto com a senha, e fica **só na memória do processo** durante a operação: não é
   gravado em disco, banco, log nem arquivo temporário. É a mesma regra da ASP-0003 (A1 lido a
   cada execução, sem guarda), estendida ao adaptador web.
2. **A coleta agendada exige guarda do certificado**, e a guarda não é decidida aqui:
   OpenBao (MPL-2.0, fork do Vault sob a Linux Foundation) ou uma alternativa mais simples
   (por exemplo, arquivo cifrado com chave fora do servidor) ficam como pendência do Marcello.
   Até lá, não há coleta agendada que dependa do A1.
3. O certificado real **nunca passa pela sessão do Claude Code**; os testes usam certificados
   gerados na hora.

## Alternativas consideradas

- **Kubernetes (ou k3s).** Padrão para muitos serviços, mas desproporcional a um servidor e um
  usuário; as imagens OCI permitem chegar lá depois.
- **Nuvem pública.** Tira o servidor de casa, mas põe dados pessoais e sensíveis num provedor e
  pede exposição à internet; contraria a decisão de acesso só pela rede local.
- **Instalação direta no sistema operacional (systemd, sem containers).** Menos uma camada, mas
  mistura dependências dos módulos e dificulta reconstruir o servidor do zero.
- **Podman + `podman compose`** (Apache-2.0). Equivalente e sem *daemon* com privilégio; fica
  como alternativa se o Docker Engine incomodar. As imagens são as mesmas.
- **nginx ou Traefik no lugar do Caddy.** Funcionam, mas o Caddy traz a CA interna e o
  `forward_auth` prontos, com configuração curta.
- **Segredos em variáveis de ambiente.** Mais simples, mas vazam em `docker inspect`, em
  listagens de processos e em relatórios de erro.

## Consequências

- O servidor passa a ser peça crítica: queda dele para todos os módulos (aceito; a PLAT-0017 já
  aceitava a queda do servidor PostgreSQL). A volta é reconstruir pelas tags e restaurar o
  backup (PLAT-0022).
- Operar PostgreSQL, Caddy e backup por conta própria exige rotina de atualização e
  monitoramento que um serviço gerenciado faria; o custo é aceito em troca da portabilidade.
- A CA interna exige instalar o certificado raiz em cada aparelho e renovar se ele mudar.
- O `oper` ganha as ADRs `OPER-` de implantação: arquivo do Compose, provisionamento dos bancos
  e papéis (hoje um script por módulo, como o `scripts/sql/provisionar.sql` do aspirador),
  agendamentos.
- As imagens base trazem software de sistema com licenças diversas (inclusive GPL); a
  PLAT-0001 trata das dependências do código, e a leitura para imagens fica como pendência.

## Referências

- [PLAT-0006](PLAT-0006-infraestrutura-aberta.md) (substituída por esta, quando aceita);
  ASP-0003, certificado por execução:
  [aspirador docs/adr/0003](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/docs/adr/0003-certificado-por-execucao.md).
- Licenças conferidas em 12/11/2026 no arquivo `LICENSE` do código-fonte de cada versão,
  obtido pelo proxy de módulos Go (`proxy.golang.org`):
  Caddy v2.11.9 (Apache-2.0), https://github.com/caddyserver/caddy/blob/v2.11.9/LICENSE;
  Docker Compose v5.7.1 (Apache-2.0), https://github.com/docker/compose/blob/v5.7.1/LICENSE;
  Moby (Docker Engine) v2.0.0-beta.29 (Apache-2.0), https://github.com/moby/moby/blob/master/LICENSE;
  Podman v5.8.10 (Apache-2.0), https://github.com/containers/podman/blob/v5.8.10/LICENSE;
  OpenBao, commit `4771dc1` de 14/07/2026 (MPL-2.0), https://github.com/openbao/openbao/blob/main/LICENSE.
  As páginas do GitHub em si não abriram na sessão.
- Caddy, diretivas `forward_auth` e `tls internal`: conferidas no código-fonte da v2.11.9
  (`modules/caddyhttp/reverseproxy/forwardauth/caddyfile.go` e
  `caddyconfig/httpcaddyfile/builtins.go`); documentação em
  https://caddyserver.com/docs/caddyfile/directives/forward_auth e
  https://caddyserver.com/docs/caddyfile/directives/tls (não abriram na sessão; a conferir).
- Compose Specification, `secrets` com `file`: conferido no schema
  `compose-spec.json` do `compose-go` v2.16.2; documentação em
  https://docs.docker.com/compose/how-tos/use-secrets/ (não abriu na sessão; a conferir).
- Dockerfile, instrução `USER`: https://docs.docker.com/reference/dockerfile/ (citado de
  memória; a conferir).
- libpq, arquivo de senhas e parâmetro `passfile`:
  https://www.postgresql.org/docs/current/libpq-pgpass.html (citado de memória; a conferir).
- PostgreSQL, licença: https://www.postgresql.org/about/licence/ (citada na PLAT-0006; não
  abriu na sessão).
- Docker Desktop tem licença própria, não aberta (citado de memória; a conferir em
  https://www.docker.com/legal/docker-subscription-service-agreement/).
- MinIO, mudança para AGPLv3:
  https://blog.min.io/from-open-source-to-free-and-open-source-minio-is-now-fully-licensed-under-gnu-agplv3
  (citada na PLAT-0001 e na PLAT-0006).
