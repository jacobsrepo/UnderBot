CREATE TABLE IF NOT EXISTS people (
 id uuid PRIMARY KEY, name text NOT NULL CHECK (length(name) BETWEEN 1 AND 120),
 active boolean NOT NULL DEFAULT true, updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS faces (
 id uuid PRIMARY KEY, person_id uuid NOT NULL REFERENCES people(id) ON DELETE CASCADE,
 model text NOT NULL, embedding real[] NOT NULL CHECK (cardinality(embedding)=128),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS observations (
 id uuid PRIMARY KEY, robot_id text NOT NULL, captured_at timestamptz NOT NULL,
 payload jsonb NOT NULL, uploaded boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS observations_pending ON observations(created_at) WHERE NOT uploaded;
CREATE TABLE IF NOT EXISTS memory_state (key text PRIMARY KEY, value timestamptz NOT NULL);
