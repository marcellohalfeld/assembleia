# Arquivos estáticos da base web

Servidos pela própria aplicação do módulo em `<prefixo>/_blatt/` (sem CDN; PLAT-0021, item 5).

| Arquivo | O que é |
| --- | --- |
| `blatt.css` | Folha de estilo da base, sem framework externo. |
| `htmx.min.js` | htmx 2.0.11, sem alteração. |
| `htmx.LICENSE.txt` | Licença do htmx (0BSD), copiada do pacote. |

## htmx

- **Versão:** 2.0.11 (`latest` no npm em 13/11/2026; a 4.0.1 é `next`), a mesma da PLAT-0021.
- **Origem:** pacote npm oficial `htmx.org`,
  `https://registry.npmjs.org/htmx.org/-/htmx.org-2.0.11.tgz`, arquivo `package/dist/htmx.min.js`.
- **Conferência do pacote (13/11/2026):** a integridade publicada no registro
  (`sha512-Thx/WtpeOQqSrqBCw/A1cwGJGg4UrVa3+sW0GmrM3p4gJgO89ecH4qtbnyzDDWFvBTqjnIMCgELTNt636dtamA==`,
  `shasum` `a85363c4c5af94cd634df04c4b83d06dd0e91aa7`) bate com o `.tgz` baixado
  (SHA-256 do `.tgz`: `165a2655073e9e6e55e307a7c74e8ebcdb76afb7701f9c16cfd106a13add408e`).
- **SHA-256 de `htmx.min.js`:** `d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717`
  (52.182 bytes). O teste `tests/test_web.py` confere este hash.
- **Licença:** 0BSD (`package/LICENSE`, copiado em `htmx.LICENSE.txt`; campo `license` do
  `package.json`), aceita como permissiva pelo Marcello em 12/11/2026 (A-13).
- **Configuração:** o modelo base liga o htmx com `allowEval: false`, `allowScriptTags: false` e
  `includeIndicatorStyles: false`, para funcionar com a política de conteúdo sem script nem
  estilo em linha.

Trocar de versão: baixar o `.tgz` do registro, conferir a integridade publicada, copiar
`package/dist/htmx.min.js` e `package/LICENSE`, atualizar esta tabela e o hash no teste.
