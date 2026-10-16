-- F0-14: super-admin de plataforma explícito (ya no depende de cod_taller=1).
-- Aplicar a mano en la BD de producción (igual que migration_timezone_bogota.sql).
-- CI/fresh DBs ya tienen esto en full_schema_v2_multitenant.sql -- este archivo es
-- solo la versión incremental para una BD ya desplegada.

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS es_super_admin BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ultimo_ingreso_usu TIMESTAMP;

-- NO ejecutar un UPDATE masivo acá: `usuarios` tiene RLS forzado y esta
-- migración se aplica como mt_app sin `app.tenant_id` fijado -- la política no
-- deja ver ninguna fila y el UPDATE responde "UPDATE 0" sin error (nadie queda
-- como super-admin, el despliegue te deja sin acceso a /superadmin). Y aunque
-- fijaras el tenant a ciegas, `cod_taller=1 AND cod_rol_prf_usu=1` volvería a
-- convertir en super-admin a TODOS los administradores del taller 1 --
-- exactamente el hueco de seguridad que F0-14 cerró (ese taller también se
-- usa para demos).
--
-- Aplicar a mano, en UNA transacción (la verificación va DENTRO, antes del
-- COMMIT -- afuera, sin `app.tenant_id` fijado, el SELECT también daría 0
-- filas por RLS y haría creer que falló aunque sí haya funcionado):
--
--   BEGIN;
--   -- 1) Busca el taller REAL del usuario (usuarios_identidad no tiene RLS,
--   --    así que esto funciona sin fijar ningún tenant todavía):
--   SELECT cod_taller FROM usuarios_identidad WHERE documento_usu = '<tu documento>';
--   -- 2) Con el cod_taller de arriba, fija el tenant y marca al usuario:
--   SELECT set_config('app.tenant_id', '<cod_taller de arriba>', true);
--   UPDATE usuarios SET es_super_admin = true WHERE documento_usu = '<tu documento>';
--   -- Debe decir "UPDATE 1". Si dice "UPDATE 0", el documento o el tenant
--   -- están mal -- ROLLBACK, no COMMIT.
--   -- 3) Verificación, DENTRO de la misma transacción:
--   SELECT documento_usu FROM usuarios WHERE es_super_admin = true;
--   -- Debe traer exactamente 1 fila (la tuya). Si trae 0 o más de 1,
--   -- ROLLBACK en vez de COMMIT.
--   COMMIT;

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
