-- F2-01 (fase 2 del rediseño visual de /orden/[token]): la cotización
-- pública agrupa los ítems en "Repuestos" y "Mano de obra" -- necesita saber
-- el tipo_pro de cada línea, que hoy no viaja en la vista de detalle.
-- Ningún ALTER TABLE: tipo_pro ya existe en productos, solo se expone en la
-- vista. Se añade AL FINAL del SELECT (no se puede reordenar una vista
-- existente con CREATE OR REPLACE). FROM/JOIN copiados tal cual de
-- full_schema_v2_multitenant.sql, sin reescribirlos de memoria.

CREATE OR REPLACE VIEW vw_detalle_ot_productos WITH (security_invoker = on) AS
SELECT
    dot.consecutivo_ot_deto, dot.cod_pro_deto,
    p.nombre_pro, p.descripcion_pro, dot.cantidad_deto, dot.valor_unitario_deto,
    dot.cobrar_deto, dot.motivo_no_cobro_deto,
    (dot.cantidad_deto * dot.valor_unitario_deto) AS subtotal,
    dot.fecha_confirmacion_deto,
    u.nombre_usu || ' ' || u.apellido_1_usu AS usuario_confirmacion,
    e.nombre_est AS estado_producto,
    p.tipo_pro
FROM detalle_orden_trabajo dot
INNER JOIN productos p ON dot.cod_pro_deto = p.cod_pro AND dot.cod_taller = p.cod_taller
INNER JOIN usuarios u  ON dot.documento_usu_deto = u.documento_usu AND dot.cod_taller = u.cod_taller
INNER JOIN estados e   ON p.cod_est_pro = e.cod_est;
