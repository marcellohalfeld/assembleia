-- Migração fictícia, só para os testes do executor.
CREATE TABLE exemplo (
    tenant_id uuid NOT NULL,
    id uuid NOT NULL,
    PRIMARY KEY (tenant_id, id)
);
