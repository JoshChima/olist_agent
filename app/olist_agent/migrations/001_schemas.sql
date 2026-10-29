-- Every migration is idempotent: the loader applies them all, in file-name order, on every
-- run that has work to do. A changed migration changes their hash and forces a reload.

-- What the loader last loaded. The hash pair decides whether a run has anything to do.
CREATE SCHEMA IF NOT EXISTS loader;
CREATE TABLE IF NOT EXISTS loader.state (
    id boolean PRIMARY KEY DEFAULT true CHECK (id),  -- one row
    source_sha256 text NOT NULL,
    migrations_sha256 text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

-- raw holds the source data; no app role can read it (ADR-0008).
CREATE SCHEMA IF NOT EXISTS raw;

-- sim is all the app can see. Its login role is made a member of sim_reader by the loader.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sim_reader') THEN
        CREATE ROLE sim_reader NOLOGIN;
    END IF;
END $$;
CREATE SCHEMA IF NOT EXISTS sim;
GRANT USAGE ON SCHEMA sim TO sim_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA sim GRANT SELECT ON TABLES TO sim_reader;

-- The data-status endpoint's source. Views run as their owner, so sim_reader needs no
-- access to loader.
CREATE OR REPLACE VIEW sim.data_status AS SELECT source_sha256, loaded_at FROM loader.state;
