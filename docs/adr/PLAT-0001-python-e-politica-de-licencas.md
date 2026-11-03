# PLAT-0001: Python e política de licenças

> Transferida de `marcellohalfeld/blatt` (`docs/adr/0001-python-e-politica-de-licencas.md`, commit `2bcff8e`) em 2026-11-03, pela [PLAT-0015](PLAT-0015-governanca-no-assembleia.md). Texto sem alteração, salvo o título e os links, que passaram a apontar para cá ou para o repositório da folha. Nas referências do texto, "ADR NNNN" é o número de origem: ver a tabela de correspondência no [README](README.md).

- **Status:** Proposta
- **Data:** 2026-10-20
- **Decisor:** Marcello

## Contexto

O Marcello domina Python e aceita outra linguagem só se houver justificativa forte. O produto
precisa de aritmética decimal exata, manipulação de XML com validação XSD, assinatura XML-DSig
e cliente SOAP. Na escala de MPE não há exigência de desempenho que justifique outra linguagem.

A premissa do projeto é não depender de nenhum fornecedor: só software livre, e partes
substituíveis. Mas o open source também aprisiona, de dois jeitos:

1. **Licença incompatível com o modelo de negócio.** A AGPL estende as obrigações da GPL ao
   uso pela rede: quem oferece o software modificado como serviço precisa disponibilizar o
   código-fonte aos usuários ([FOSSA](https://fossa.com/blog/open-source-software-licenses-101-agpl-license/)).
   A GPL comum não tem essa cláusula, mas aqui a distinção importa pouco: o modelo de "uma
   instância por escritório" (ADR 0004) pode significar instalar o sistema no servidor do
   cliente, o que é distribuição e aciona a GPL.
2. **Licença que muda.** A HashiCorp trocou a licença do Vault de MPL 2.0 para a Business
   Source License em 2023; a comunidade respondeu com o fork OpenBao
   ([The New Stack](https://thenewstack.io/meet-openbao-an-open-source-fork-of-hashicorp-vault/)).
   O MinIO, que era Apache 2.0, passou inteiramente para AGPLv3 em 2021
   ([MinIO](https://blog.min.io/from-open-source-to-free-and-open-source-minio-is-now-fully-licensed-under-gnu-agplv3)).

## Decisão

1. **Linguagem:** Python ≥ 3.12, com tipagem estrita (`mypy --strict`). Gerenciador de
   projeto: `uv`.
2. **Licenças permitidas** para dependências, sem consulta: MIT, BSD (2 e 3 cláusulas),
   Apache-2.0, ISC, PSF, MPL-2.0 (copyleft por arquivo, aceitável enquanto não modificarmos
   os arquivos da biblioteca), PostgreSQL License.
3. **Exigem ADR específica:** LGPL (aceitável em princípio como biblioteca dinâmica, mas
   avaliar caso a caso).
4. **Proibidas:** GPL, AGPL, SSPL, Business Source License, licenças "source available" e
   qualquer componente proprietário.
5. **Critério de desempate:** entre opções equivalentes, preferir projeto com governança em
   fundação (Linux Foundation, Apache, PSF, OpenSSF) ou com múltiplos mantenedores ativos.
6. **Verificação automática:** o CI roda `pip-licenses` e falha se aparecer GPL/AGPL. Como a
   busca é por substring, LGPL também dispara a falha — o que é intencional, porque LGPL exige
   ADR (item 3).
7. **Adaptadores** (ADR 0002) isolam toda dependência externa relevante, para que uma troca de
   licença no futuro custe a troca de um adaptador, não do sistema.

## Questão em aberto: licença do próprio Blatt

Até aqui decidimos o que o Blatt **usa**, não como ele é **licenciado**. Opções:

| Opção | Efeito |
| --- | --- |
| Fechado (sem licença) | Todos os direitos reservados; máximo controle comercial |
| MIT/Apache-2.0 | Qualquer um pode usar, inclusive concorrentes, sem devolver melhorias |
| AGPL-3.0 | Código aberto, mas quem oferecer como serviço precisa abrir suas modificações; protege contra concorrente que "pega e vende", e é compatível com venda de licença comercial separada |

Decisão pendente do Marcello. Enquanto não houver `LICENSE`, o código fica fechado. A escolha
não afeta as dependências: todas as permitidas no item 2 são compatíveis com qualquer uma das
três opções.

## Consequências

- Restringe algumas bibliotecas do ecossistema brasileiro de ERP que são AGPL; podem servir
  de referência de estudo, mas não de dependência nem de origem de código copiado.
- A checagem de licenças no CI torna a política verificável, não só declarada.

## Referências

- [FOSSA — AGPL license 101](https://fossa.com/blog/open-source-software-licenses-101-agpl-license/)
- [The New Stack — OpenBao, fork do Vault](https://thenewstack.io/meet-openbao-an-open-source-fork-of-hashicorp-vault/)
- [MinIO — mudança para AGPLv3](https://blog.min.io/from-open-source-to-free-and-open-source-minio-is-now-fully-licensed-under-gnu-agplv3)
