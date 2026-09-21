-- ============================================================
-- Migración: catálogo de PLANES + gating (Fase 1, item 2).
-- `planes` es un catálogo GLOBAL (no por taller, sin RLS). `talleres.plan_tal`
-- referencia el nombre del plan cuando el taller está 'activo' (pagó).
-- Durante 'prueba' (trial vigente) el taller tiene todas las features.
-- Idempotente. Correr como el rol DUEÑO de las tablas (mt_app local).
-- ============================================================

BEGIN;

CREATE SEQUENCE IF NOT EXISTS seq_planes START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;

CREATE TABLE IF NOT EXISTS planes (
    cod_plan     INTEGER      NOT NULL DEFAULT nextval('seq_planes'),
    nombre_plan  VARCHAR(50)  NOT NULL,
    precio_plan  INTEGER      NOT NULL DEFAULT 0,   -- COP / mes
    max_usuarios INTEGER,                            -- NULL = ilimitado
    max_motos    INTEGER,                            -- NULL = ilimitado
    features     JSONB        NOT NULL DEFAULT '{}', -- flags: {"reportes": true, ...}
    orden        INTEGER      NOT NULL DEFAULT 0,
    CONSTRAINT pk_planes PRIMARY KEY (cod_plan),
    CONSTRAINT ux_planes_nombre UNIQUE (nombre_plan)
);
-- planes es catálogo global de la plataforma: NO lleva RLS.

INSERT INTO planes (nombre_plan, precio_plan, max_usuarios, max_motos, features, orden) VALUES
    ('Prueba',       0,     3,    NULL, '{"reportes": true}', 1),
    ('Profesional',  49000, NULL, NULL, '{"reportes": true}', 2),
    ('Premium',      99000, NULL, NULL, '{"reportes": true, "multi_sucursal": true}', 3)
ON CONFLICT (nombre_plan) DO NOTHING;

-- El taller demo (activo) queda en Premium para tener todas las features.
UPDATE talleres SET plan_tal = 'Premium'
 WHERE estado_tal = 'activo' AND (plan_tal IS NULL OR plan_tal = '');

COMMIT;
