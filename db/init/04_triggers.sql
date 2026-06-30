-- ============================================================
-- 04_triggers.sql
-- Triggers FUNCIONALES en PL/pgSQL.
-- Se portan SOLO los que afectan datos (decision de alcance):
--   * tg_actualizar_stock     -> descuenta stock al insertar un detalle
--   * tg_gen_consecutivo_ot   -> genera consecutivo_ot = MAX+1 si viene NULL
--   * tg_calc_fecha_garantia  -> calcula fecha_fin_garantia_ot (1 mes) si estado=4
-- Se OMITEN las validaciones de formato (email/placa/telefono/rangos) y
-- tg_alerta_stock_bajo (lanzaba error en UPDATE, bloqueante).
-- ============================================================

-- ----- Descontar stock al confirmar un detalle de OT -----
CREATE OR REPLACE FUNCTION fn_actualizar_stock()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE productos
       SET stock_pro = stock_pro - NEW.cantidad_deto
     WHERE cod_pro = NEW.cod_pro_deto;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_actualizar_stock
AFTER INSERT ON detalle_orden_trabajo
FOR EACH ROW
EXECUTE FUNCTION fn_actualizar_stock();

-- ----- Generar consecutivo de la orden de trabajo (MAX+1) -----
CREATE OR REPLACE FUNCTION fn_gen_consecutivo_ot()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.consecutivo_ot IS NULL THEN
        SELECT COALESCE(MAX(consecutivo_ot), 0) + 1
          INTO NEW.consecutivo_ot
          FROM ordenes_trabajo;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_gen_consecutivo_ot
BEFORE INSERT ON ordenes_trabajo
FOR EACH ROW
EXECUTE FUNCTION fn_gen_consecutivo_ot();

-- ----- Calcular fecha fin de garantia (1 mes desde entrega si estado = 4) -----
CREATE OR REPLACE FUNCTION fn_calc_fecha_garantia()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.cod_ot_est_ot = 4 THEN
        IF NEW.fecha_entrega_ot IS NOT NULL THEN
            NEW.fecha_fin_garantia_ot := (NEW.fecha_entrega_ot + INTERVAL '1 month')::date;
        END IF;
    ELSE
        NEW.fecha_fin_garantia_ot := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_calc_fecha_garantia
BEFORE INSERT OR UPDATE ON ordenes_trabajo
FOR EACH ROW
EXECUTE FUNCTION fn_calc_fecha_garantia();
