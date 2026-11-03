-- =====================================================================
-- Inicialización del clúster: rol de aplicación y base de datos de n8n.
-- Se ejecuta antes que 01_schema.sql (orden alfabético).
-- =====================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'soc_app') THEN
        CREATE ROLE soc_app LOGIN PASSWORD 'soc_app';
    END IF;
END;
$$;

SELECT 'CREATE DATABASE n8n OWNER soc_admin'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'n8n')\gexec

GRANT CONNECT ON DATABASE soclite TO soc_app;
