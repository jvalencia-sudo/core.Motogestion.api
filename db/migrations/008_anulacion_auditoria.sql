-- F1-05: auditoría con usuario real (fn_audit nunca escribía audit_log.usuario,
-- quedaba siempre session_user = mt_app) + anular (no eliminar) una orden de
-- trabajo, con motivo obligatorio, devolución de stock y registro de quién y
-- cuándo. Reutiliza el estado 5 ("Cancelada" -> "Anulada").

-- 1. Renombrar estado 5.
UPDATE ot_estados SET nombre_ot_est = 'Anulada' WHERE cod_ot_est = 5;

-- 2. Columnas de anulación en ordenes_trabajo.
ALTER TABLE ordenes_trabajo
    ADD COLUMN motivo_anulacion_ot         VARCHAR(500),
    ADD COLUMN fecha_anulacion_ot          TIMESTAMP,
    ADD COLUMN documento_usu_anulacion_ot  VARCHAR(11);

ALTER TABLE ordenes_trabajo
    ADD CONSTRAINT fk_ot_anulacion
    FOREIGN KEY (cod_taller, documento_usu_anulacion_ot) REFERENCES usuarios (cod_taller, documento_usu);

-- 3. fn_audit: usa app.usuario (seteado por el backend en _apply_tenant junto
--    con app.tenant_id), cae a session_user si no viene nada (scripts/psql
--    directo contra la BD).
CREATE OR REPLACE FUNCTION fn_audit()
RETURNS TRIGGER AS $$
DECLARE
    v_taller  INTEGER;
    v_usuario VARCHAR(100);
BEGIN
    v_usuario := current_setting('app.usuario', true);
    IF v_usuario IS NULL OR v_usuario = '' THEN
        v_usuario := session_user;
    END IF;

    IF TG_OP = 'DELETE' THEN
        v_taller := OLD.cod_taller;
        INSERT INTO audit_log (cod_taller, usuario, tabla, evento, valor_anterior)
        VALUES (v_taller, v_usuario, TG_TABLE_NAME, 'D', to_jsonb(OLD));
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        v_taller := NEW.cod_taller;
        INSERT INTO audit_log (cod_taller, usuario, tabla, evento, valor_anterior, valor_nuevo)
        VALUES (v_taller, v_usuario, TG_TABLE_NAME, 'U', to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSE
        v_taller := NEW.cod_taller;
        INSERT INTO audit_log (cod_taller, usuario, tabla, evento, valor_nuevo)
        VALUES (v_taller, v_usuario, TG_TABLE_NAME, 'I', to_jsonb(NEW));
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 4. vw_ordenes_trabajo_completa: agrega las 3 columnas nuevas AL FINAL del
--    SELECT (Postgres no permite reordenar columnas de una vista existente
--    con CREATE OR REPLACE, solo añadir al final -- mismo motivo que en la
--    migración 006).
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
    ot.motivo_anulacion_ot, ot.fecha_anulacion_ot, ot.documento_usu_anulacion_ot
FROM ordenes_trabajo ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu AND ot.cod_taller = urp.cod_taller
LEFT JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;
