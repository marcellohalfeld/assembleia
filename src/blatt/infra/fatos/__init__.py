"""Integração por fatos (PLAT-0019): envelope, SQL da ``outbox``/``inbox``/``entrega_cursor``,
DDL de referência para as migrações dos módulos e a entrega usada pelo entregador do ``oper``.

- ``envelope``: ``Envelope``, ``texto_decimal``, ``ErroEnvelope``;
- ``postgres``: ``gravar_na_outbox``, ``ler_outbox``, ``inserir_na_inbox``,
  ``proximos_da_inbox``, ``marcar_processado``, ``ler_cursor``, ``avancar_cursor``;
- ``ddl``: ``ddl_outbox(origem)``, ``ddl_inbox()``, ``ddl_entrega_cursor()``,
  ``ddl_consumidor()``;
- ``entrega``: ``Inscricao``, ``entregar``, ``ResultadoEntrega``, ``ErroOrigemRestaurada``.

Sem regra de negócio: nenhum tipo de fato de módulo é conhecido aqui.
"""
