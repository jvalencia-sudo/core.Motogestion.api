-- F2-02: retirar un item de una orden ya NO borra la fila fisicamente -- se
-- marca retirado=true con un motivo obligatorio, para que el cliente (link
-- publico) y el taller puedan ver QUE se quito y POR QUE, en vez de que
-- simplemente desaparezca. Mismo patron ya usado por cobrar_deto (cortesia):
-- la fila sigue existiendo real, se excluye solo del DINERO, nunca de la
-- vista. El stock SI se sigue devolviendo igual que con el DELETE de antes
-- (ver fn_revertir_stock_detalle, reusada sin tocarla via un trigger AFTER
-- UPDATE en vez de AFTER DELETE).
--
-- Importante para quien toque este codigo despues: la app NUNCA debe cambiar
-- cantidad_deto y retirado en el mismo UPDATE -- son dos acciones distintas
-- (dos metodos de repositorio distintos). detalle_orden_trabajo ya tiene
-- otros dos triggers AFTER UPDATE (tg_ajustar_stock por cantidad,
-- tg_audit_detalle_orden_trabajo); Postgres los ejecuta en orden alfabetico
-- por nombre, y tg_ajustar_stock ya tiene su propio guard (no hace nada si
-- cantidad_deto no cambio), asi que mientras un retiro solo toque
-- retirado/motivo_retiro, no hay solapamiento.

ALTER TABLE detalle_orden_trabajo
    ADD COLUMN retirado      BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN motivo_retiro VARCHAR(200);

ALTER TABLE detalle_orden_trabajo
    ADD CONSTRAINT chk_deto_motivo_si_retirado CHECK (NOT retirado OR motivo_retiro IS NOT NULL);

CREATE TRIGGER tg_revertir_stock_retiro
AFTER UPDATE OF retirado ON detalle_orden_trabajo
FOR EACH ROW WHEN (NEW.retirado AND NOT OLD.retirado)
EXECUTE FUNCTION fn_revertir_stock_detalle();

-- Vista de detalle: agrega retirado/motivo_retiro al final (visibles, la fila
-- nunca se excluye de esta vista -- solo del dinero en vw_resumen_financiero_ot).
CREATE OR REPLACE VIEW vw_detalle_ot_productos WITH (security_invoker = on) AS
SELECT
    dot.consecutivo_ot_deto, dot.cod_pro_deto,
    p.nombre_pro, p.descripcion_pro, dot.cantidad_deto, dot.valor_unitario_deto,
    dot.cobrar_deto, dot.motivo_no_cobro_deto,
    (dot.cantidad_deto * dot.valor_unitario_deto) AS subtotal,
    dot.fecha_confirmacion_deto,
    u.nombre_usu || ' ' || u.apellido_1_usu AS usuario_confirmacion,
    e.nombre_est AS estado_producto,
    p.tipo_pro,
    dot.retirado, dot.motivo_retiro
FROM detalle_orden_trabajo dot
INNER JOIN productos p ON dot.cod_pro_deto = p.cod_pro AND dot.cod_taller = p.cod_taller
INNER JOIN usuarios u  ON dot.documento_usu_deto = u.documento_usu AND dot.cod_taller = u.cod_taller
INNER JOIN estados e   ON p.cod_est_pro = e.cod_est;

-- Totales: un item retirado no cuenta plata, igual que una cortesia no
-- cobrada -- misma condicion CASE, ahora con NOT dot.retirado ademas de
-- dot.cobrar_deto.
CREATE OR REPLACE VIEW vw_resumen_financiero_ot WITH (security_invoker = on) AS
SELECT
    ot.consecutivo_ot, ot.fecha_elaboracion_ot,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente, m.placa_mot,
    COUNT(CASE WHEN dot.cobrar_deto AND NOT dot.retirado THEN dot.cod_pro_deto END) AS total_items,
    SUM(CASE WHEN dot.cobrar_deto AND NOT dot.retirado THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS subtotal_productos,
    0 AS total_impuestos,
    SUM(CASE WHEN dot.cobrar_deto AND NOT dot.retirado THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS total_ot,
    COALESCE(pg.total_pagado, 0) AS total_pagado,
    SUM(CASE WHEN dot.cobrar_deto AND NOT dot.retirado THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) - COALESCE(pg.total_pagado, 0) AS saldo_ot
FROM ordenes_trabajo ot
INNER JOIN detalle_orden_trabajo dot ON ot.consecutivo_ot = dot.consecutivo_ot_deto AND ot.cod_taller = dot.cod_taller
INNER JOIN motos m    ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
LEFT JOIN (
    SELECT cod_taller, consecutivo_ot_pago, SUM(valor_pago) AS total_pagado
    FROM pagos_orden
    WHERE NOT anulado_pago
    GROUP BY cod_taller, consecutivo_ot_pago
) pg ON pg.cod_taller = ot.cod_taller AND pg.consecutivo_ot_pago = ot.consecutivo_ot
GROUP BY ot.consecutivo_ot, ot.fecha_elaboracion_ot, c.nombre_cli, c.apellido_1_cli, m.placa_mot, pg.total_pagado;

-- "trabajos" (resumen de la orden en listados) ya no debe listar items
-- retirados como si siguieran activos.
CREATE OR REPLACE VIEW vw_ordenes_trabajo_completa WITH (security_invoker = on) AS
SELECT
    ot.consecutivo_ot, ot.fecha_elaboracion_ot, ot.fecha_entrega_ot,
    ot.kilometraje_ingreso_ot,
    ot.observacion_cli_ot, ot.observacion_ot,
    ot.fecha_fin_garantia_ot,
    m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
    mar.nombre_mar AS marca_moto,
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo_cliente,
    c.telefono_cli, c.correo_cli, c.direccion_cli,
    urp.documento_usu AS documento_recepcionista,
    urp.nombre_usu || ' ' || urp.apellido_1_usu AS recepcionista,
    umc.documento_usu AS documento_mecanico,
    umc.nombre_usu || ' ' || umc.apellido_1_usu AS mecanico,
    ote.nombre_ot_est AS estado_ot, ot.cod_ot_est_ot,
    (SELECT STRING_AGG(p.nombre_pro, ', ' ORDER BY p.nombre_pro)
       FROM detalle_orden_trabajo dot
       JOIN productos p ON dot.cod_pro_deto = p.cod_pro AND dot.cod_taller = p.cod_taller
      WHERE dot.consecutivo_ot_deto = ot.consecutivo_ot AND dot.cod_taller = ot.cod_taller
        AND NOT dot.retirado
    ) AS trabajos,
    ot.kilometraje_salida_ot,
    ot.motivo_anulacion_ot, ot.fecha_anulacion_ot, ot.documento_usu_anulacion_ot,
    c.tipo_documento_cli, m.ciudad_placa_mot,
    ot.token_publico::text AS token_publico
FROM ordenes_trabajo ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu AND ot.cod_taller = urp.cod_taller
LEFT JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;
