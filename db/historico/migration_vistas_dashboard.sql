-- ============================================================
-- Migración: vistas de dominio para dashboard y tablero.
--
-- Evita que DashboardRepositorio (table=ordenes_trabajo) y TableroRepositorio
-- consulten tablas base ajenas (clientes, motos, productos, reclamos, usuarios).
-- Ahora esos repos leen vistas de dominio (RLS por security_invoker → por taller).
--
-- Idempotente. Correr como el rol DUEÑO de las tablas (mt_app local).
-- ============================================================

BEGIN;

-- Resumen escalar de la home (una fila). Cada subconsulta respeta el RLS del taller.
CREATE OR REPLACE VIEW vw_dashboard_resumen WITH (security_invoker = on) AS
SELECT
  (SELECT count(*) FROM clientes)        AS total_clientes,
  (SELECT count(*) FROM motos)           AS total_motos,
  (SELECT count(*) FROM productos)       AS total_productos,
  (SELECT count(*) FROM ordenes_trabajo) AS total_ordenes,
  (SELECT count(*) FROM ordenes_trabajo WHERE cod_ot_est_ot IN (1, 2, 6)) AS ot_activas,
  (SELECT count(*) FROM productos
     WHERE cod_est_pro = 1 AND stock_pro <= stock_pro_min)               AS productos_bajo_stock,
  (SELECT count(*) FROM reclamos)        AS total_reclamos;

-- Conteo de órdenes por estado (todos los estados, aunque tengan 0).
CREATE OR REPLACE VIEW vw_dashboard_ordenes_por_estado WITH (security_invoker = on) AS
SELECT e.cod_ot_est, e.nombre_ot_est, COUNT(o.consecutivo_ot) AS cantidad
FROM ot_estados e
LEFT JOIN ordenes_trabajo o ON o.cod_ot_est_ot = e.cod_ot_est
GROUP BY e.cod_ot_est, e.nombre_ot_est;

-- Mecánicos activos del taller (para el selector del tablero).
CREATE OR REPLACE VIEW vw_mecanicos WITH (security_invoker = on) AS
SELECT documento_usu, nombre_usu || ' ' || COALESCE(apellido_1_usu, '') AS nombre
FROM usuarios
WHERE cod_rol_prf_usu = 2 AND cod_est_usu = 1;

COMMIT;
