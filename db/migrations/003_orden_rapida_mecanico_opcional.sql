-- F1-01: abrir una orden de trabajo solo con placa, kilometraje y motivo del
-- cliente -- sin mecánico asignado todavía (se asigna después).
--
-- documento_usu_mc_ot ya acepta NULL a nivel de columna (ver
-- full_schema_v2_multitenant.sql), pero 3 vistas la unían con INNER JOIN: una
-- orden sin mecánico desaparecía del listado principal, del tablero Kanban y
-- de "pendientes" -- no por un bug de la app, sino porque la vista la excluía
-- antes de que el backend la viera. Se cambia a LEFT JOIN en las 3.

CREATE OR REPLACE VIEW vw_ordenes_trabajo_completa WITH (security_invoker = on) AS
SELECT
    ot.consecutivo_ot, ot.fecha_elaboracion_ot, ot.fecha_entrega_ot,
    ot.kilometraje_ingreso_ot, ot.observacion_cli_ot, ot.observacion_ot,
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
    ote.nombre_ot_est AS estado_ot, ot.cod_ot_est_ot
FROM ordenes_trabajo ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu AND ot.cod_taller = urp.cod_taller
LEFT JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

CREATE OR REPLACE VIEW vw_ot_pendientes WITH (security_invoker = on) AS
SELECT
    ot.consecutivo_ot, ot.fecha_elaboracion_ot,
    (CURRENT_DATE - ot.fecha_elaboracion_ot) AS dias_pendiente,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente, c.telefono_cli,
    m.placa_mot, mar.nombre_mar || ' ' || m.modelo_mot AS moto,
    umc.nombre_usu || ' ' || umc.apellido_1_usu AS mecanico_asignado,
    ote.nombre_ot_est AS estado
FROM ordenes_trabajo ot
INNER JOIN motos m        ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN marcas mar     ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN clientes c     ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
LEFT JOIN usuarios umc    ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est
WHERE ot.fecha_entrega_ot IS NULL
ORDER BY ot.fecha_elaboracion_ot;

CREATE OR REPLACE VIEW vw_reclamos_completo WITH (security_invoker = on) AS
SELECT
    rec.cod_rec, rec.descripcion_rec, rec.consecutivo_ot_rec,
    ot.fecha_elaboracion_ot, ot.fecha_entrega_ot, ot.kilometraje_ingreso_ot,
    ot.observacion_cli_ot, ot.observacion_ot, ot.fecha_fin_garantia_ot,
    ote.nombre_ot_est AS estado_ot,
    m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
    mar.nombre_mar AS marca_moto,
    mar.nombre_mar || ' ' || m.modelo_mot || ' (' || m.placa_mot || ')' AS moto_completa,
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo_cliente,
    c.telefono_cli, c.correo_cli, c.direccion_cli,
    urp.documento_usu AS documento_recepcionista,
    urp.nombre_usu || ' ' || urp.apellido_1_usu AS recepcionista,
    umc.documento_usu AS documento_mecanico,
    umc.nombre_usu || ' ' || umc.apellido_1_usu AS mecanico,
    CASE
        WHEN ot.fecha_fin_garantia_ot >= CURRENT_DATE THEN 'VIGENTE'
        WHEN ot.fecha_fin_garantia_ot <  CURRENT_DATE THEN 'VENCIDA'
        ELSE 'SIN INFORMACIÓN'
    END AS estado_garantia,
    CASE WHEN ot.fecha_fin_garantia_ot >= CURRENT_DATE
         THEN (ot.fecha_fin_garantia_ot - CURRENT_DATE) ELSE NULL END AS dias_garantia_restantes
FROM reclamos rec
INNER JOIN ordenes_trabajo ot ON rec.consecutivo_ot_rec = ot.consecutivo_ot AND rec.cod_taller = ot.cod_taller
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu AND ot.cod_taller = urp.cod_taller
LEFT JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;
