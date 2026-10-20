-- F1-04: la garantía de una orden la fijaba un trigger con el número de días
-- configurado en "Mi taller" (dias_garantia_pred), igual para toda orden sin
-- importar qué se hizo -- el campo manual del formulario (con su validación
-- de "mínimo 30 días") nunca tenía efecto, porque el trigger la pisaba
-- siempre al entregar. Ahora la garantía la da el servicio/producto más
-- largo de la orden (MAX(dias_garantia_pro) de sus ítems); 0 = sin garantía.

ALTER TABLE talleres DROP COLUMN dias_garantia_pred;

ALTER TABLE productos
    ADD COLUMN dias_garantia_pro INTEGER NOT NULL DEFAULT 0;

CREATE OR REPLACE FUNCTION fn_calc_fecha_garantia()
RETURNS TRIGGER AS $$
DECLARE
    v_dias_garantia INTEGER;
BEGIN
    IF NEW.cod_ot_est_ot = 4 THEN
        SELECT COALESCE(MAX(p.dias_garantia_pro), 0) INTO v_dias_garantia
        FROM detalle_orden_trabajo d
        JOIN productos p ON d.cod_pro_deto = p.cod_pro AND d.cod_taller = p.cod_taller
        WHERE d.consecutivo_ot_deto = NEW.consecutivo_ot AND d.cod_taller = NEW.cod_taller;

        IF v_dias_garantia > 0 AND NEW.fecha_entrega_ot IS NOT NULL THEN
            NEW.fecha_fin_garantia_ot := NEW.fecha_entrega_ot + make_interval(days => v_dias_garantia);
        ELSE
            NEW.fecha_fin_garantia_ot := NULL;
        END IF;
    ELSE
        NEW.fecha_fin_garantia_ot := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- vw_productos / vw_productos_activos: agregan dias_garantia_pro AL FINAL del
-- SELECT (Postgres no permite reordenar columnas de una vista existente con
-- CREATE OR REPLACE, solo añadir al final -- mismo motivo que en 006/008).
CREATE OR REPLACE VIEW vw_productos WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
       p.stock_pro, p.stock_pro_min, p.unidad_pro, p.cod_est_pro, e.nombre_est AS estado_producto,
       p.tipo_pro, p.dias_garantia_pro
FROM productos p INNER JOIN estados e ON p.cod_est_pro = e.cod_est;

CREATE OR REPLACE VIEW vw_productos_activos WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
       p.stock_pro, p.stock_pro_min, p.unidad_pro, p.cod_est_pro, e.nombre_est AS estado_producto,
       p.tipo_pro, p.dias_garantia_pro
FROM productos p INNER JOIN estados e ON p.cod_est_pro = e.cod_est
WHERE p.cod_est_pro = 1;
