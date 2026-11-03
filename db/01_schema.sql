-- =====================================================================
-- SOC-Lite · Esquema de base de datos (PostgreSQL 16)
-- Proyecto: Triaje automático de alertas SOC para PYME / mediana empresa
--           / organismo público
-- Autor: Equipo SOC-Lite · Semana 09
-- Requisitos cubiertos: PostgreSQL, RBAC, bitácora de auditoría inmutable,
--                       trazabilidad ISO 27001 A.8.15 / A.5.24 y NIST CSF DE.AE
-- =====================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;      -- gen_random_uuid(), crypt(), digest()
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- búsqueda difusa por título/regla
CREATE EXTENSION IF NOT EXISTS citext;        -- correos sin distinción de mayúsculas
CREATE EXTENSION IF NOT EXISTS btree_gin;     -- índices GIN combinados

-- ---------------------------------------------------------------------
-- 0. Esquemas y tipos
-- ---------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS soc;
SET search_path = soc, public;

CREATE TYPE severity_level AS ENUM ('critical', 'high', 'medium', 'low', 'info');
CREATE TYPE alert_status   AS ENUM ('pending', 'triaged', 'in_review', 'escalated',
                                    'closed', 'suppressed', 'false_positive');
CREATE TYPE triage_verdict AS ENUM ('true_positive', 'suspicious', 'benign', 'false_positive');
CREATE TYPE incident_status AS ENUM ('open', 'investigating', 'contained', 'eradicated',
                                     'recovered', 'closed');
CREATE TYPE report_format  AS ENUM ('pdf', 'docx', 'xlsx');
CREATE TYPE audit_result   AS ENUM ('success', 'denied', 'error');
CREATE TYPE notification_status AS ENUM ('queued', 'sent', 'failed', 'skipped');

-- ---------------------------------------------------------------------
-- 1. RBAC: roles, permisos y asignaciones
-- ---------------------------------------------------------------------
CREATE TABLE roles (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code        VARCHAR(32)  NOT NULL UNIQUE,
    name        VARCHAR(80)  NOT NULL,
    description TEXT,
    is_system   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE permissions (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code        VARCHAR(64)  NOT NULL UNIQUE,   -- ej. alerts:read
    module      VARCHAR(32)  NOT NULL,          -- ej. alerts
    action      VARCHAR(32)  NOT NULL,          -- ej. read
    description TEXT,
    CONSTRAINT permissions_code_ck CHECK (code = module || ':' || action)
);

CREATE TABLE role_permissions (
    role_id       SMALLINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id SMALLINT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT NOT NULL UNIQUE,
    full_name       VARCHAR(120) NOT NULL,
    password_hash   TEXT NOT NULL,
    role_id         SMALLINT NOT NULL REFERENCES roles(id),
    area            VARCHAR(80),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    mfa_enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret      TEXT,
    failed_attempts SMALLINT NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    last_login_at   TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      UUID REFERENCES users(id)
);
CREATE INDEX users_role_idx ON users(role_id) WHERE is_active;

-- Tokens de refresco (rotación y revocación por sesión)
CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,
    ip_address  INET,
    user_agent  TEXT
);
CREATE INDEX refresh_tokens_user_idx ON refresh_tokens(user_id) WHERE revoked_at IS NULL;

-- ---------------------------------------------------------------------
-- 2. Inventario y fuentes de alertas
-- ---------------------------------------------------------------------
CREATE TABLE assets (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(120) NOT NULL,
    hostname      VARCHAR(120),
    ip_address    INET,
    kind          VARCHAR(32) NOT NULL,      -- server, workstation, firewall, switch, cloud, app
    criticality   severity_level NOT NULL DEFAULT 'medium',
    owner_area    VARCHAR(80),
    tags          TEXT[] NOT NULL DEFAULT '{}',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX assets_ip_uk ON assets(ip_address) WHERE ip_address IS NOT NULL;

CREATE TABLE alert_sources (
    id         SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code       VARCHAR(32) NOT NULL UNIQUE,  -- wazuh, opnsense, suricata, manual
    name       VARCHAR(80) NOT NULL,
    kind       VARCHAR(32) NOT NULL,
    endpoint   TEXT,
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    config     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 3. Alertas (tabla de hechos central)
-- ---------------------------------------------------------------------
-- Huella determinista para deduplicación (se usa en la columna generada)
CREATE OR REPLACE FUNCTION fn_alert_fingerprint(
    p_source SMALLINT, p_rule VARCHAR, p_src INET, p_dst INET, p_title VARCHAR)
RETURNS CHAR(64) LANGUAGE sql IMMUTABLE AS $$
    SELECT encode(digest(
        coalesce(p_source::text,'') || '|' || coalesce(p_rule,'') || '|' ||
        coalesce(host(p_src),'')     || '|' || coalesce(host(p_dst),'') || '|' ||
        coalesce(left(p_title,120),''), 'sha256'), 'hex');
$$;

CREATE TABLE alerts (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id      TEXT,                       -- id de la alerta en Wazuh
    source_id        SMALLINT NOT NULL REFERENCES alert_sources(id),
    asset_id         UUID REFERENCES assets(id),
    rule_id          VARCHAR(32),
    rule_level       SMALLINT CHECK (rule_level BETWEEN 0 AND 15),
    severity         severity_level NOT NULL DEFAULT 'medium',
    status           alert_status   NOT NULL DEFAULT 'pending',
    assigned_to      UUID REFERENCES users(id),
    assigned_at      TIMESTAMPTZ,
    title            VARCHAR(240) NOT NULL,
    description      TEXT,
    src_ip           INET,
    dst_ip           INET,
    src_port         INTEGER,
    dst_port         INTEGER,
    protocol         VARCHAR(16),
    username         VARCHAR(80),
    agent_name       VARCHAR(120),
    fingerprint      CHAR(64) GENERATED ALWAYS AS (
                         fn_alert_fingerprint(source_id, rule_id, src_ip, dst_ip, title)
                     ) STORED,
    dedup_count      INTEGER NOT NULL DEFAULT 1,
    first_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload      JSONB NOT NULL DEFAULT '{}'::jsonb,
    mitre_tactic     VARCHAR(80),
    mitre_technique  VARCHAR(16),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT alerts_dedup_uk UNIQUE (source_id, fingerprint),
    CONSTRAINT alerts_ports_ck CHECK (
        (src_port IS NULL OR src_port BETWEEN 0 AND 65535) AND
        (dst_port IS NULL OR dst_port BETWEEN 0 AND 65535))
);

-- Consulta principal del dashboard: alertas abiertas por severidad y fecha
CREATE INDEX alerts_status_sev_created_idx ON alerts(status, severity, created_at DESC);
CREATE INDEX alerts_created_brin ON alerts USING brin(created_at) WITH (pages_per_range = 32);
CREATE INDEX alerts_src_ip_idx ON alerts(src_ip);
CREATE INDEX alerts_asset_idx ON alerts(asset_id, created_at DESC);
CREATE INDEX alerts_rule_idx ON alerts(rule_id);
CREATE INDEX alerts_payload_gin ON alerts USING gin(raw_payload jsonb_path_ops);
CREATE INDEX alerts_title_trgm ON alerts USING gin(title gin_trgm_ops);
CREATE INDEX alerts_open_idx ON alerts(severity, last_seen_at DESC)
    WHERE status IN ('pending', 'triaged', 'in_review', 'escalated');

-- Reglas de supresión / tuning (reducen falsos positivos recurrentes)
CREATE TABLE suppression_rules (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(120) NOT NULL,
    description TEXT,
    match_expr  JSONB NOT NULL,     -- {"rule_id":"5710","src_ip":"10.0.0.0/8"}
    reason      VARCHAR(240) NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at  TIMESTAMPTZ,
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX suppression_active_idx ON suppression_rules(is_active) WHERE is_active;

-- ---------------------------------------------------------------------
-- 4. Enriquecimiento y triaje
-- ---------------------------------------------------------------------
CREATE TABLE enrichment_data (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_id       UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    provider       VARCHAR(32) NOT NULL,     -- virustotal, abuseipdb, geoip, mitre, nvd, wazuh
    indicator      TEXT NOT NULL,
    indicator_type VARCHAR(16) NOT NULL,     -- ip, domain, url, hash, cve, user
    verdict        VARCHAR(32),              -- malicious, suspicious, clean, unknown
    score          NUMERIC(5,2),             -- 0..100 normalizado
    raw            JSONB NOT NULL DEFAULT '{}'::jsonb,
    ttl_expires_at TIMESTAMPTZ,
    fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    error          TEXT,
    CONSTRAINT enrichment_provider_ind_uk UNIQUE (alert_id, provider, indicator)
);
CREATE INDEX enrichment_alert_idx ON enrichment_data(alert_id);

CREATE TABLE triage_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id            UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    engine              VARCHAR(32) NOT NULL DEFAULT 'langchain',
    model               VARCHAR(64) NOT NULL,             -- llama3.1:8b, gpt-4o-mini...
    prompt_version      VARCHAR(16) NOT NULL DEFAULT 'v1.2',
    suggested_severity  severity_level NOT NULL,
    verdict             triage_verdict NOT NULL,
    confidence          NUMERIC(4,3) CHECK (confidence BETWEEN 0 AND 1),
    summary             TEXT NOT NULL,
    recommended_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    mitre_techniques    TEXT[] NOT NULL DEFAULT '{}',
    evidence            JSONB NOT NULL DEFAULT '{}'::jsonb,
    tokens_in           INTEGER,
    tokens_out          INTEGER,
    latency_ms          INTEGER,
    cost_usd            NUMERIC(10,6),
    needs_human_review  BOOLEAN NOT NULL DEFAULT FALSE,
    human_verdict       triage_verdict,
    reviewed_by         UUID REFERENCES users(id),
    reviewed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT triage_confidence_ck CHECK (confidence IS NULL OR confidence <= 1)
);
CREATE INDEX triage_alert_idx ON triage_results(alert_id, created_at DESC);
CREATE INDEX triage_review_idx ON triage_results(needs_human_review) WHERE needs_human_review;
CREATE INDEX triage_verdict_idx ON triage_results(verdict, created_at DESC);

-- ---------------------------------------------------------------------
-- 5. Incidentes y SLA
-- ---------------------------------------------------------------------
CREATE TABLE sla_policies (
    severity        severity_level PRIMARY KEY,
    ack_minutes     INTEGER NOT NULL,
    resolve_minutes INTEGER NOT NULL,
    notify_channel  VARCHAR(32) NOT NULL DEFAULT 'slack'
);

CREATE TABLE incidents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(24) NOT NULL UNIQUE,       -- INC-2026-00042
    title       VARCHAR(240) NOT NULL,
    severity    severity_level NOT NULL,
    status      incident_status NOT NULL DEFAULT 'open',
    asset_id    UUID REFERENCES assets(id),
    assigned_to UUID REFERENCES users(id),
    sla_due_at  TIMESTAMPTZ NOT NULL,
    opened_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at   TIMESTAMPTZ,
    resolution  TEXT,
    ticket_system VARCHAR(32),
    ticket_ref  VARCHAR(64),
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX incidents_status_idx ON incidents(status, sla_due_at);
CREATE INDEX incidents_assignee_idx ON incidents(assigned_to) WHERE status <> 'closed';

CREATE TABLE incident_alerts (
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    alert_id    UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    linked_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (incident_id, alert_id)
);

-- ---------------------------------------------------------------------
-- 6. Notificaciones y reportes
-- ---------------------------------------------------------------------
CREATE TABLE notifications (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_id    UUID REFERENCES alerts(id) ON DELETE SET NULL,
    incident_id UUID REFERENCES incidents(id) ON DELETE SET NULL,
    channel     VARCHAR(32) NOT NULL,   -- slack, telegram, email, teams
    target      TEXT NOT NULL,
    subject     TEXT,
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    status      notification_status NOT NULL DEFAULT 'queued',
    attempts    SMALLINT NOT NULL DEFAULT 0,
    sent_at     TIMESTAMPTZ,
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reports (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code         VARCHAR(24) NOT NULL UNIQUE,      -- RPT-2026-0007
    title        VARCHAR(160) NOT NULL,
    kind         VARCHAR(32) NOT NULL,             -- operational, management, executive
    format       report_format NOT NULL,
    period_start DATE NOT NULL,
    period_end   DATE NOT NULL,
    filters      JSONB NOT NULL DEFAULT '{}'::jsonb,
    file_path    TEXT,
    file_size    BIGINT,
    checksum     CHAR(64),
    status       VARCHAR(16) NOT NULL DEFAULT 'pending',
    generated_by UUID REFERENCES users(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX reports_created_idx ON reports(created_at DESC);

-- ---------------------------------------------------------------------
-- 7. Bitácora de auditoría (append-only, encadenada por hash)
-- ---------------------------------------------------------------------
CREATE TABLE audit_log (
    id          BIGINT GENERATED ALWAYS AS IDENTITY,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    user_id     UUID,
    user_email  CITEXT,
    role_code   VARCHAR(32),
    action      VARCHAR(64) NOT NULL,     -- login, logout, alerts.read, alerts.update...
    module      VARCHAR(32) NOT NULL,
    entity      VARCHAR(48),
    entity_id   TEXT,
    result      audit_result NOT NULL DEFAULT 'success',
    ip_address  INET,
    user_agent  TEXT,
    request_id  UUID,
    detail      JSONB NOT NULL DEFAULT '{}'::jsonb,
    prev_hash   CHAR(64),
    row_hash    CHAR(64),
    PRIMARY KEY (id, occurred_at)
) PARTITION BY RANGE (occurred_at);

-- Particiones mensuales (2026). Un job pg_partman/cron crea las siguientes.
CREATE TABLE audit_log_2026_01 PARTITION OF audit_log
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE audit_log_2026_02 PARTITION OF audit_log
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE audit_log_2026_03 PARTITION OF audit_log
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE audit_log_default PARTITION OF audit_log DEFAULT;

CREATE INDEX audit_log_occurred_idx ON audit_log(occurred_at DESC);
CREATE INDEX audit_log_user_idx ON audit_log(user_id, occurred_at DESC);
CREATE INDEX audit_log_module_idx ON audit_log(module, occurred_at DESC);
CREATE INDEX audit_log_entity_idx ON audit_log(entity, entity_id);

-- ---------------------------------------------------------------------
-- 8. Funciones y disparadores
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_users_updated     BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_assets_updated    BEFORE UPDATE ON assets
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_alerts_updated    BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_incidents_updated BEFORE UPDATE ON incidents
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- Encadenamiento de hashes de la bitácora (integridad tipo blockchain ligera)
CREATE OR REPLACE FUNCTION fn_audit_hash_chain() RETURNS trigger
LANGUAGE plpgsql SET search_path = soc, public AS $$
DECLARE
    v_prev CHAR(64);
BEGIN
    SELECT row_hash INTO v_prev
      FROM soc.audit_log
     WHERE occurred_at <= NEW.occurred_at
     ORDER BY occurred_at DESC, id DESC
     LIMIT 1;

    NEW.prev_hash := v_prev;
    NEW.row_hash  := encode(digest(
        coalesce(v_prev,'') || '|' || NEW.occurred_at::text || '|' ||
        coalesce(NEW.user_email::text,'') || '|' || NEW.action || '|' ||
        coalesce(NEW.entity,'') || '|' || coalesce(NEW.entity_id,'') || '|' ||
        coalesce(NEW.detail::text,'{}'), 'sha256'), 'hex');
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_audit_hash BEFORE INSERT ON audit_log
    FOR EACH ROW EXECUTE FUNCTION fn_audit_hash_chain();

-- Inmutabilidad: prohibido UPDATE/DELETE sobre la bitácora
CREATE OR REPLACE FUNCTION fn_audit_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_log es append-only: operación % no permitida', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$;

CREATE TRIGGER trg_audit_no_update BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION fn_audit_immutable();

-- Verificación de la cadena de integridad (para informe de auditoría)
CREATE OR REPLACE FUNCTION fn_verify_audit_chain(p_from TIMESTAMPTZ, p_to TIMESTAMPTZ)
RETURNS TABLE (total BIGINT, broken BIGINT)
LANGUAGE sql STABLE SET search_path = soc, public AS $$
    WITH ordered AS (
        SELECT id, occurred_at, prev_hash, row_hash,
               lag(row_hash) OVER (ORDER BY occurred_at, id) AS expected_prev
          FROM soc.audit_log
         WHERE occurred_at BETWEEN p_from AND p_to
    )
    SELECT count(*),
           count(*) FILTER (WHERE prev_hash IS DISTINCT FROM expected_prev)
      FROM ordered;
$$;

-- Apertura automática de incidente + SLA a partir de un triaje de severidad alta
CREATE OR REPLACE FUNCTION fn_open_incident(p_alert UUID, p_user UUID DEFAULT NULL)
RETURNS UUID LANGUAGE plpgsql SET search_path = soc, public AS $$
DECLARE
    v_alert   alerts%ROWTYPE;
    v_sla     sla_policies%ROWTYPE;
    v_inc     UUID;
    v_seq     INTEGER;
    v_code    VARCHAR(24);
BEGIN
    SELECT * INTO v_alert FROM soc.alerts WHERE id = p_alert FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'alerta % inexistente', p_alert; END IF;

    SELECT * INTO v_sla FROM soc.sla_policies WHERE severity = v_alert.severity;

    SELECT count(*) + 1 INTO v_seq
      FROM soc.incidents WHERE date_part('year', opened_at) = date_part('year', now());
    v_code := format('INC-%s-%s', date_part('year', now())::int, lpad(v_seq::text, 5, '0'));

    INSERT INTO soc.incidents (code, title, severity, asset_id, sla_due_at, created_by)
    VALUES (v_code, left(v_alert.title, 240), v_alert.severity, v_alert.asset_id,
            now() + make_interval(mins => coalesce(v_sla.resolve_minutes, 240)), p_user)
    RETURNING id INTO v_inc;

    INSERT INTO soc.incident_alerts(incident_id, alert_id) VALUES (v_inc, p_alert);
    UPDATE soc.alerts SET status = 'escalated' WHERE id = p_alert;
    RETURN v_inc;
END;
$$;

-- Actualización idempotente de métricas diarias
CREATE TABLE metrics_daily (
    day             DATE PRIMARY KEY,
    alerts_total    INTEGER NOT NULL DEFAULT 0,
    alerts_critical INTEGER NOT NULL DEFAULT 0,
    alerts_high     INTEGER NOT NULL DEFAULT 0,
    true_positive   INTEGER NOT NULL DEFAULT 0,
    false_positive  INTEGER NOT NULL DEFAULT 0,
    auto_triaged    INTEGER NOT NULL DEFAULT 0,
    avg_triage_ms   NUMERIC(10,2),
    mttt_minutes    NUMERIC(10,2),
    mttr_minutes    NUMERIC(10,2),
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Cada KPI se calcula con una subconsulta independiente para evitar la
-- multiplicación de filas que producirían los JOIN sobre triaje e incidentes.
CREATE OR REPLACE FUNCTION fn_refresh_metrics(p_day DATE DEFAULT CURRENT_DATE - 1)
RETURNS void LANGUAGE sql SET search_path = soc, public AS $$
    INSERT INTO metrics_daily AS m (day, alerts_total, alerts_critical, alerts_high,
                                    true_positive, false_positive, auto_triaged,
                                    avg_triage_ms, mttt_minutes, mttr_minutes, computed_at)
    SELECT p_day,
           (SELECT count(*) FROM soc.alerts WHERE created_at::date = p_day),
           (SELECT count(*) FROM soc.alerts WHERE created_at::date = p_day AND severity = 'critical'),
           (SELECT count(*) FROM soc.alerts WHERE created_at::date = p_day AND severity = 'high'),
           (SELECT count(*) FROM soc.triage_results
             WHERE created_at::date = p_day AND verdict = 'true_positive'),
           (SELECT count(*) FROM soc.triage_results
             WHERE created_at::date = p_day AND verdict = 'false_positive'),
           (SELECT count(*) FROM soc.triage_results WHERE created_at::date = p_day),
           (SELECT avg(latency_ms) FROM soc.triage_results WHERE created_at::date = p_day),
           (SELECT avg(EXTRACT(EPOCH FROM (t.created_at - a.created_at)) / 60.0)
              FROM soc.triage_results t JOIN soc.alerts a ON a.id = t.alert_id
             WHERE t.created_at::date = p_day),
           (SELECT avg(EXTRACT(EPOCH FROM (closed_at - opened_at)) / 60.0)
              FROM soc.incidents WHERE closed_at::date = p_day),
           now()
    ON CONFLICT (day) DO UPDATE
       SET alerts_total    = EXCLUDED.alerts_total,
           alerts_critical = EXCLUDED.alerts_critical,
           alerts_high     = EXCLUDED.alerts_high,
           true_positive   = EXCLUDED.true_positive,
           false_positive  = EXCLUDED.false_positive,
           auto_triaged    = EXCLUDED.auto_triaged,
           avg_triage_ms   = EXCLUDED.avg_triage_ms,
           mttt_minutes    = EXCLUDED.mttt_minutes,
           mttr_minutes    = EXCLUDED.mttr_minutes,
           computed_at     = now();
$$;

-- ---------------------------------------------------------------------
-- 9. Vistas para dashboard y reportes
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_alert_overview AS
SELECT a.id, a.created_at, a.title, a.severity, a.status, a.rule_id, a.rule_level,
       a.src_ip, a.dst_ip, a.agent_name, s.code AS source_code,
       t.verdict, t.confidence, t.summary,
       (t.needs_human_review AND t.reviewed_at IS NULL) AS pending_review,
       i.code AS incident_code,
       EXTRACT(EPOCH FROM (now() - a.created_at)) / 60.0 AS age_minutes
  FROM alerts a
  JOIN alert_sources s ON s.id = a.source_id
  LEFT JOIN LATERAL (
        SELECT * FROM triage_results tr
         WHERE tr.alert_id = a.id ORDER BY tr.created_at DESC LIMIT 1) t ON TRUE
  LEFT JOIN incident_alerts ia ON ia.alert_id = a.id
  LEFT JOIN incidents i ON i.id = ia.incident_id;

CREATE OR REPLACE VIEW v_kpi_current AS
SELECT
    (SELECT count(*) FROM alerts WHERE status IN ('pending','triaged','in_review','escalated')) AS open_alerts,
    (SELECT count(*) FROM alerts WHERE severity = 'critical'
        AND status IN ('pending','triaged','in_review','escalated')) AS open_critical,
    (SELECT round(avg(EXTRACT(EPOCH FROM (t.created_at - a.created_at)) / 60.0)::numeric, 2)
       FROM triage_results t JOIN alerts a ON a.id = t.alert_id
      WHERE t.created_at > now() - interval '7 days') AS mttt_minutes_7d,
    (SELECT round(100.0 * count(*) FILTER (WHERE t.verdict = 'false_positive') / greatest(count(*),1), 2)
       FROM triage_results t WHERE t.created_at > now() - interval '7 days') AS fp_rate_7d,
    (SELECT round(avg(t.confidence)::numeric, 3) FROM triage_results t
      WHERE t.created_at > now() - interval '7 days') AS avg_confidence_7d,
    (SELECT count(*) FROM incidents WHERE status <> 'closed' AND sla_due_at < now()) AS sla_breached;

-- ---------------------------------------------------------------------
-- 10. Seguridad a nivel de fila (defensa en profundidad)
-- ---------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'soc_app') THEN
        CREATE ROLE soc_app NOLOGIN;
    END IF;
END;
$$;

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS audit_read_all ON audit_log;
CREATE POLICY audit_read_all ON audit_log FOR SELECT USING (TRUE);
DROP POLICY IF EXISTS audit_insert_all ON audit_log;
CREATE POLICY audit_insert_all ON audit_log FOR INSERT WITH CHECK (TRUE);

-- El rol de aplicación solo inserta y lee; UPDATE/DELETE quedan bloqueados
-- por el trigger de inmutabilidad y por ausencia de GRANT.
GRANT USAGE ON SCHEMA soc TO soc_app;
GRANT SELECT, INSERT ON audit_log TO soc_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA soc TO soc_app;
REVOKE UPDATE, DELETE ON audit_log FROM soc_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA soc TO soc_app;

COMMIT;

