CREATE TABLE tenant (
    id text PRIMARY KEY CHECK (length(trim(id)) > 0)
);
CREATE TABLE membership (
    tenant_id text NOT NULL REFERENCES tenant(id),
    subject text NOT NULL CHECK (length(trim(subject)) > 0),
    active boolean NOT NULL DEFAULT true,
    PRIMARY KEY (tenant_id, subject)
);
CREATE TABLE plant (
    public_id text PRIMARY KEY CHECK (length(trim(public_id)) > 0),
    tenant_id text NOT NULL REFERENCES tenant(id),
    name text NOT NULL CHECK (length(trim(name)) > 0),
    capacity_kw double precision CHECK (
        capacity_kw >= 0 AND capacity_kw < 'Infinity'::double precision
    ),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX plant_tenant_public_id ON plant (tenant_id, public_id COLLATE "C");
