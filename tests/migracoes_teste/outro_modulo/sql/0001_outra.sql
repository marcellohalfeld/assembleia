-- Migração fictícia de um segundo módulo, com banco próprio.
CREATE TABLE outra (tenant_id uuid NOT NULL, id uuid NOT NULL, PRIMARY KEY (tenant_id, id));
