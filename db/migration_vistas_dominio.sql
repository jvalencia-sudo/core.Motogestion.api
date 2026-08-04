-- ============================================================
-- Migración: vistas de dominio para respetar "un repositorio = una tabla".
--
-- El repo de inventario (movimientos_inventario) y el de paquetes
-- (paquete_componentes) necesitan el nombre/tipo/stock del producto asociado.
-- En vez de que esos repos consulten la tabla `productos` directamente, leen de
-- una vista de dominio propia (mismo patrón que vw_productos, vw_clientes_resumen).
--
-- Idempotente. Correr como el rol DUEÑO de las tablas (mt_app local).
-- ============================================================

BEGIN;

-- Kardex de inventario con el nombre del producto (para las pantallas de movimientos).
CREATE OR REPLACE VIEW vw_movimientos_inventario WITH (security_invoker = on) AS
SELECT m.cod_mov, m.cod_pro_mov, p.nombre_pro, m.tipo_mov, m.cantidad_mov,
       m.stock_ant_mov, m.stock_nue_mov, m.motivo_mov, m.documento_usu_mov,
       to_char(m.fecha_mov, 'YYYY-MM-DD HH24:MI') AS fecha_mov, m.referencia_mov
FROM movimientos_inventario m
JOIN productos p ON p.cod_pro = m.cod_pro_mov AND p.cod_taller = m.cod_taller;

-- Componentes de un paquete con los datos del producto incluido.
CREATE OR REPLACE VIEW vw_paquete_componentes WITH (security_invoker = on) AS
SELECT pc.cod_paq_comp, pc.cod_pro_paq, pc.cod_pro_comp, pc.cantidad_comp,
       p.nombre_pro, p.tipo_pro, p.stock_pro
FROM paquete_componentes pc
JOIN productos p ON p.cod_pro = pc.cod_pro_comp AND p.cod_taller = pc.cod_taller;

COMMIT;
