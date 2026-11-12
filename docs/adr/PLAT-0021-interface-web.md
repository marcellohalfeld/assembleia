# PLAT-0021: Interface web — adaptador web em cada módulo e um portal no `oper`

- **Status:** Aceita (12/11/2026: "plat-0017 a 0022 aprovadas")
- **Data:** 2026-11-12
- **Decisor:** Marcello
- **Origem:** sessão de 12/11/2026 com o Marcello; a interface web é a próxima entrega, com
  urgência ([PLAT-0016](PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md), item 3).

## Contexto

Os dois módulos em uso são operados só por linhas de comando (`blatt-esocial`, `blatt-banco`
na folha; os comandos do aspirador), rodadas no computador do Marcello a partir de guias. Para
produção limitada num servidor doméstico ([PLAT-0020](PLAT-0020-infraestrutura-e-implantacao.md)),
ele precisa de uma interface no navegador para os mesmos trabalhos, mais uma visão geral da
instância: o que cada módulo fez, o estado dos backups e a linha do tempo dos fatos.

Restrições: a arquitetura hexagonal ([PLAT-0002](PLAT-0002-arquitetura-hexagonal.md)), em que
interface é adaptador; cada módulo precisa poder ser trocado sem grande impacto nos outros; um
único usuário; Python como linguagem ([PLAT-0001](PLAT-0001-python-e-politica-de-licencas.md)); e
o desejo de não manter uma segunda pilha (JavaScript com cadeia de build).

## Decisão

1. **Cada módulo tem um adaptador web**, em `blatt.<modulo>.adaptadores.web`, que chama **os
   mesmos casos de uso da linha de comando**. A web não contém regra de negócio: valida a
   forma da entrada, chama a aplicação e mostra o resultado. Lógica que hoje está presa nas
   CLIs (montagem de resultados, decisões de fluxo) é extraída para a camada de aplicação
   antes de ser usada pela web, para que CLI e web sejam dois adaptadores finos sobre o mesmo
   caso de uso.
2. **O adaptador web roda no container do próprio módulo**, sob um prefixo de caminho próprio
   (`/folha`, `/fiscal` e assim por diante). Um módulo fora do ar tira do ar só o prefixo
   dele.
3. **Um portal no `oper`**, com: login, página inicial com o acesso aos módulos, estado dos
   backups e dos testes de restauração ([PLAT-0022](PLAT-0022-backup-arquivo-imutavel-e-dossies.md)),
   e a linha do tempo dos fatos (agregada das `outbox` e `inbox`,
   [PLAT-0019](PLAT-0019-integracao-por-fatos-e-entregador.md), item 11, e dos registros de
   execução). O portal não tem regra de negócio de nenhum módulo e não lê tabela de negócio.
4. **Caddy na frente de tudo, com `forward_auth` para o portal:** cada requisição a um módulo
   passa antes por uma verificação no portal; sem sessão válida, vai para o login. Os módulos
   recebem do Caddy o usuário autenticado num cabeçalho e não implementam login. Os containers
   dos módulos não são alcançáveis a não ser pelo Caddy (PLAT-0020, item 3).
5. **Renderização no servidor, com FastAPI + Jinja2 + htmx, sem cadeia de build de
   JavaScript.** Páginas HTML montadas no servidor; o htmx (um arquivo, servido pela própria
   aplicação, sem CDN) faz as trocas parciais. Servidor ASGI: Uvicorn.
6. **Base visual comum no `blatt-plataforma`** (PLAT-0016, item 4): modelo de página,
   navegação, estilo, o arquivo do htmx e utilitários (leitura do usuário autenticado, proteção
   contra CSRF nos formulários, mensagens de erro). Cada módulo usa a base e acrescenta as suas
   páginas.
7. **Uploads sensíveis** (certificado A1 e senha, PLAT-0020, item 5): lidos para a memória e
   descartados ao fim da operação; o adaptador web garante que não passem por arquivo
   temporário em disco nem por log.

### Licenças (conferidas em 12/11/2026)

| Componente | Versão consultada | Licença | Fonte |
| --- | --- | --- | --- |
| FastAPI | 0.162.5 | MIT | PyPI |
| Starlette | 1.10.0 | BSD-3-Clause | PyPI |
| Uvicorn | 0.54.0 | BSD-3-Clause | PyPI |
| Jinja2 | 3.1.6 | BSD (classificador do PyPI) | PyPI |
| python-multipart (formulários e upload no FastAPI) | 0.0.33 | Apache-2.0 | PyPI |
| itsdangerous (assinatura de cookies de sessão) | 2.2.0 | BSD (classificador do PyPI) | PyPI |
| htmx | 2.0.11 (`latest` no npm; a 4.0.1 é `next`) | **0BSD** | npm, arquivo `LICENSE` do pacote |

Todas estão na lista da PLAT-0001, item 2, **exceto o htmx**: a 0BSD (*Zero-Clause BSD*) é mais
permissiva que a BSD de duas cláusulas (só a permissão e a isenção de garantia, sem exigir
aviso de copyright), mas não está nominalmente na lista. **Decisão do Marcello pendente:**
aceitar a 0BSD como permissiva (acréscimo à lista da PLAT-0001) ou trocar o htmx. Até lá, o
htmx não entra em código. Decidido em 12/11/2026 (pendência A-13): 0BSD aceita como permissiva.

## Alternativas consideradas

- **SPA (React, Vue ou similar) com uma API por módulo.** Interface mais rica, mas uma segunda
  linguagem, uma cadeia de build e uma API a versionar em cada módulo, para um único usuário.
- **Uma aplicação web única importando todos os módulos.** Um processo só, mas acopla os
  módulos num mesmo ambiente Python e numa mesma versão de dependências: trocar ou derrubar um
  módulo afeta todos, o contrário do que a PLAT-0016 pede.
- **Django.** Completo (admin, sessões, formulários), mas traz ORM e modelo de aplicação
  próprios, que competem com o SQL explícito ([PLAT-0017](PLAT-0017-persistencia-postgresql.md))
  e com a arquitetura hexagonal; usaria-se uma fração dele.
- **Login em cada módulo.** Dispensa o `forward_auth`, mas repete autenticação e sessão em
  cada módulo.

## Consequências

- A primeira entrega web de cada módulo começa por extrair casos de uso das CLIs para a
  aplicação; isso melhora os testes, mas é trabalho antes da primeira tela.
- O portal é um ponto único de entrada: fora do ar, os módulos ficam inacessíveis pelo
  navegador (as linhas de comando continuam funcionando no servidor).
- Os detalhes do portal (armazenamento do usuário e das sessões, origem dos dados de backup,
  formato da linha do tempo) são decisões `OPER-`. Proposta para começar: sem banco próprio,
  com o usuário e a chave de sessão em *secrets* do Compose e o estado dos backups lido de
  arquivos gravados pelo serviço de backup.
- O portal precisa de um papel de banco só de leitura nas tabelas de integração de cada módulo
  (PLAT-0019, item 11); provisionado pelo `oper`.
- Sem cadeia de build de JavaScript, não há verificação de licenças de pacotes npm a fazer; o
  arquivo do htmx entra versionado, com a licença ao lado.

## Referências

- [PLAT-0002](PLAT-0002-arquitetura-hexagonal.md) (interface como adaptador) e
  [PLAT-0001](PLAT-0001-python-e-politica-de-licencas.md), item 2 (licenças permitidas).
- Metadados do PyPI consultados em 12/11/2026: https://pypi.org/project/fastapi/,
  https://pypi.org/project/starlette/, https://pypi.org/project/uvicorn/,
  https://pypi.org/project/Jinja2/, https://pypi.org/project/python-multipart/,
  https://pypi.org/project/itsdangerous/ (lidos pela API JSON, `https://pypi.org/pypi/<nome>/json`).
- htmx no npm, licença 0BSD, versão 2.0.11, arquivo `LICENSE` do pacote lido em 12/11/2026:
  https://www.npmjs.com/package/htmx.org; texto da 0BSD na SPDX:
  https://spdx.org/licenses/0BSD.html (não abriu na sessão; a conferir).
- Caddy, `forward_auth`: ver as referências da [PLAT-0020](PLAT-0020-infraestrutura-e-implantacao.md).
- Documentação de FastAPI (https://fastapi.tiangolo.com/), Jinja2
  (https://jinja.palletsprojects.com/) e htmx (https://htmx.org/): não abriram na sessão de
  12/11/2026; citadas como página oficial de cada projeto.
