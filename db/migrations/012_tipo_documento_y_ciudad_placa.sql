-- Rediseno del PDF de orden de trabajo: la plantilla nueva necesita el tipo
-- de documento del cliente (CC/CE/NIT/Pasaporte) y la ciudad de matricula de
-- la placa, que no existian. ALTER TABLE ADD COLUMN es DDL y no pasa por
-- RLS (solo afecta DML sobre filas existentes), asi que no hace falta loop
-- de tenant -- igual que 011_personalizacion_pdf.sql.

ALTER TABLE clientes
    ADD COLUMN tipo_documento_cli VARCHAR(10) NOT NULL DEFAULT 'CC';
ALTER TABLE clientes
    ADD CONSTRAINT chk_cliente_tipo_documento
    CHECK (tipo_documento_cli IN ('CC', 'CE', 'NIT', 'PASAPORTE'));

ALTER TABLE motos
    ADD COLUMN ciudad_placa_mot VARCHAR(40);  -- nullable: dato nuevo, nadie lo tiene hoy

-- Vistas: anadir las columnas nuevas AL FINAL del SELECT (Postgres no
-- permite reordenar columnas de una vista existente con CREATE OR REPLACE).
-- FROM/JOIN copiados tal cual de full_schema_v2_multitenant.sql, sin
-- reescribirlos de memoria.

CREATE OR REPLACE VIEW vw_clientes WITH (security_invoker = on) AS
SELECT c.documento_cli, c.nombre_cli, c.apellido_1_cli, c.apellido_2_cli,
       c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo,
       c.telefono_cli, c.correo_cli, c.direccion_cli,
       c.tipo_documento_cli
FROM clientes c;

CREATE OR REPLACE VIEW vw_clientes_resumen WITH (security_invoker = on) AS
SELECT c.documento_cli,
       c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo,
       c.telefono_cli, c.correo_cli, c.direccion_cli,
       COUNT(m.placa_mot) AS total_motos,
       c.tipo_documento_cli
FROM clientes c
LEFT JOIN motos m ON c.documento_cli = m.documento_cli_mot AND c.cod_taller = m.cod_taller
GROUP BY c.documento_cli, c.nombre_cli, c.apellido_1_cli, c.apellido_2_cli,
         c.telefono_cli, c.correo_cli, c.direccion_cli, c.tipo_documento_cli;

CREATE OR REPLACE VIEW vw_motos WITH (security_invoker = on) AS
SELECT m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
       m.documento_cli_mot, m.cod_marca_mot,
       m.ciudad_placa_mot
FROM motos m;

CREATE OR REPLACE VIEW vw_motos_marcas WITH (security_invoker = on) AS
SELECT m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
       m.documento_cli_mot, m.cod_marca_mot, mar.nombre_mar AS marca,
       m.ciudad_placa_mot
FROM motos m INNER JOIN marcas mar ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller;

CREATE OR REPLACE VIEW vw_motos_detalle WITH (security_invoker = on) AS
SELECT m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
       mar.nombre_mar AS marca, c.documento_cli,
       c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo_cliente,
       c.telefono_cli, c.correo_cli,
       m.ciudad_placa_mot
FROM motos m
INNER JOIN marcas mar ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN clientes c ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller;

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
    ot.kilometraje_salida_ot,
    ot.motivo_anulacion_ot, ot.fecha_anulacion_ot, ot.documento_usu_anulacion_ot,
    c.tipo_documento_cli, m.ciudad_placa_mot
FROM ordenes_trabajo ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu AND ot.cod_taller = urp.cod_taller
LEFT JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;
