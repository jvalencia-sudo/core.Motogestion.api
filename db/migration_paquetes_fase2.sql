-- ============================================================
-- Migración Fase 2: PAQUETES (combos) en editar/eliminar detalle de OT.
--
-- El INSERT ya explotaba los componentes de un PAQUETE (migration_productos_tipos.sql).
-- Aquí se completa el ciclo: los triggers de UPDATE y DELETE también contemplan
-- PAQUETE, ajustando/revirtiendo el stock de cada componente BIEN. Solo se redefinen
-- las funciones (los triggers ya existen y las referencian).
--
-- Idempotente. Correr como el rol DUEÑO de las tablas (mt_app local).
-- ============================================================

BEGIN;

-- DELETE: al quitar un detalle, revertir stock. PAQUETE devuelve sus componentes BIEN.
CREATE OR REPLACE FUNCTION fn_revertir_stock_detalle()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo TEXT;
    v_ant  INTEGER;
    v_nue  INTEGER;
    v_cant INTEGER;
    r      RECORD;
BEGIN
    SELECT tipo_pro INTO v_tipo FROM productos
     WHERE cod_pro = OLD.cod_pro_deto AND cod_taller = OLD.cod_taller;

    -- Cortesía / no facturable: no se había afectado stock.
    IF OLD.cantidad_deto <= 0 THEN
        RETURN OLD;
    END IF;

    -- PAQUETE: devolver el stock de cada componente BIEN.
    IF v_tipo = 'PAQUETE' THEN
        FOR r IN
            SELECT pc.cod_pro_comp, pc.cantidad_comp, p.tipo_pro AS tipo_comp
              FROM paquete_componentes pc
              JOIN productos p ON p.cod_pro = pc.cod_pro_comp AND p.cod_taller = pc.cod_taller
             WHERE pc.cod_pro_paq = OLD.cod_pro_deto AND pc.cod_taller = OLD.cod_taller
        LOOP
            IF r.tipo_comp = 'BIEN' THEN
                v_cant := (r.cantidad_comp * OLD.cantidad_deto)::integer;
                SELECT stock_pro INTO v_ant FROM productos
                 WHERE cod_pro = r.cod_pro_comp AND cod_taller = OLD.cod_taller;
                v_nue := COALESCE(v_ant, 0) + v_cant;
                UPDATE productos SET stock_pro = v_nue
                 WHERE cod_pro = r.cod_pro_comp AND cod_taller = OLD.cod_taller;
                INSERT INTO movimientos_inventario
                  (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
                   motivo_mov, documento_usu_mov, referencia_mov)
                VALUES
                  (OLD.cod_taller, r.cod_pro_comp, 'AJUSTE', v_cant, v_ant, v_nue,
                   'Reversa componente de paquete', OLD.documento_usu_deto, 'OT #' || OLD.consecutivo_ot_deto);
            END IF;
        END LOOP;
        RETURN OLD;
    END IF;

    -- SERVICIO no mueve stock; solo BIEN.
    IF v_tipo IS DISTINCT FROM 'BIEN' THEN
        RETURN OLD;
    END IF;

    v_cant := OLD.cantidad_deto::integer;
    SELECT stock_pro INTO v_ant FROM productos
     WHERE cod_pro = OLD.cod_pro_deto AND cod_taller = OLD.cod_taller;
    v_nue := COALESCE(v_ant, 0) + v_cant;
    UPDATE productos SET stock_pro = v_nue
     WHERE cod_pro = OLD.cod_pro_deto AND cod_taller = OLD.cod_taller;
    INSERT INTO movimientos_inventario
      (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
       motivo_mov, documento_usu_mov, referencia_mov)
    VALUES
      (OLD.cod_taller, OLD.cod_pro_deto, 'AJUSTE', v_cant, v_ant, v_nue,
       'Reversa por eliminación de OT', OLD.documento_usu_deto, 'OT #' || OLD.consecutivo_ot_deto);
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- UPDATE: al cambiar la cantidad, ajustar por el delta. PAQUETE ajusta sus componentes BIEN.
CREATE OR REPLACE FUNCTION fn_ajustar_stock_detalle()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo   TEXT;
    v_ant    INTEGER;
    v_nue    INTEGER;
    v_old_ef NUMERIC;   -- efecto de la cantidad anterior (0 si cortesía)
    v_new_ef NUMERIC;   -- efecto de la cantidad nueva
    v_delta  INTEGER;
    r        RECORD;
BEGIN
    IF NEW.cod_pro_deto <> OLD.cod_pro_deto THEN
        RETURN NEW;
    END IF;
    IF NEW.cantidad_deto = OLD.cantidad_deto THEN
        RETURN NEW;
    END IF;

    SELECT tipo_pro INTO v_tipo FROM productos
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;

    v_old_ef := CASE WHEN OLD.cantidad_deto > 0 THEN OLD.cantidad_deto ELSE 0 END;
    v_new_ef := CASE WHEN NEW.cantidad_deto > 0 THEN NEW.cantidad_deto ELSE 0 END;

    -- PAQUETE: ajustar cada componente BIEN por el delta de paquetes.
    IF v_tipo = 'PAQUETE' THEN
        FOR r IN
            SELECT pc.cod_pro_comp, pc.cantidad_comp, p.tipo_pro AS tipo_comp
              FROM paquete_componentes pc
              JOIN productos p ON p.cod_pro = pc.cod_pro_comp AND p.cod_taller = pc.cod_taller
             WHERE pc.cod_pro_paq = NEW.cod_pro_deto AND pc.cod_taller = NEW.cod_taller
        LOOP
            IF r.tipo_comp = 'BIEN' THEN
                v_delta := (r.cantidad_comp * (v_new_ef - v_old_ef))::integer;
                IF v_delta <> 0 THEN
                    SELECT stock_pro INTO v_ant FROM productos
                     WHERE cod_pro = r.cod_pro_comp AND cod_taller = NEW.cod_taller;
                    v_nue := COALESCE(v_ant, 0) - v_delta;
                    UPDATE productos SET stock_pro = v_nue
                     WHERE cod_pro = r.cod_pro_comp AND cod_taller = NEW.cod_taller;
                    INSERT INTO movimientos_inventario
                      (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
                       motivo_mov, documento_usu_mov, referencia_mov)
                    VALUES
                      (NEW.cod_taller, r.cod_pro_comp, 'AJUSTE', -v_delta, v_ant, v_nue,
                       'Edición de paquete en OT', NEW.documento_usu_deto, 'OT #' || NEW.consecutivo_ot_deto);
                END IF;
            END IF;
        END LOOP;
        RETURN NEW;
    END IF;

    -- SERVICIO no mueve stock; solo BIEN.
    IF v_tipo IS DISTINCT FROM 'BIEN' THEN
        RETURN NEW;
    END IF;

    v_delta := (v_new_ef - v_old_ef)::integer;
    IF v_delta = 0 THEN
        RETURN NEW;
    END IF;

    SELECT stock_pro INTO v_ant FROM productos
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;
    v_nue := COALESCE(v_ant, 0) - v_delta;
    UPDATE productos SET stock_pro = v_nue
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;
    INSERT INTO movimientos_inventario
      (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
       motivo_mov, documento_usu_mov, referencia_mov)
    VALUES
      (NEW.cod_taller, NEW.cod_pro_deto, 'AJUSTE', -v_delta, v_ant, v_nue,
       'Edición de OT', NEW.documento_usu_deto, 'OT #' || NEW.consecutivo_ot_deto);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMIT;
