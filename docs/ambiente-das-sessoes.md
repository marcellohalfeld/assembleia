# O que se aprendeu sobre o ambiente das sessões

Notas práticas para as sessões do Claude Code que trabalham nos repositórios da plataforma. Não
são regras de arquitetura; podem mudar com a configuração do ambiente. Vieram da seção 13 do
`PLATAFORMA.md` (sessões da folha, outubro de 2026), com o que a sessão de 12/11/2026
acrescentou.

- **Rede da sessão na nuvem:** `www.gov.br`, Planalto, Senado, CONCLA/IBGE e sites de
  fornecedores não resolveram em outubro de 2026. A Câmara (`www2.camara.leg.br`, "norma
  atualizada") respondeu e foi a fonte dos textos legais conferidos. Quando a fonte primária
  está fora de alcance, o Marcello confere e manda o trecho; o código registra o que foi lido
  por quem.
- **Em 12/11/2026**, também não abriram: `postgresql.org`, `docs.docker.com`,
  `caddyserver.com`, `peps.python.org`, `docs.astral.sh`, `microservices.io`, `htmx.org`,
  `spdx.org` e páginas de projetos no `github.com` fora dos repositórios da plataforma.
  Responderam os registros de pacotes: a API JSON do PyPI (`https://pypi.org/pypi/<nome>/json`,
  licença e versão), o registro do npm (`https://registry.npmjs.org/<nome>`, inclusive o
  `LICENSE` dentro do pacote) e o proxy de módulos Go (`https://proxy.golang.org/<módulo>/@v/<versão>.zip`),
  que traz o código-fonte de uma versão com `LICENSE` e documentação (serviu para Caddy,
  restic, rclone, Docker Compose, Moby, Podman e OpenBao). As páginas de manual do PostgreSQL
  instalado na sessão (`man pg_dump`) servem para conferir opções das ferramentas.
- **GitHub:** pelo conector (ferramentas MCP do GitHub), não pela CLI `gh`; o conector só alcança
  os repositórios anexados à sessão. Cada sessão trabalha num branch designado; PR aberto ao
  fim, acompanhado até o CI passar.
- **Retomada depois do limite de uso:** a sessão agenda a própria retomada (tarefa agendada)
  com o objetivo e o estado, e apaga o agendamento ao concluir.
- **macOS do Marcello:** zsh não aceita `#` como comentário em comandos colados (os guias não
  põem comentários dentro dos blocos de comando); `.venv` dentro de pasta sincronizada pode
  receber a marca de oculto e quebrar a instalação editável (`chflags -R nohidden .venv`).
