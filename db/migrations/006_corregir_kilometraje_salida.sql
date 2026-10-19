-- F1-11: kilometreje_salida_ot era DATE (y con error de ortografía) mientras
-- que el contrato EntregarOrdenContract y el repositorio ya le mandaban un
-- entero -- entregar una orden con kilometraje de salida fallaba con un
-- error de tipo en Postgres.
--
-- Ninguna vista selecciona hoy esta columna, así que no hace falta dropearla
-- antes de tocar la tabla. El guardia de abajo verifica en cada entorno real
-- (en vez de asumirlo por el seed local) que no haya datos que perder antes
-- de eliminarla.
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count FROM ordenes_trabajo WHERE kilometreje_salida_ot IS NOT NULL;
    IF v_count > 0 THEN
        RAISE EXCEPTION 'kilometreje_salida_ot tiene % fila(s) con datos -- revisar antes de eliminar la columna', v_count;
    END IF;
END $$;

ALTER TABLE ordenes_trabajo DROP COLUMN kilometreje_salida_ot;
ALTER TABLE ordenes_trabajo ADD COLUMN kilometraje_salida_ot INTEGER;
ALTER TABLE ordenes_trabajo ADD CONSTRAINT chk_ot_km_salida
    CHECK (kilometraje_salida_ot IS NULL OR kilometraje_salida_ot >= kilometraje_ingreso_ot);

-- Se expone en el listado/detalle de órdenes para que quede visible una vez
-- entregada (antes no estaba en ninguna vista, ni siquiera con el nombre
-- viejo). Va al final del SELECT, no junto a kilometraje_ingreso_ot: Postgres
-- no permite que CREATE OR REPLACE VIEW reordene columnas existentes, solo
-- agregar nuevas al final.
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
    ) AS trabajos,
    ot.kilometraje_salida_ot
FROM ordenes_trabajo ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu AND ot.cod_taller = urp.cod_taller
LEFT JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;
