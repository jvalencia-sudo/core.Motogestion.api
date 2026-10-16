-- ============================================================
-- Migración: TIPOS DE PRODUCTO + MANO DE OBRA + PAQUETES (combos)
--
-- Introduce productos.tipo_pro con tres tipos:
--   * BIEN     -> repuesto/insumo. Afecta inventario (como hasta hoy).
--   * SERVICIO -> mano de obra. NO afecta inventario. Se cobra por horas/cantidad.
--   * PAQUETE  -> combo de precio fijo. No descuenta stock por sí mismo; al usarse
--                 en una OT "explota" sus componentes y descuenta los que sean BIEN.
--
-- Además:
--   * detalle_orden_trabajo.cantidad_deto pasa a NUMERIC (permite medias horas).
--   * tabla paquete_componentes (la "receta" de cada combo), con RLS por taller.
--   * config de mano de obra por taller (modo + tarifa/hora por defecto).
--   * el trigger de stock contempla los 3 tipos.
--
-- Idempotente. Correr como el rol DUEÑO de las tablas (mt_app local / motogestion prod),
-- igual que db/migration_inventario.sql.
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. Tipo de producto
-- ------------------------------------------------------------
ALTER TABLE productos ADD COLUMN IF NOT EXISTS tipo_pro VARCHAR(10) NOT NULL DEFAULT 'BIEN';

ALTER TABLE productos DROP CONSTRAINT IF EXISTS chk_producto_tipo;
ALTER TABLE productos ADD CONSTRAINT chk_producto_tipo
    CHECK (tipo_pro IN ('BIEN', 'SERVICIO', 'PAQUETE'));

-- Los SERVICIO y PAQUETE no manejan stock: se deja explícito en NULL para no confundir.
UPDATE productos SET stock_pro = NULL, stock_pro_min = NULL
 WHERE tipo_pro IN ('SERVICIO', 'PAQUETE');

-- ------------------------------------------------------------
-- 2. Medias horas: la cantidad de un detalle puede ser fraccionaria
--    (p.ej. 1.5 h de mano de obra). Los BIEN se siguen usando en enteros.
--    Hay vistas que dependen de la columna: se dropean, se cambia el tipo y se
--    recrean idénticas (la aritmética ABS/SUM es compatible con NUMERIC).
-- ------------------------------------------------------------
DROP VIEW IF EXISTS vw_detalle_ot_productos;
DROP VIEW IF EXISTS vw_resumen_financiero_ot;

ALTER TABLE detalle_orden_trabajo ALTER COLUMN cantidad_deto TYPE NUMERIC(10, 2);

CREATE VIEW vw_detalle_ot_productos WITH (security_invoker = on) AS
SELECT
    dot.consecutivo_ot_deto, dot.cod_pro_deto,
    p.nombre_pro, p.descripcion_pro, dot.cantidad_deto, dot.valor_unitario_deto,
    (ABS(dot.cantidad_deto) * dot.valor_unitario_deto) AS subtotal,
    dot.fecha_confirmacion_deto,
    u.nombre_usu || ' ' || u.apellido_1_usu AS usuario_confirmacion,
    e.nombre_est AS estado_producto
FROM detalle_orden_trabajo dot
INNER JOIN productos p ON dot.cod_pro_deto = p.cod_pro AND dot.cod_taller = p.cod_taller
INNER JOIN usuarios u  ON dot.documento_usu_deto = u.documento_usu AND dot.cod_taller = u.cod_taller
INNER JOIN estados e   ON p.cod_est_pro = e.cod_est;

CREATE VIEW vw_resumen_financiero_ot WITH (security_invoker = on) AS
SELECT
    ot.consecutivo_ot, ot.fecha_elaboracion_ot,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente, m.placa_mot,
    COUNT(CASE WHEN dot.cantidad_deto > 0 THEN dot.cod_pro_deto END) AS total_items,
    SUM(CASE WHEN dot.cantidad_deto > 0 THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS subtotal_productos,
    0 AS total_impuestos,
    SUM(CASE WHEN dot.cantidad_deto > 0 THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS total_ot
FROM ordenes_trabajo ot
INNER JOIN detalle_orden_trabajo dot ON ot.consecutivo_ot = dot.consecutivo_ot_deto AND ot.cod_taller = dot.cod_taller
INNER JOIN motos m    ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
GROUP BY ot.consecutivo_ot, ot.fecha_elaboracion_ot, c.nombre_cli, c.apellido_1_cli, m.placa_mot;

-- ------------------------------------------------------------
-- 3. Componentes de un paquete (la "receta"/BOM del combo)
--    Cada PAQUETE incluye N productos (BIEN o SERVICIO) con su cantidad.
--    El precio lo pone el paquete; los componentes solo definen qué se consume.
-- ------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS seq_paquete_componentes START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;

CREATE TABLE IF NOT EXISTS paquete_componentes (
    cod_taller    INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_paq_comp  INTEGER NOT NULL DEFAULT nextval('seq_paquete_componentes'),
    cod_pro_paq   INTEGER NOT NULL,                 -- el paquete (producto tipo PAQUETE)
    cod_pro_comp  INTEGER NOT NULL,                 -- el componente incluido
    cantidad_comp NUMERIC(10, 2) NOT NULL DEFAULT 1,
    CONSTRAINT pk_paq_comp      PRIMARY KEY (cod_taller, cod_paq_comp),
    CONSTRAINT fk_paqc_taller   FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_paqc_paquete  FOREIGN KEY (cod_taller, cod_pro_paq)  REFERENCES productos (cod_taller, cod_pro),
    CONSTRAINT fk_paqc_comp     FOREIGN KEY (cod_taller, cod_pro_comp) REFERENCES productos (cod_taller, cod_pro),
    CONSTRAINT chk_paqc_no_self CHECK (cod_pro_paq <> cod_pro_comp)
);

ALTER TABLE paquete_componentes ENABLE ROW LEVEL SECURITY;
ALTER TABLE paquete_componentes FORCE  ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON paquete_componentes;
CREATE POLICY tenant_isolation ON paquete_componentes
    USING      (cod_taller = current_setting('app.tenant_id', true)::integer)
    WITH CHECK (cod_taller = current_setting('app.tenant_id', true)::integer);

-- ------------------------------------------------------------
-- 4. Configuración de mano de obra por taller
--    HORAS -> tarifa fija por hora (tarifa_hora_pred). El front cobra horas * tarifa.
--    LIBRE -> el usuario pone el valor de la mano de obra a mano en cada OT.
--    (El modelo de datos es el mismo en ambos; el modo solo cambia los defaults del front.)
-- ------------------------------------------------------------
ALTER TABLE talleres ADD COLUMN IF NOT EXISTS modo_mano_obra VARCHAR(10) NOT NULL DEFAULT 'HORAS';
ALTER TABLE talleres DROP CONSTRAINT IF EXISTS chk_taller_modo_mo;
ALTER TABLE talleres ADD CONSTRAINT chk_taller_modo_mo
    CHECK (modo_mano_obra IN ('HORAS', 'LIBRE'));
ALTER TABLE talleres ADD COLUMN IF NOT EXISTS tarifa_hora_pred INTEGER NOT NULL DEFAULT 0;

-- ------------------------------------------------------------
-- 5. Triggers de stock: la BD es la ÚNICA dueña del stock + kardex.
--    INSERT descuenta, UPDATE ajusta el delta, DELETE revierte. El servicio
--    Python ya NO toca stock (evita el doble descuento que existía).
--    Regla de cortesía: cantidad_deto <= 0 (línea no facturable) NO afecta stock.
-- ------------------------------------------------------------

-- 5a. INSERT: descontar al agregar un detalle (contempla los 3 tipos).
CREATE OR REPLACE FUNCTION fn_actualizar_stock()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo TEXT;
    v_ant  INTEGER;
    v_nue  INTEGER;
    v_cant INTEGER;
    r      RECORD;
BEGIN
    SELECT tipo_pro INTO v_tipo FROM productos
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;

    -- SERVICIO (mano de obra): no afecta inventario ni deja movimiento.
    IF v_tipo = 'SERVICIO' THEN
        RETURN NEW;
    END IF;

    -- Cortesía: cantidad no positiva no afecta inventario (línea no facturable).
    IF NEW.cantidad_deto <= 0 THEN
        RETURN NEW;
    END IF;

    -- PAQUETE (combo): no descuenta el paquete en sí; explota sus componentes.
    -- Solo los componentes BIEN descuentan stock; los SERVICIO se ignoran.
    IF v_tipo = 'PAQUETE' THEN
        FOR r IN
            SELECT pc.cod_pro_comp, pc.cantidad_comp, p.tipo_pro AS tipo_comp
              FROM paquete_componentes pc
              JOIN productos p
                ON p.cod_pro = pc.cod_pro_comp AND p.cod_taller = pc.cod_taller
             WHERE pc.cod_pro_paq = NEW.cod_pro_deto
               AND pc.cod_taller  = NEW.cod_taller
        LOOP
            IF r.tipo_comp = 'BIEN' THEN
                -- cantidad del componente * nº de paquetes agregados a la OT
                v_cant := (r.cantidad_comp * NEW.cantidad_deto)::integer;
                SELECT stock_pro INTO v_ant FROM productos
                 WHERE cod_pro = r.cod_pro_comp AND cod_taller = NEW.cod_taller;
                v_nue := COALESCE(v_ant, 0) - v_cant;
                UPDATE productos SET stock_pro = v_nue
                 WHERE cod_pro = r.cod_pro_comp AND cod_taller = NEW.cod_taller;
                INSERT INTO movimientos_inventario
                  (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
                   motivo_mov, documento_usu_mov, referencia_mov)
                VALUES
                  (NEW.cod_taller, r.cod_pro_comp, 'SALIDA', -v_cant, v_ant, v_nue,
                   'Componente de paquete', NEW.documento_usu_deto,
                   'OT #' || NEW.consecutivo_ot_deto);
            END IF;
        END LOOP;
        RETURN NEW;
    END IF;

    -- BIEN: comportamiento normal (descuenta su propio stock y deja SALIDA).
    v_cant := NEW.cantidad_deto::integer;
    SELECT stock_pro INTO v_ant FROM productos
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;
    v_nue := COALESCE(v_ant, 0) - v_cant;
    UPDATE productos SET stock_pro = v_nue
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;
    INSERT INTO movimientos_inventario
      (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
       motivo_mov, documento_usu_mov, referencia_mov)
    VALUES
      (NEW.cod_taller, NEW.cod_pro_deto, 'SALIDA', -v_cant, v_ant, v_nue,
       'Uso en orden de trabajo', NEW.documento_usu_deto, 'OT #' || NEW.consecutivo_ot_deto);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- El trigger de INSERT ya existe (tg_actualizar_stock AFTER INSERT ON detalle_orden_trabajo);
-- basta con haber redefinido la función.

-- 5b. DELETE: revertir el stock al quitar un detalle (solo BIEN facturable).
CREATE OR REPLACE FUNCTION fn_revertir_stock_detalle()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo TEXT;
    v_ant  INTEGER;
    v_nue  INTEGER;
    v_cant INTEGER;
BEGIN
    SELECT tipo_pro INTO v_tipo FROM productos
     WHERE cod_pro = OLD.cod_pro_deto AND cod_taller = OLD.cod_taller;

    -- Solo los BIEN mueven stock. SERVICIO/PAQUETE: sin efecto en Fase 1.
    IF v_tipo IS DISTINCT FROM 'BIEN' THEN
        RETURN OLD;
    END IF;
    -- Cortesía: no había afectado stock, no hay nada que devolver.
    IF OLD.cantidad_deto <= 0 THEN
        RETURN OLD;
    END IF;

    v_cant := OLD.cantidad_deto::integer;
    SELECT stock_pro INTO v_ant FROM productos
     WHERE cod_pro = OLD.cod_pro_deto AND cod_taller = OLD.cod_taller;
    v_nue := COALESCE(v_ant, 0) + v_cant;   -- devolver al stock
    UPDATE productos SET stock_pro = v_nue
     WHERE cod_pro = OLD.cod_pro_deto AND cod_taller = OLD.cod_taller;
    INSERT INTO movimientos_inventario
      (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
       motivo_mov, documento_usu_mov, referencia_mov)
    VALUES
      (OLD.cod_taller, OLD.cod_pro_deto, 'AJUSTE', v_cant, v_ant, v_nue,
       'Reversa por eliminación de OT', OLD.documento_usu_deto,
       'OT #' || OLD.consecutivo_ot_deto);
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tg_revertir_stock ON detalle_orden_trabajo;
CREATE TRIGGER tg_revertir_stock
AFTER DELETE ON detalle_orden_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_revertir_stock_detalle();

-- 5c. UPDATE: ajustar el stock por el delta cuando cambia la cantidad (solo BIEN).
CREATE OR REPLACE FUNCTION fn_ajustar_stock_detalle()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo   TEXT;
    v_ant    INTEGER;
    v_nue    INTEGER;
    v_old_ef INTEGER;   -- unidades que descontó la cantidad anterior
    v_new_ef INTEGER;   -- unidades que descuenta la nueva cantidad
    v_delta  INTEGER;   -- >0: descontar más; <0: devolver
BEGIN
    -- Cambiar el producto de un detalle no se soporta en Fase 1.
    IF NEW.cod_pro_deto <> OLD.cod_pro_deto THEN
        RETURN NEW;
    END IF;
    IF NEW.cantidad_deto = OLD.cantidad_deto THEN
        RETURN NEW;
    END IF;

    SELECT tipo_pro INTO v_tipo FROM productos
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;
    IF v_tipo IS DISTINCT FROM 'BIEN' THEN
        RETURN NEW;
    END IF;

    -- Regla de cortesía aplicada a ambos extremos.
    v_old_ef := CASE WHEN OLD.cantidad_deto > 0 THEN OLD.cantidad_deto::integer ELSE 0 END;
    v_new_ef := CASE WHEN NEW.cantidad_deto > 0 THEN NEW.cantidad_deto::integer ELSE 0 END;
    v_delta  := v_new_ef - v_old_ef;
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

DROP TRIGGER IF EXISTS tg_ajustar_stock ON detalle_orden_trabajo;
CREATE TRIGGER tg_ajustar_stock
AFTER UPDATE ON detalle_orden_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_ajustar_stock_detalle();

-- ------------------------------------------------------------
-- 6. Exponer tipo_pro en las vistas de catálogo (columna añadida al final
--    para que CREATE OR REPLACE VIEW funcione sobre las vistas existentes).
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_productos WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
       p.stock_pro, p.stock_pro_min, p.cod_est_pro, e.nombre_est AS estado_producto,
       p.tipo_pro
FROM productos p INNER JOIN estados e ON p.cod_est_pro = e.cod_est;

CREATE OR REPLACE VIEW vw_productos_activos WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
       p.stock_pro, p.stock_pro_min, p.cod_est_pro, e.nombre_est AS estado_producto,
       p.tipo_pro
FROM productos p INNER JOIN estados e ON p.cod_est_pro = e.cod_est
WHERE p.cod_est_pro = 1;

COMMIT;
