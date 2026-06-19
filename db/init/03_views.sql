-- ============================================================
-- 03_views.sql
-- Vistas (migradas de Oracle ScripVistas.sql)
-- Cambios Oracle -> Postgres:
--   * SYSDATE                 -> CURRENT_DATE
--   * TRUNC(SYSDATE - fecha)  -> (CURRENT_DATE - fecha)   [resta de date da entero de dias]
--   * Se omite la vista duplicada Oracle "US_PPI"."VW_PRODUCTOS_CON_IMPUESTOS"
--   * || (concatenacion), COALESCE, ROUND, ABS, CASE: validos en Postgres tal cual
-- ============================================================

-- ----- Ordenes de trabajo -----

CREATE OR REPLACE VIEW vw_ordenes_trabajo_completa AS
SELECT
    ot.consecutivo_ot,
    ot.fecha_elaboracion_ot,
    ot.fecha_entrega_ot,
    ot.kilometraje_ingreso_ot,
    ot.observacion_cli_ot,
    ot.observacion_ot,
    ot.fecha_fin_garantia_ot,
    m.placa_mot,
    m.modelo_mot,
    m.color_mot,
    m.cilindraje_mot,
    mar.nombre_mar AS marca_moto,
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo_cliente,
    c.telefono_cli,
    c.correo_cli,
    c.direccion_cli,
    urp.documento_usu AS documento_recepcionista,
    urp.nombre_usu || ' ' || urp.apellido_1_usu AS recepcionista,
    umc.documento_usu AS documento_mecanico,
    umc.nombre_usu || ' ' || umc.apellido_1_usu AS mecanico,
    ote.nombre_ot_est AS estado_ot,
    ot.cod_ot_est_ot
FROM ordenes_trabajo ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu
INNER JOIN usuarios umc  ON ot.documento_usu_mc_ot = umc.documento_usu
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

CREATE OR REPLACE VIEW vw_detalle_ot_productos AS
SELECT
    dot.consecutivo_ot_deto,
    dot.cod_pro_deto,
    p.nombre_pro,
    p.descripcion_pro,
    dot.cantidad_deto,
    dot.valor_unitario_deto,
    (ABS(dot.cantidad_deto) * dot.valor_unitario_deto) AS subtotal,
    dot.fecha_confirmacion_deto,
    u.nombre_usu || ' ' || u.apellido_1_usu AS usuario_confirmacion,
    e.nombre_est AS estado_producto
FROM detalle_orden_trabajo dot
INNER JOIN productos p ON dot.cod_pro_deto = p.cod_pro
INNER JOIN usuarios u  ON dot.documento_usu_deto = u.documento_usu
INNER JOIN estados e   ON p.cod_est_pro = e.cod_est;

CREATE OR REPLACE VIEW vw_resumen_financiero_ot AS
SELECT
    ot.consecutivo_ot,
    ot.fecha_elaboracion_ot,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente,
    m.placa_mot,
    COUNT(CASE WHEN dot.cantidad_deto > 0 THEN dot.cod_pro_deto END) AS total_items,
    SUM(CASE WHEN dot.cantidad_deto > 0 THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS subtotal_productos,
    0 AS total_impuestos,
    SUM(CASE WHEN dot.cantidad_deto > 0 THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS total_ot
FROM ordenes_trabajo ot
INNER JOIN detalle_orden_trabajo dot ON ot.consecutivo_ot = dot.consecutivo_ot_deto
INNER JOIN motos m    ON ot.placa_mot_ot = m.placa_mot
INNER JOIN clientes c ON m.documento_cli_mot = c.documento_cli
GROUP BY ot.consecutivo_ot, ot.fecha_elaboracion_ot, c.nombre_cli, c.apellido_1_cli, m.placa_mot;

CREATE OR REPLACE VIEW vw_ot_pendientes AS
SELECT
    ot.consecutivo_ot,
    ot.fecha_elaboracion_ot,
    (CURRENT_DATE - ot.fecha_elaboracion_ot) AS dias_pendiente,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente,
    c.telefono_cli,
    m.placa_mot,
    mar.nombre_mar || ' ' || m.modelo_mot AS moto,
    umc.nombre_usu || ' ' || umc.apellido_1_usu AS mecanico_asignado,
    ote.nombre_ot_est AS estado
FROM ordenes_trabajo ot
INNER JOIN motos m        ON ot.placa_mot_ot = m.placa_mot
INNER JOIN marcas mar     ON m.cod_marca_mot = mar.cod_mar
INNER JOIN clientes c     ON m.documento_cli_mot = c.documento_cli
INNER JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est
WHERE ot.fecha_entrega_ot IS NULL
ORDER BY ot.fecha_elaboracion_ot;

CREATE OR REPLACE VIEW vw_reclamos_completo AS
SELECT
    rec.cod_rec,
    rec.descripcion_rec,
    rec.consecutivo_ot_rec,
    ot.fecha_elaboracion_ot,
    ot.fecha_entrega_ot,
    ot.kilometraje_ingreso_ot,
    ot.observacion_cli_ot,
    ot.observacion_ot,
    ot.fecha_fin_garantia_ot,
    ote.nombre_ot_est AS estado_ot,
    m.placa_mot,
    m.modelo_mot,
    m.color_mot,
    m.cilindraje_mot,
    mar.nombre_mar AS marca_moto,
    mar.nombre_mar || ' ' || m.modelo_mot || ' (' || m.placa_mot || ')' AS moto_completa,
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo_cliente,
    c.telefono_cli,
    c.correo_cli,
    c.direccion_cli,
    urp.documento_usu AS documento_recepcionista,
    urp.nombre_usu || ' ' || urp.apellido_1_usu AS recepcionista,
    umc.documento_usu AS documento_mecanico,
    umc.nombre_usu || ' ' || umc.apellido_1_usu AS mecanico,
    CASE
        WHEN ot.fecha_fin_garantia_ot >= CURRENT_DATE THEN 'VIGENTE'
        WHEN ot.fecha_fin_garantia_ot <  CURRENT_DATE THEN 'VENCIDA'
        ELSE 'SIN INFORMACIÓN'
    END AS estado_garantia,
    CASE
        WHEN ot.fecha_fin_garantia_ot >= CURRENT_DATE
        THEN (ot.fecha_fin_garantia_ot - CURRENT_DATE)
        ELSE NULL
    END AS dias_garantia_restantes
FROM reclamos rec
INNER JOIN ordenes_trabajo ot ON rec.consecutivo_ot_rec = ot.consecutivo_ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu
INNER JOIN usuarios umc  ON ot.documento_usu_mc_ot = umc.documento_usu
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

CREATE OR REPLACE VIEW vw_reclamos_detalle AS
SELECT
    rec.cod_rec,
    rec.descripcion_rec,
    ot.consecutivo_ot,
    ot.fecha_elaboracion_ot,
    ot.fecha_entrega_ot,
    m.placa_mot,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente,
    c.telefono_cli,
    ote.nombre_ot_est AS estado_ot
FROM reclamos rec
INNER JOIN ordenes_trabajo ot ON rec.consecutivo_ot_rec = ot.consecutivo_ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

-- ----- Productos / impuestos -----

CREATE OR REPLACE VIEW vw_productos AS
SELECT
    p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
    p.stock_pro, p.stock_pro_min, p.cod_est_pro,
    e.nombre_est AS estado_producto
FROM productos p
INNER JOIN estados e ON p.cod_est_pro = e.cod_est;

CREATE OR REPLACE VIEW vw_productos_activos AS
SELECT
    p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
    p.stock_pro, p.stock_pro_min, p.cod_est_pro,
    e.nombre_est AS estado_producto
FROM productos p
INNER JOIN estados e ON p.cod_est_pro = e.cod_est
WHERE p.cod_est_pro = 1;

CREATE OR REPLACE VIEW vw_productos_impuestos AS
SELECT
    pi.cod_pro_imp, pi.cod_imp_pro_imp, pi.cod_pro_pro_imp, pi.porcentaje_pro_imp,
    i.cod_imp, i.nombre_imp, i.porcentaje_imp
FROM productos_impuestos pi
INNER JOIN impuestos i ON pi.cod_imp_pro_imp = i.cod_imp;

CREATE OR REPLACE VIEW vw_productos_con_impuestos AS
SELECT
    p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
    p.stock_pro, p.stock_pro_min,
    e.nombre_est AS estado_producto,
    pi.cod_pro_imp, i.nombre_imp, pi.porcentaje_pro_imp,
    ROUND(p.precio_pro * (pi.porcentaje_pro_imp / 100), 2) AS valor_impuesto,
    ROUND(p.precio_pro + (p.precio_pro * (pi.porcentaje_pro_imp / 100)), 2) AS precio_con_impuesto
FROM productos p
INNER JOIN estados e ON p.cod_est_pro = e.cod_est
LEFT JOIN productos_impuestos pi ON p.cod_pro = pi.cod_pro_pro_imp
LEFT JOIN impuestos i ON pi.cod_imp_pro_imp = i.cod_imp;

CREATE OR REPLACE VIEW vw_inventario_alertas AS
SELECT
    p.cod_pro, p.nombre_pro, p.descripcion_pro,
    p.stock_pro, p.stock_pro_min, p.precio_pro,
    e.nombre_est AS estado,
    CASE
        WHEN p.stock_pro = 0 THEN 'SIN STOCK'
        WHEN p.stock_pro <= p.stock_pro_min THEN 'STOCK BAJO'
        WHEN p.stock_pro > p.stock_pro_min AND p.stock_pro <= (p.stock_pro_min * 2) THEN 'STOCK MEDIO'
        ELSE 'STOCK NORMAL'
    END AS nivel_alerta,
    (p.stock_pro_min - p.stock_pro) AS cantidad_a_pedir
FROM productos p
INNER JOIN estados e ON p.cod_est_pro = e.cod_est;

-- ----- Clientes -----

CREATE OR REPLACE VIEW vw_clientes AS
SELECT
    c.documento_cli, c.nombre_cli, c.apellido_1_cli, c.apellido_2_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo,
    c.telefono_cli, c.correo_cli, c.direccion_cli
FROM clientes c;

CREATE OR REPLACE VIEW vw_clientes_resumen AS
SELECT
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo,
    c.telefono_cli, c.correo_cli, c.direccion_cli,
    COUNT(m.placa_mot) AS total_motos
FROM clientes c
LEFT JOIN motos m ON c.documento_cli = m.documento_cli_mot
GROUP BY c.documento_cli, c.nombre_cli, c.apellido_1_cli, c.apellido_2_cli,
         c.telefono_cli, c.correo_cli, c.direccion_cli;

CREATE OR REPLACE VIEW vw_clientes_motos AS
SELECT
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo,
    c.telefono_cli, c.correo_cli, c.direccion_cli,
    m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
    mar.nombre_mar AS marca
FROM clientes c
INNER JOIN motos m   ON c.documento_cli = m.documento_cli_mot
INNER JOIN marcas mar ON m.cod_marca_mot = mar.cod_mar;

-- ----- Motos -----

CREATE OR REPLACE VIEW vw_motos AS
SELECT m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
       m.documento_cli_mot, m.cod_marca_mot
FROM motos m;

CREATE OR REPLACE VIEW vw_motos_marcas AS
SELECT m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
       m.documento_cli_mot, m.cod_marca_mot,
       mar.nombre_mar AS marca
FROM motos m
INNER JOIN marcas mar ON m.cod_marca_mot = mar.cod_mar;

CREATE OR REPLACE VIEW vw_motos_detalle AS
SELECT
    m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
    mar.nombre_mar AS marca,
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo_cliente,
    c.telefono_cli, c.correo_cli
FROM motos m
INNER JOIN marcas mar ON m.cod_marca_mot = mar.cod_mar
INNER JOIN clientes c ON m.documento_cli_mot = c.documento_cli;

-- ----- Marcas -----

CREATE OR REPLACE VIEW vw_marcas AS
SELECT mar.cod_mar, mar.nombre_mar FROM marcas mar;

CREATE OR REPLACE VIEW vw_marcas_resumen AS
SELECT mar.cod_mar, mar.nombre_mar, COUNT(m.placa_mot) AS total_motos
FROM marcas mar
LEFT JOIN motos m ON mar.cod_mar = m.cod_marca_mot
GROUP BY mar.cod_mar, mar.nombre_mar;

CREATE OR REPLACE VIEW vw_marcas_motos AS
SELECT mar.cod_mar, mar.nombre_mar,
       m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot
FROM marcas mar
LEFT JOIN motos m ON mar.cod_mar = m.cod_marca_mot;

-- ----- Auth: usuarios / perfiles / permisos -----

CREATE OR REPLACE VIEW vw_usuarios_perfiles AS
SELECT
    u.documento_usu,
    u.nombre_usu || ' ' || u.apellido_1_usu || ' ' || COALESCE(u.apellido_2_usu, '') AS nombre_completo,
    u.correo_usu,
    u.cod_tipo_usu,
    e.nombre_est AS estado_usuario,
    p.nombre_prf AS perfil,
    p.descripcion_prf AS descripcion_perfil,
    r.nombre_rol AS rol,
    r.descripcion_rol AS descripcion_rol
FROM usuarios u
INNER JOIN estados e  ON u.cod_est_usu = e.cod_est
INNER JOIN perfiles p ON u.cod_prf_usu = p.cod_prf AND u.cod_rol_prf_usu = p.cod_rol_prf
INNER JOIN roles r    ON p.cod_rol_prf = r.cod_rol;

CREATE OR REPLACE VIEW vw_perfiles AS
SELECT
    p.cod_prf, p.nombre_prf, p.descripcion_prf,
    e.nombre_est AS nombre_est_prf,
    r.nombre_rol AS nombre_rol_prf
FROM perfiles p
INNER JOIN estados e ON p.cod_est_prf = e.cod_est
INNER JOIN roles r   ON p.cod_rol_prf = r.cod_rol
ORDER BY p.cod_prf;

CREATE OR REPLACE VIEW vw_perfiles_permisos_detalle AS
SELECT
    pf.cod_prf, pf.nombre_prf, r.nombre_rol,
    pm.cod_prm, pm.nombre_prm, pm.descripcion_prm,
    v.nombre_vis, v.ruta_vis,
    e.nombre_est AS estado_permiso
FROM perfiles_permisos pp
INNER JOIN perfiles pf ON pp.cod_prf_pp = pf.cod_prf AND pp.cod_rol_prf_pp = pf.cod_rol_prf
INNER JOIN roles r     ON pf.cod_rol_prf = r.cod_rol
INNER JOIN permisos pm ON pp.cod_prm_pp = pm.cod_prm
INNER JOIN vistas v    ON pm.ruta_vis_prm = v.ruta_vis
INNER JOIN estados e   ON pp.cod_est_pp = e.cod_est;

-- vw_permisos: no existia en los scripts Oracle y el repo la ordena por una
-- columna inexistente (cod_rol_prm). Se crea una version best-effort para que
-- el endpoint no falle: lista los permisos con una columna cod_rol_prm nula.
CREATE OR REPLACE VIEW vw_permisos AS
SELECT
    p.cod_prm, p.nombre_prm, p.descripcion_prm, p.ruta_vis_prm,
    NULL::INTEGER AS cod_rol_prm
FROM permisos p;
