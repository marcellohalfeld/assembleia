# `blatt.comum`: fonte canônica

Tipos sem regra de negócio de nenhum módulo, usados por mais de um (resumo, seção 7):
`AnoMes` (`periodo.py`), validação de CPF e CNPJ, inclusive alfanumérico (`documentos.py`), e
regras de texto do eSocial (`texto.py`).

- **Origem:** `marcellohalfeld/blatt`, `src/blatt/comum`, commit `2bcff8e`; idêntico à cópia do
  aspirador em 03/11/2026 (conferido por hash).
- **Manifesto:** `MANIFESTO.json`, SHA-256 de cada arquivo.
- **Testes:** continuam na folha, que exercita estes tipos; ainda não há testes próprios aqui.
- **Distribuição:** cópia nos módulos, conferida com `python scripts/conferir_comum.py
  <raiz do módulo>`. Empacotamento em aberto (pendência A-03).

Mudança aqui primeiro; depois `python scripts/conferir_comum.py --atualizar`; depois a cópia
nos módulos.
