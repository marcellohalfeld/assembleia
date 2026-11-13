# Contrato web: módulos, portal e Caddy

O que a base web do `blatt-plataforma` (`blatt.web`, a partir da 0.2.0) espera do Caddy e do
portal do `oper`, e o que garante aos módulos
([PLAT-0021](../adr/PLAT-0021-interface-web.md), itens 2, 4 a 7;
[PLAT-0020](../adr/PLAT-0020-infraestrutura-e-implantacao.md), itens 3 e 5). As decisões de
implantação (Caddyfile, portal) são `OPER-`; este texto é a interface entre as peças. Os
pontos 1 a 4 confirmam o que já está em `docs/contrato-imagem-modulo.md` do `oper` (item 3) e
nos encaixes comentados do `caddy/Caddyfile` de lá.

## 1. Módulo

| Item | Valor |
| --- | --- |
| Porta | `0.0.0.0:8000`, HTTP simples, só na rede `web` do Compose (TLS termina no Caddy) |
| Servidor | Uvicorn: `uvicorn blatt.<modulo>.adaptadores.web:app --host 0.0.0.0 --port 8000` |
| Prefixo | Um por módulo, `^/[a-z][a-z0-9-]*$`: `/folha`, `/fiscal`. Todas as rotas do módulo ficam sob ele; o Caddy repassa o caminho **com** o prefixo (`handle`, não `handle_path`) |
| Arquivos da base | `<prefixo>/_blatt/blatt.css`, `<prefixo>/_blatt/htmx.min.js` (servidos pelo módulo, sem CDN) |
| Arquivos do módulo | `<prefixo>/estatico/...`, se o módulo tiver |
| Saúde | `GET /saude` e `GET <prefixo>/saude`: `200 {"estado": "ok", "modulo": ..., "versao": ...}`, ou `503` com `"estado": "falha"` se a conferência do módulo falhar. **Sem** exigir usuário: serve ao `healthcheck` do Compose (`/saude`) e a quem passa pelo Caddy |
| Corpo | Requisição que grava (POST, PUT, PATCH, DELETE) com até 5 MiB por padrão (`limite_corpo`), lida para a memória; acima disso, `413` |

## 2. Identidade

- O módulo **não faz login**. Toda requisição, menos a saúde, precisa do cabeçalho
  **`X-Blatt-Usuario`**, com o usuário autenticado: texto `^[A-Za-z0-9._@+-]{1,128}$` (sem
  espaço nem acento; o portal escolhe o formato dentro disso, por exemplo `marcello`).
- Sem o cabeçalho, ou fora do formato: `401` com página "Acesso só pelo portal". O módulo não
  redireciona para o login; quem redireciona é o portal, pelo `forward_auth`.
- O valor fica disponível aos modelos (`usuario`) e às rotas (`blatt.web.seguranca.usuario_do_escopo(request.scope)`).
- **Quem garante que o cabeçalho é verdadeiro é o Caddy**: o container do módulo só é
  alcançável pela rede `web` (PLAT-0020, item 3.1), e o Caddy apaga o `X-Blatt-Usuario` que
  vier do cliente antes de copiar o da resposta do portal (conferido no código do Caddy
  v2.11.9, `modules/caddyhttp/reverseproxy/forwardauth/caddyfile.go`: "Always delete the
  client-supplied header before conditionally setting it from the auth response").

## 3. Portal: o que responder ao `forward_auth`

O Caddy chama o portal sempre com `GET` no `uri` do `forward_auth` (`/autenticar`), com os
cabeçalhos da requisição original, inclusive o `Cookie` da sessão, mais `X-Forwarded-Method` e
`X-Forwarded-Uri` (método e caminho originais) e os `X-Forwarded-*` do `reverse_proxy`
(conferido no mesmo arquivo do Caddy v2.11.9). O portal responde:

- **sessão válida:** `2xx` (sem corpo) com `X-Blatt-Usuario: <usuario>`. O Caddy copia o
  cabeçalho para a requisição ao módulo e a repassa;
- **sem sessão:** `302` (ou `303`) com `Location` para o login do portal, de preferência com
  o endereço original para voltar depois (`X-Forwarded-Uri`). Qualquer resposta que não seja
  `2xx` volta ao navegador como veio, e o módulo não é chamado;
- a resposta `2xx` não pode deixar de trazer o `X-Blatt-Usuario`: sem ele o módulo responde
  `401`.

O cookie de sessão do portal é dele (nome, assinatura, validade: decisão `OPER-`). Ele não pode
se chamar `__Host-blatt-csrf`, que é o da base (item 5).

## 4. Caddyfile (encaixe para o `oper`)

O que já está comentado no `caddy/Caddyfile` do `oper` atende ao contrato:

```caddyfile
(autenticado) {
	forward_auth portal:8000 {
		uri /autenticar
		copy_headers X-Blatt-Usuario
	}
}

handle /folha/* {
	import autenticado
	reverse_proxy folha:8000
}
handle /fiscal/* {
	import autenticado
	reverse_proxy aspirador:8000
}
handle {
	reverse_proxy portal:8000
}
```

- Manter o `Host` original (o padrão do `reverse_proxy`): a proteção contra CSRF compara o
  `Origin` do navegador com o `Host` (item 5).
- O caminho `/folha` sem barra final não casa com `/folha/*`; se for preciso, um
  `redir /folha /folha/` no Caddy.
- O `healthcheck` do Compose bate direto no container (`http://localhost:8000/saude`), sem
  passar pelo Caddy.

## 5. CSRF

Implementado em `blatt.web.seguranca.LimiteECsrf`, aplicado a toda rota pela `criar_app`.
Para POST, PUT, PATCH e DELETE:

1. `Sec-Fetch-Site`, se presente, tem de ser `same-origin`;
2. `Origin`, se presente, tem de ter o mesmo `host[:porta]` do `Host` (e não pode ser `null`);
3. o *token* do *cookie* **`__Host-blatt-csrf`** tem de ser igual ao do cabeçalho
   **`X-Blatt-CSRF`** ou ao do campo de formulário **`csrf`** (formulário comum ou
   `multipart/form-data`). A comparação é em tempo constante.

O *cookie* é gravado na primeira resposta que não o encontrar: 32 bytes aleatórios,
`Path=/; Secure; HttpOnly; SameSite=Strict`, com o prefixo `__Host-` (só desta origem). O
mesmo *cookie* vale para todos os módulos da instância, porque o caminho é `/`; nenhum módulo o
sobrescreve se já existir. Não há segredo do servidor nem estado no módulo.

No modelo base, o `<body>` leva `hx-headers='{"X-Blatt-CSRF": "..."}'`, e todo pedido do htmx
já vai com o *token*; formulário comum usa `{{ csrf_campo() }}`. Recusa: `403` com a página de
erro. Atrás do Caddy o navegador vê HTTPS, então o `Secure` funciona; num teste local sem TLS,
use `https://` no cliente de teste (como `tests/test_web.py`).

## 6. Página e cabeçalhos

- Modelo base `blatt/base.html` (blocos `titulo`, `cabeca`, `conteudo`): cabeçalho com a
  navegação entre módulos, usuário, rodapé com "módulo versão · blatt-plataforma versão".
- Navegação: parâmetro `navegacao` da `criar_app` ou, sem ele, a variável
  **`BLATT_WEB_NAVEGACAO`** (`Início=/;Folha=/folha/;Fiscal=/fiscal/`), que o `oper` pode pôr no
  `environment` de cada módulo; sem nenhuma das duas, só o próprio módulo.
- Toda resposta leva `Content-Security-Policy` (`default-src 'self'; script-src 'self';
  style-src 'self'; ...; frame-ancestors 'none'`), `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: no-referrer`; páginas e JSON, `Cache-Control: no-store`. O htmx roda com
  `allowEval: false`, sem script nem estilo em linha. O `Strict-Transport-Security` continua no
  Caddy.
- Páginas de erro (401, 403, 404, 405, 413, 422, 500) no mesmo modelo; nunca mostram o que veio
  no formulário nem o detalhe de um erro interno (que vai para o log `blatt.web`, sem o corpo da
  requisição).

## 7. Upload sensível (A1 e senha)

`blatt.web.formulario.formulario_certificado()` é uma dependência do FastAPI que devolve um
`CertificadoA1` (`conteudo: bytes`, `senha: str`, `nome_arquivo`, `campos`), lido do corpo já em
memória, sem `UploadFile` (que passa por `SpooledTemporaryFile` e vai para disco acima de
1 MiB), com limite de tamanho (64 KiB por padrão) e `repr` que não mostra conteúdo nem senha. A
rota do módulo não declara `File`/`Form`. O teste prova, com um gancho de auditoria do Python
(evento `open`), que um certificado de 1,5 MiB vai ao caso de uso sem nenhuma abertura de
arquivo, e que a senha não aparece em log.
