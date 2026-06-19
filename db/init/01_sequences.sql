-- ============================================================
-- 01_sequences.sql
-- Secuencias (migradas de Oracle ScriptSequencias.sql)
-- En Postgres alimentan el DEFAULT de cada PK autogenerada.
-- ============================================================

CREATE SEQUENCE seq_impuestos            START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_marcas               START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_perfiles             START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_permisos             START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_productos            START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_productos_impuestos  START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_reclamos             START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_roles                START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
