-- Carga el esquema multi-tenant COMO mt_app (para que las tablas sean suyas y el
-- RLS FORCE aplique). El archivo se monta en /schema.sql desde docker-compose.
SET ROLE mt_app;
\i /schema.sql
