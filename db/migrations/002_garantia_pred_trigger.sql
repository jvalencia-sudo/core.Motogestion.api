-- F0-13 (revisión): el trigger de garantía pisaba SIEMPRE fecha_fin_garantia_ot
-- con "entrega + 1 mes" fijo, sin importar qué hubiera calculado la app (con
-- el dias_garantia_pred configurado en "Mi taller") -- dias_garantia_pred no
-- tenía ningún efecto real.
--
-- Esto es DDL (CREATE OR REPLACE FUNCTION), no toca filas -- no necesita fijar
-- app.tenant_id.

CREATE OR REPLACE FUNCTION fn_calc_fecha_garantia()
RETURNS TRIGGER AS $$
DECLARE
    v_dias_garantia INTEGER;
    v_debe_calcular BOOLEAN;
BEGIN
    IF NEW.cod_ot_est_ot = 4 THEN
        IF TG_OP = 'INSERT' THEN
            v_debe_calcular := NEW.fecha_fin_garantia_ot IS NULL;
        ELSE
            v_debe_calcular := NEW.fecha_fin_garantia_ot IS NOT DISTINCT FROM OLD.fecha_fin_garantia_ot;
        END IF;

        IF v_debe_calcular AND NEW.fecha_entrega_ot IS NOT NULL THEN
            SELECT dias_garantia_pred INTO v_dias_garantia
            FROM talleres WHERE cod_taller = NEW.cod_taller;
            NEW.fecha_fin_garantia_ot :=
                NEW.fecha_entrega_ot + make_interval(days => COALESCE(v_dias_garantia, 30));
        END IF;
    ELSE
        NEW.fecha_fin_garantia_ot := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Órdenes ya entregadas ANTES de este fix pueden tener fecha_fin_garantia_ot
-- calculada con el "+1 mes" viejo en vez del dias_garantia_pred real del
-- taller. Si hace falta corregir datos históricos, hacerlo taller por taller,
-- fijando el tenant primero (ordenes_trabajo SÍ tiene RLS) y verificando las
-- filas afectadas antes de confiar en el resultado -- esto es aparte, manual,
-- NO lo corre scripts/migrate.py (es un UPDATE condicional, no DDL idempotente):
--
--   BEGIN;
--   SELECT set_config('app.tenant_id', '<cod_taller>', true);
--   UPDATE ordenes_trabajo o
--   SET fecha_fin_garantia_ot = o.fecha_entrega_ot
--       + make_interval(days => (SELECT dias_garantia_pred FROM talleres WHERE cod_taller = o.cod_taller))
--   WHERE o.cod_ot_est_ot = 4 AND o.fecha_entrega_ot IS NOT NULL;
--   -- Revisa cuántas filas dice "UPDATE N" antes de decidir COMMIT o ROLLBACK.
--   COMMIT;
