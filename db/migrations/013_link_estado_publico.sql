-- F2-01: link publico de estado de la orden (sin login). Cada orden gana un
-- token aleatorio (no el consecutivo, para que no sea adivinable) y la
-- policy RLS de ordenes_trabajo se extiende para dejar ver (SOLO lectura,
-- nunca escritura) la fila cuyo token coincide con el que fija el endpoint
-- publico -- ver repository/ordenes_trabajo/orden_trabajo_publica_repositorio.py.
-- El resto de la fila sigue aislado por tenant exactamente igual que siempre.

ALTER TABLE ordenes_trabajo
    ADD COLUMN token_publico UUID NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE ordenes_trabajo
    ADD CONSTRAINT ux_ordenes_trabajo_token_publico UNIQUE (token_publico);

-- Toggle por taller: ¿se muestran items y total en el link publico, o solo
-- el estado? (default: mostrar, igual que el resto de toggles de F1-09).
ALTER TABLE talleres
    ADD COLUMN mostrar_detalle_publico_tal BOOLEAN NOT NULL DEFAULT true;

-- Reemplaza la policy generica de ordenes_trabajo (creada en el loop de
-- full_schema_v2_multitenant.sql) por una que ADEMAS deja ver la fila cuyo
-- token_publico coincida con el GUC app.public_order_token. WITH CHECK NO
-- lleva esa condicion: un visitante publico nunca puede insertar/actualizar,
-- solo el tenant dueno de la fila (igual que antes).
-- NULLIF (no solo `current_setting(..., true)`) es necesario: un GUC custom
-- que NUNCA se tocó en la sesión da NULL con el 2do argumento en true, pero
-- en cuanto se le hace UN set_config (aunque sea dentro de una transacción
-- que termina en ROLLBACK) Postgres lo deja en '' para el resto de la
-- sesión/conexión -- y como el pool reutiliza conexiones entre requests,
-- '' ::uuid reventaria CUALQUIER SELECT futuro sobre ordenes_trabajo en esa
-- misma conexión. NULLIF(..., '') trata ese '' residual igual que "nunca
-- seteado" (NULL), sin romper nada.
DROP POLICY IF EXISTS tenant_isolation ON ordenes_trabajo;
CREATE POLICY tenant_isolation ON ordenes_trabajo
    USING (
        cod_taller = current_setting('app.tenant_id', true)::integer
        OR token_publico = NULLIF(current_setting('app.public_order_token', true), '')::uuid
    )
    WITH CHECK (cod_taller = current_setting('app.tenant_id', true)::integer);

-- Vista: anadir token_publico AL FINAL del SELECT (Postgres no permite
-- reordenar columnas de una vista existente con CREATE OR REPLACE). FROM/JOIN
-- copiados tal cual de full_schema_v2_multitenant.sql, sin reescribirlos de
-- memoria. ::text porque el resto del backend lee filas como dict de
-- strings/numeros (psycopg devolveria un uuid.UUID nativo si no se castea).
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
    c.tipo_documento_cli, m.ciudad_placa_mot,
    ot.token_publico::text AS token_publico
FROM ordenes_trabajo ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu AND ot.cod_taller = urp.cod_taller
LEFT JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

-- Feature flag para quitar el pie "Hecho con MotoGestion" en planes de pago
-- (mismo mecanismo que ya usan reportes/multi_sucursal, ver planes.features).
UPDATE planes SET features = features || '{"sin_marca_motogestion": true}'::jsonb
    WHERE nombre_plan IN ('Taller', 'Premium');
