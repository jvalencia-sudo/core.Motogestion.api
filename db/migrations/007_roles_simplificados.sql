-- F1-12: fusiona perfil+rol (perfiles.es_admin en vez de la tabla global
-- roles + cod_rol_prf como parte de la PK), elimina roles/vistas
-- (vestigiales: ningún require_permiso/usuario_tiene_permiso las consulta),
-- y renueva el catálogo de permisos por módulo (ver / crear_editar /
-- eliminar_o_anular) + acciones sensibles. Limpia además 16+8 permisos
-- muertos de una plantilla de logística que nunca se usó (operations,
-- orders, roles, vistas, users, perfiles-permisos -- ninguno se consulta en
-- ningún require_permiso hoy).
--
-- Orden: (1) DROP de las 6 vistas que dependen de roles/vistas/cod_rol_prf
-- -> (2) columnas nuevas es_admin/es_admin_usu -> (3) un único loop por
-- taller que hace TODO el DML sensible a RLS (perfiles/usuarios/
-- perfiles_permisos tienen FORCE ROW LEVEL SECURITY) mientras el catálogo
-- viejo todavía tiene sus nombres originales -> (4) restructura de llaves
-- -> (5) DROP de columnas cod_rol_prf* -> (6) DROP de roles/vistas ->
-- (7) catálogo nuevo (rename en sitio + altas) -> (8) fn_seed_perfiles_taller
-- reescrita -> (9) recrear las 6 vistas sin roles/vistas.

-- ============================================================
-- 1. DROP de vistas dependientes
-- ============================================================
DROP VIEW IF EXISTS vw_usuarios_perfiles;
DROP VIEW IF EXISTS vw_perfiles;
DROP VIEW IF EXISTS vw_perfiles_permisos_detalle;
DROP VIEW IF EXISTS vw_permisos;
DROP VIEW IF EXISTS vw_permisos_por_perfil;
-- vw_mecanicos no apareció en el análisis inicial (dependía de
-- usuarios.cod_rol_prf_usu directamente, no de perfiles/roles) -- se
-- descubrió al correr la migración contra Postgres real.
DROP VIEW IF EXISTS vw_mecanicos;

-- ============================================================
-- 2. Columnas nuevas (denormalizadas, igual patrón que cod_rol_prf_usu hoy)
-- ============================================================
ALTER TABLE perfiles ADD COLUMN es_admin BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE usuarios ADD COLUMN es_admin_usu BOOLEAN NOT NULL DEFAULT false;

-- ============================================================
-- 3. Loop único por taller: todo el DML que depende de RLS, ANTES de que
--    el catálogo viejo cambie de nombre (los JOIN de abajo buscan
--    'crear:%'/'actualizar:%' literal).
-- ============================================================
DO $$
DECLARE
    r RECORD;
BEGIN
    ALTER TABLE usuarios DISABLE TRIGGER tg_audit_usuarios;

    FOR r IN SELECT cod_taller FROM talleres LOOP
        PERFORM set_config('app.tenant_id', r.cod_taller::text, true);

        -- 3a. Backfill es_admin / es_admin_usu desde el rol actual.
        UPDATE perfiles SET es_admin = true
         WHERE cod_taller = r.cod_taller AND cod_rol_prf = 1;

        UPDATE usuarios SET es_admin_usu = true
         WHERE cod_taller = r.cod_taller AND cod_rol_prf_usu = 1;

        -- 3b. Relleno del hueco crear/actualizar: si un perfil tenía
        --     'crear:X' pero NO 'actualizar:X', le damos también el cod_prm
        --     de 'actualizar:X' (que en el paso 7 se renombra a
        --     'crear_editar:X') -- así no pierde el permiso al fusionar.
        INSERT INTO perfiles_permisos (cod_taller, cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp)
        SELECT pp.cod_taller, act.cod_prm, pp.cod_prf_pp, pp.cod_rol_prf_pp, pp.cod_est_pp
          FROM perfiles_permisos pp
          JOIN permisos crea ON crea.cod_prm = pp.cod_prm_pp
          JOIN permisos act  ON act.nombre_prm = 'actualizar:' || split_part(crea.nombre_prm, ':', 2)
         WHERE pp.cod_taller = r.cod_taller
           AND crea.nombre_prm LIKE 'crear:%'
           AND split_part(crea.nombre_prm, ':', 2) IN
               ('clientes','marcas','motos','productos','ordenes-trabajo','reclamos')
           AND NOT EXISTS (
               SELECT 1 FROM perfiles_permisos x
                WHERE x.cod_taller = pp.cod_taller AND x.cod_prf_pp = pp.cod_prf_pp
                  AND x.cod_prm_pp = act.cod_prm
           );

        -- 3c. Borra asignaciones a la "plantilla de logística" + users/
        --     perfiles-permisos (ningún endpoint los consulta hoy).
        DELETE FROM perfiles_permisos
         WHERE cod_taller = r.cod_taller
           AND cod_prm_pp IN (
               SELECT cod_prm FROM permisos
                WHERE split_part(nombre_prm, ':', 2) IN
                      ('operations','orders','roles','vistas','users','perfiles-permisos')
           );

        -- 3d. Borra las asignaciones 'crear:X' ya cubiertas por 3b (si no se
        --     borran aquí, el DELETE de permisos del paso 7 fallaría por la
        --     FK fk_pp_permiso).
        DELETE FROM perfiles_permisos
         WHERE cod_taller = r.cod_taller
           AND cod_prm_pp IN (
               SELECT cod_prm FROM permisos
                WHERE nombre_prm LIKE 'crear:%'
                  AND split_part(nombre_prm, ':', 2) IN
                      ('clientes','marcas','motos','productos','ordenes-trabajo','reclamos')
           );

        -- 3e. El Administrador deja de necesitar asignación explícita
        --     (bypass total vía es_admin_usu).
        DELETE FROM perfiles_permisos
         WHERE cod_taller = r.cod_taller
           AND cod_prf_pp IN (
               SELECT cod_prf FROM perfiles WHERE cod_taller = r.cod_taller AND es_admin = true
           );
    END LOOP;

    ALTER TABLE usuarios ENABLE TRIGGER tg_audit_usuarios;
END $$;

-- ============================================================
-- 4. Restructura de llaves: soltar las FK que apuntan al PK compuesto de
--    `perfiles` ANTES de poder cambiar ese PK.
-- ============================================================
ALTER TABLE perfiles_permisos DROP CONSTRAINT fk_pp_perfil;
ALTER TABLE usuarios          DROP CONSTRAINT fk_usuarios_perfil;
ALTER TABLE perfiles          DROP CONSTRAINT fk_perfiles_rol;

ALTER TABLE perfiles DROP CONSTRAINT pk_perfiles;
ALTER TABLE perfiles ADD CONSTRAINT pk_perfiles PRIMARY KEY (cod_taller, cod_prf);

ALTER TABLE perfiles_permisos DROP CONSTRAINT pk_perfiles_permisos;
ALTER TABLE perfiles_permisos ADD CONSTRAINT pk_perfiles_permisos
    PRIMARY KEY (cod_taller, cod_prm_pp, cod_prf_pp);
-- Seguro: cod_rol_prf_pp siempre estuvo determinado 1:1 por cod_prf_pp (vía
-- la FK a perfiles), quitarlo de la PK no puede crear duplicados.

ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_perfil
    FOREIGN KEY (cod_taller, cod_prf_usu) REFERENCES perfiles (cod_taller, cod_prf);

ALTER TABLE perfiles_permisos ADD CONSTRAINT fk_pp_perfil
    FOREIGN KEY (cod_taller, cod_prf_pp) REFERENCES perfiles (cod_taller, cod_prf);

-- ============================================================
-- 5. Las columnas cod_rol_prf* ya no se usan para nada -- se elimina el
--    concepto, no solo la FK.
-- ============================================================
ALTER TABLE perfiles          DROP COLUMN cod_rol_prf;
ALTER TABLE usuarios          DROP COLUMN cod_rol_prf_usu;
ALTER TABLE perfiles_permisos DROP COLUMN cod_rol_prf_pp;

-- ============================================================
-- 6. Elimina roles y vistas (vestigiales). ruta_vis_prm se borra primero
--    (arrastra su propia FK fk_permisos_vista).
-- ============================================================
ALTER TABLE permisos DROP COLUMN ruta_vis_prm;
DROP TABLE vistas;
DROP TABLE roles;
DROP SEQUENCE IF EXISTS seq_roles;

-- ============================================================
-- 7. Catálogo nuevo (tabla GLOBAL, sin RLS -- estas sentencias corren una
--    sola vez, sin loop).
-- ============================================================
-- 7a. Rename en sitio (mismo cod_prm -> perfiles_permisos queda traducido
--     automáticamente, sin tocarla).
UPDATE permisos SET
    nombre_prm = 'ver:' || split_part(nombre_prm, ':', 2),
    descripcion_prm = 'Permite ver ' || split_part(nombre_prm, ':', 2)
WHERE nombre_prm LIKE 'leer:%'
  AND split_part(nombre_prm, ':', 2) IN
      ('clientes','marcas','motos','productos','ordenes-trabajo','reclamos');

UPDATE permisos SET
    nombre_prm = 'crear_editar:' || split_part(nombre_prm, ':', 2),
    descripcion_prm = 'Permite crear y editar ' || split_part(nombre_prm, ':', 2)
WHERE nombre_prm LIKE 'actualizar:%'
  AND split_part(nombre_prm, ':', 2) IN
      ('clientes','marcas','motos','productos','ordenes-trabajo','reclamos');

UPDATE permisos SET
    nombre_prm = 'eliminar_o_anular:' || split_part(nombre_prm, ':', 2),
    descripcion_prm = 'Permite eliminar o anular ' || split_part(nombre_prm, ':', 2)
WHERE nombre_prm LIKE 'eliminar:%'
  AND split_part(nombre_prm, ':', 2) IN
      ('clientes','marcas','motos','productos','ordenes-trabajo','reclamos');
-- 'marcar_no_cobro:ordenes-trabajo' no se toca (ya está en el formato nuevo).

-- 7b. Borra lo superado por el rename (ya sin hijos en perfiles_permisos,
--     ver 3d/3c) y la plantilla de logística + users/perfiles-permisos.
DELETE FROM permisos
 WHERE nombre_prm LIKE 'crear:%'
   AND split_part(nombre_prm, ':', 2) IN
       ('clientes','marcas','motos','productos','ordenes-trabajo','reclamos');

DELETE FROM permisos
 WHERE split_part(nombre_prm, ':', 2) IN
       ('operations','orders','roles','vistas','users','perfiles-permisos');

-- 7c. Módulos nuevos (sin traducción -- no existían permisos antes).
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm)
SELECT nextval('seq_permisos'), v.nombre, v.descripcion
FROM (VALUES
    ('ver:inventario',               'Permite ver el inventario y el kardex'),
    ('crear_editar:inventario',      'Permite registrar entradas y tomas físicas de inventario'),
    ('eliminar_o_anular:inventario', 'Permite anular movimientos de inventario'),
    ('ver:tablero',                  'Permite ver el tablero de órdenes'),
    ('crear_editar:tablero',         'Permite mover órdenes en el tablero'),
    ('eliminar_o_anular:tablero',    'Permite anular órdenes desde el tablero'),
    ('ver:talleres',                 'Permite ver la configuración del taller ("Mi taller")'),
    ('crear_editar:talleres',        'Permite editar la configuración del taller'),
    ('eliminar_o_anular:talleres',   'Reservado (el taller no se elimina desde este módulo)'),
    ('ver:planes',                   'Permite ver el plan y la suscripción del taller'),
    ('crear_editar:planes',          'Permite cambiar el plan del taller'),
    ('eliminar_o_anular:planes',     'Reservado (no hay acción de eliminar plan hoy)'),
    ('ver:impuestos',                'Permite ver el catálogo de impuestos'),
    ('crear_editar:impuestos',       'Permite crear y editar impuestos'),
    ('eliminar_o_anular:impuestos',  'Permite eliminar impuestos')
) AS v(nombre, descripcion)
WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE nombre_prm = v.nombre);

-- 7d. Acciones sensibles (fuera de la grilla estándar ver/crear_editar/eliminar_o_anular).
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm)
SELECT nextval('seq_permisos'), v.nombre, v.descripcion
FROM (VALUES
    ('anular:ordenes-trabajo', 'Permite anular una orden de trabajo completa (con motivo obligatorio)'),
    ('ajustar:inventario',     'Permite registrar entradas y tomas físicas que ajustan el stock'),
    ('ver_costos:productos',  'Permite ver costos y márgenes de productos'),
    ('ver_todo:tablero',      'Permite ver el tablero completo (todas las órdenes, no solo las propias) y filtrar por mecánico')
) AS v(nombre, descripcion)
WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE nombre_prm = v.nombre);

-- ============================================================
-- 8. fn_seed_perfiles_taller: ya no inserta cod_rol_prf, Admin ya no recibe
--    asignación explícita, Mecánico/Recepcionista usan los nombres nuevos.
--    Recepcionista recibe también 'ver_todo:tablero'/'ajustar:inventario'
--    (reproduce el ROLES_GESTOR que hoy tienen tablero/inventario).
-- ============================================================
CREATE OR REPLACE FUNCTION fn_seed_perfiles_taller(p_taller INTEGER)
RETURNS INTEGER AS $$
DECLARE
    v_admin INTEGER;
    v_meca  INTEGER;
    v_recep INTEGER;
BEGIN
    PERFORM set_config('app.tenant_id', p_taller::text, true);

    INSERT INTO perfiles (cod_taller, cod_prf, nombre_prf, descripcion_prf, cod_est_prf, es_admin)
    VALUES (p_taller, nextval('seq_perfiles'), 'Administrador', 'Acceso total al taller', 1, true)
    RETURNING cod_prf INTO v_admin;

    INSERT INTO perfiles (cod_taller, cod_prf, nombre_prf, descripcion_prf, cod_est_prf, es_admin)
    VALUES (p_taller, nextval('seq_perfiles'), 'Mecánico', 'Gestión de órdenes de trabajo', 1, false)
    RETURNING cod_prf INTO v_meca;

    INSERT INTO perfiles (cod_taller, cod_prf, nombre_prf, descripcion_prf, cod_est_prf, es_admin)
    VALUES (p_taller, nextval('seq_perfiles'), 'Recepcionista', 'Gestión de clientes, motos y órdenes', 1, false)
    RETURNING cod_prf INTO v_recep;

    -- Admin: SIN asignación explícita (bypass vía es_admin_usu).

    INSERT INTO perfiles_permisos (cod_taller, cod_prm_pp, cod_prf_pp, cod_est_pp)
    SELECT p_taller, cod_prm, v_meca, 1 FROM permisos
    WHERE nombre_prm IN (
        'ver:clientes','ver:marcas','ver:motos','ver:productos',
        'ver:ordenes-trabajo','crear_editar:ordenes-trabajo',
        'ver:tablero','ver:reclamos','crear_editar:reclamos'
    );

    INSERT INTO perfiles_permisos (cod_taller, cod_prm_pp, cod_prf_pp, cod_est_pp)
    SELECT p_taller, cod_prm, v_recep, 1 FROM permisos
    WHERE nombre_prm IN (
        'ver:clientes','crear_editar:clientes','ver:marcas',
        'ver:motos','crear_editar:motos','ver:productos',
        'ver:ordenes-trabajo','crear_editar:ordenes-trabajo',
        'ver:tablero','ver_todo:tablero','ver:inventario','ajustar:inventario',
        'ver:reclamos','crear_editar:reclamos'
    );

    RETURN v_admin;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 9. Recrear las 6 vistas, sin roles/vistas, usando es_admin/es_admin_usu.
-- ============================================================
-- vw_mecanicos filtraba por cod_rol_prf_usu = 2 (el id global fijo de
-- "Mecánico", que en la práctica ya recibía también cualquier perfil
-- propio no-admin que el Admin creara -- NON_ADMIN_ROL_DEFAULT=2). Sin
-- códigos de rol fijos, el reemplazo directo es "cualquier usuario activo
-- que no sea Administrador" (incluye ahora también a Recepcionista en el
-- filtro de mecánico del tablero -- ensanchamiento menor y consciente, no
-- una restricción de seguridad).
CREATE OR REPLACE VIEW vw_mecanicos WITH (security_invoker = on) AS
SELECT documento_usu, nombre_usu || ' ' || COALESCE(apellido_1_usu, '') AS nombre
FROM usuarios
WHERE NOT es_admin_usu AND cod_est_usu = 1;

CREATE OR REPLACE VIEW vw_usuarios_perfiles WITH (security_invoker = on) AS
SELECT u.documento_usu,
       u.nombre_usu || ' ' || u.apellido_1_usu || ' ' || COALESCE(u.apellido_2_usu, '') AS nombre_completo,
       u.correo_usu, u.cod_tipo_usu, e.nombre_est AS estado_usuario,
       p.nombre_prf AS perfil, p.descripcion_prf AS descripcion_perfil,
       u.es_admin_usu, u.ultimo_ingreso_usu
FROM usuarios u
INNER JOIN estados e  ON u.cod_est_usu = e.cod_est
INNER JOIN perfiles p ON u.cod_taller = p.cod_taller AND u.cod_prf_usu = p.cod_prf;

CREATE OR REPLACE VIEW vw_perfiles WITH (security_invoker = on) AS
SELECT p.cod_prf, p.nombre_prf, p.descripcion_prf, p.es_admin, p.cod_est_prf,
       e.nombre_est AS nombre_est_prf
FROM perfiles p
INNER JOIN estados e ON p.cod_est_prf = e.cod_est
ORDER BY p.cod_prf;

CREATE OR REPLACE VIEW vw_perfiles_permisos_detalle WITH (security_invoker = on) AS
SELECT pf.cod_prf, pf.nombre_prf, pf.es_admin,
       pm.cod_prm, pm.nombre_prm, pm.descripcion_prm,
       e.nombre_est AS estado_permiso
FROM perfiles_permisos pp
INNER JOIN perfiles pf ON pp.cod_taller = pf.cod_taller AND pp.cod_prf_pp = pf.cod_prf
INNER JOIN permisos pm ON pp.cod_prm_pp = pm.cod_prm
INNER JOIN estados e   ON pp.cod_est_pp = e.cod_est;

CREATE OR REPLACE VIEW vw_permisos WITH (security_invoker = on) AS
SELECT p.cod_prm, p.nombre_prm, p.descripcion_prm FROM permisos p;

CREATE OR REPLACE VIEW vw_permisos_por_perfil WITH (security_invoker = on) AS
SELECT p.cod_prm, p.nombre_prm, p.descripcion_prm, pp.cod_prf_pp, pp.cod_est_pp
FROM permisos p
INNER JOIN perfiles_permisos pp ON p.cod_prm = pp.cod_prm_pp;
