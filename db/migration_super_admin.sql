-- F0-14: super-admin de plataforma explícito (ya no depende de cod_taller=1).
-- Aplicar a mano en la BD de producción (igual que migration_timezone_bogota.sql).
-- CI/fresh DBs ya tienen esto en full_schema_v2_multitenant.sql -- este archivo es
-- solo la versión incremental para una BD ya desplegada.

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS es_super_admin BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ultimo_ingreso_usu TIMESTAMP;

-- Preserva el acceso de quien hoy es "super-admin" bajo el significado viejo
-- (Admin del taller plataforma, cod_taller=1) para no perder acceso al desplegar.
UPDATE usuarios SET es_super_admin = true WHERE cod_taller = 1 AND cod_rol_prf_usu = 1;

ALTER TABLE pagos ADD COLUMN IF NOT EXISTS medio VARCHAR(10) NOT NULL DEFAULT 'WOMPI';
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS detalle_medio VARCHAR(50);
ALTER TABLE pagos DROP CONSTRAINT IF EXISTS chk_pagos_medio;
ALTER TABLE pagos ADD CONSTRAINT chk_pagos_medio CHECK (medio IN ('WOMPI', 'MANUAL'));

CREATE TABLE IF NOT EXISTS auditoria_superadmin (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario        VARCHAR(100) NOT NULL,
    fecha          TIMESTAMP    NOT NULL DEFAULT now(),
    cod_taller     INTEGER REFERENCES talleres (cod_taller),
    accion         VARCHAR(50)  NOT NULL,
    valor_anterior JSONB,
    valor_nuevo    JSONB,
    motivo         TEXT         NOT NULL
);

CREATE TABLE IF NOT EXISTS notas_taller (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cod_taller INTEGER NOT NULL REFERENCES talleres (cod_taller),
    autor      VARCHAR(100) NOT NULL,
    fecha      TIMESTAMP NOT NULL DEFAULT now(),
    texto      TEXT NOT NULL
);

CREATE OR REPLACE VIEW vw_usuarios_perfiles WITH (security_invoker = on) AS
SELECT u.documento_usu,
       u.nombre_usu || ' ' || u.apellido_1_usu || ' ' || COALESCE(u.apellido_2_usu, '') AS nombre_completo,
       u.correo_usu, u.cod_tipo_usu, e.nombre_est AS estado_usuario,
       p.nombre_prf AS perfil, p.descripcion_prf AS descripcion_perfil,
       r.nombre_rol AS rol, r.descripcion_rol AS descripcion_rol,
       u.ultimo_ingreso_usu
FROM usuarios u
INNER JOIN estados e  ON u.cod_est_usu = e.cod_est
INNER JOIN perfiles p ON u.cod_taller = p.cod_taller AND u.cod_prf_usu = p.cod_prf AND u.cod_rol_prf_usu = p.cod_rol_prf
INNER JOIN roles r    ON p.cod_rol_prf = r.cod_rol;
