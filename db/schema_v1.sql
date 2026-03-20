-- Sketch-to-Cloud PostgreSQL schema v1
-- Contract alignment:
-- - session status: created | analyzing | generated | failed
-- - architecture JSON matches A_JSON_스키마_v1.json
-- - timestamps stored in UTC-capable timestamptz

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    owner_id VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_no INT NOT NULL CHECK (version_no > 0),
    input_type VARCHAR(20) NOT NULL DEFAULT 'TEXT' CHECK (input_type IN ('TEXT', 'SKETCH', 'TEXT_WITH_SKETCH')),
    input_text TEXT,
    input_image_url TEXT,
    status VARCHAR(30) NOT NULL CHECK (
        status IN (
            'CREATED',
            'ANALYZING',
            'ANALYZED',
            'GENERATING_TERRAFORM',
            'GENERATED',
            'COST_CALCULATED',
            'FAILED'
        )
    ),
    error_code VARCHAR(50),
    error_message TEXT,
    contract_version VARCHAR(20) NOT NULL DEFAULT 'v1' CHECK (contract_version = 'v1'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, version_no)
);

CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);

CREATE TABLE IF NOT EXISTS session_architectures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    schema_version VARCHAR(20) NOT NULL DEFAULT 'v1',
    architecture_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_session_architectures_json ON session_architectures USING GIN (architecture_json);

CREATE TABLE IF NOT EXISTS session_terraform_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    terraform_code TEXT NOT NULL,
    validation_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (validation_status IN ('PENDING', 'PASSED', 'FAILED')),
    validation_output TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS session_cost_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    currency VARCHAR(10) NOT NULL DEFAULT 'KRW',
    region VARCHAR(30) NOT NULL,
    assumption_json JSONB NOT NULL,
    monthly_total NUMERIC(12, 2) NOT NULL CHECK (monthly_total >= 0),
    cost_breakdown_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_session_cost_results_region ON session_cost_results(region);

CREATE TABLE IF NOT EXISTS session_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    event_type VARCHAR(40) NOT NULL,
    payload_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_session_events_session_id ON session_events(session_id);
CREATE INDEX IF NOT EXISTS idx_session_events_event_type ON session_events(event_type);

COMMIT;

