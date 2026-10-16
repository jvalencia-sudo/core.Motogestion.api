-- ============================================================
-- Migración: vistas de dominio para permisos.
--
-- Evita que los repos de permisos crucen tablas ajenas:
--   * PermisoRepositorio leía permisos JOIN perfiles_permisos  -> vw_permisos_por_perfil
--   * PerfilPermisoRepositorio filtraba con (SELECT nombre_rol FROM roles ...) ->
--     se añade cod_rol a vw_perfiles_permisos_detalle para filtrar directo.
--
-- Idempotente. Correr como el rol DUEÑO de las tablas (mt_app local).
-- ============================================================

BEGIN;

-- Permisos asignados a un perfil (para login y para la pantalla de permisos).
CREATE OR REPLACE VIEW vw_permisos_por_perfil WITH (security_invoker = on) AS
SELECT p.cod_prm, p.nombre_prm, p.descripcion_prm, p.ruta_vis_prm,
       pp.cod_prf_pp, pp.cod_rol_prf_pp, pp.cod_est_pp
FROM permisos p
INNER JOIN perfiles_permisos pp ON p.cod_prm = pp.cod_prm_pp;

-- Se añade cod_rol al final (CREATE OR REPLACE solo permite columnas nuevas al final)
-- para poder filtrar por rol sin la subconsulta a `roles`.
CREATE OR REPLACE VIEW vw_perfiles_permisos_detalle WITH (security_invoker = on) AS
SELECT pf.cod_prf, pf.nombre_prf, r.nombre_rol,
       pm.cod_prm, pm.nombre_prm, pm.descripcion_prm,
       v.nombre_vis, v.ruta_vis, e.nombre_est AS estado_permiso,
       r.cod_rol
FROM perfiles_permisos pp
INNER JOIN perfiles pf ON pp.cod_taller = pf.cod_taller AND pp.cod_prf_pp = pf.cod_prf AND pp.cod_rol_prf_pp = pf.cod_rol_prf
INNER JOIN roles r     ON pf.cod_rol_prf = r.cod_rol
INNER JOIN permisos pm ON pp.cod_prm_pp = pm.cod_prm
INNER JOIN vistas v    ON pm.ruta_vis_prm = v.ruta_vis
INNER JOIN estados e   ON pp.cod_est_pp = e.cod_est;

COMMIT;
