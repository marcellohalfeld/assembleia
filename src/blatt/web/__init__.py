"""Base da interface web dos módulos (PLAT-0021, itens 5 a 7), no extra ``[web]``.

- ``app``: ``criar_app`` e ``renderizar`` (FastAPI + Jinja2), modelo base, estilo, htmx;
- ``seguranca``: identidade pelo cabeçalho do Caddy, CSRF e limite do corpo;
- ``formulario``: certificado A1 e senha lidos só em memória;
- ``apresentacao``: moeda, datas, competência, CNPJ e CPF (só biblioteca padrão).

Este ``__init__`` não importa nada: ``blatt.web.apresentacao`` funciona sem o extra ``[web]``.
Contrato com o portal e o Caddy: ``docs/contratos/web.md`` do ``assembleia``.
"""
