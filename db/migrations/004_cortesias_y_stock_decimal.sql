-- F1-06 + F1-03 (misma rama/migración: ambas reescriben las mismas 3
-- funciones de trigger de inventario).
--
-- F1-06: hoy "no se factura" se guarda como cantidad_deto NEGATIVA, y los
-- triggers ignoran cualquier línea con cantidad_deto <= 0 -- un repuesto
-- marcado como cortesía sale de la bodega pero el inventario nunca baja
-- (hueco de fraude/descuadre). Se reemplaza por una columna booleana
-- explícita (cobrar_deto) que ya NO afecta si el stock se descuenta -- solo
-- cambia el motivo que queda en el kardex.
--
-- F1-03: stock_pro/stock_pro_min y las columnas de movimientos_inventario son
-- INTEGER aunque cantidad_deto ya es NUMERIC(10,2); los triggers truncan con
-- ::integer (1.5 litros descuentan 2 del stock). Se pasa todo a NUMERIC(12,3)
-- y se agrega unidad_pro.
--
-- Orden: (1) DROP de las 9 vistas que referencian columnas que cambian de
-- tipo (Postgres no permite ALTER COLUMN TYPE con una vista dependiente,
-- aunque la columna solo se use en un WHERE, no en el SELECT de salida) ->
-- (2) columnas nuevas y cambios de tipo (sin CHECK todavía: los datos
-- legados los violarían) -> (3) backfill de cortesías legadas con los
-- triggers de stock apagados, taller por taller (mt_app NO bypassea RLS
-- pese a ser dueño del schema: todas las tablas tienen FORCE ROW LEVEL
-- SECURITY) -> (4) CHECK constraints -> (5) triggers reescritos -> (6)
-- recrear las 9 vistas -> (7) catálogo de permisos.

-- ============================================================
-- 1. DROP de vistas dependientes
-- ============================================================
DROP VIEW IF EXISTS vw_detalle_ot_productos;
DROP VIEW IF EXISTS vw_resumen_financiero_ot;
DROP VIEW IF EXISTS vw_movimientos_inventario;
DROP VIEW IF EXISTS vw_paquete_componentes;
DROP VIEW IF EXISTS vw_productos;
DROP VIEW IF EXISTS vw_productos_activos;
DROP VIEW IF EXISTS vw_productos_con_impuestos;
DROP VIEW IF EXISTS vw_inventario_alertas;
DROP VIEW IF EXISTS vw_dashboard_resumen;

-- ============================================================
-- 2. Columnas nuevas y cambios de tipo
-- ============================================================
ALTER TABLE detalle_orden_trabajo
    ALTER COLUMN cantidad_deto TYPE NUMERIC(12, 3),
    ADD COLUMN IF NOT EXISTS cobrar_deto BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS motivo_no_cobro_deto VARCHAR(200);

ALTER TABLE productos
    ALTER COLUMN stock_pro     TYPE NUMERIC(12, 3) USING stock_pro::numeric(12, 3),
    ALTER COLUMN stock_pro_min TYPE NUMERIC(12, 3) USING stock_pro_min::numeric(12, 3),
    ADD COLUMN IF NOT EXISTS unidad_pro VARCHAR(10) NOT NULL DEFAULT 'unidad';

ALTER TABLE movimientos_inventario
    ALTER COLUMN cantidad_mov  TYPE NUMERIC(12, 3) USING cantidad_mov::numeric(12, 3),
    ALTER COLUMN stock_ant_mov TYPE NUMERIC(12, 3) USING stock_ant_mov::numeric(12, 3),
    ALTER COLUMN stock_nue_mov TYPE NUMERIC(12, 3) USING stock_nue_mov::numeric(12, 3);

ALTER TABLE paquete_componentes
    ALTER COLUMN cantidad_comp TYPE NUMERIC(12, 3);

-- ============================================================
-- 3. Backfill: cantidad negativa (cortesía legada) -> ABS + cobrar_deto=false.
--    Triggers de stock Y de auditoría apagados (no se vuelve a descontar
--    inventario que el bug ya dejó sin tocar en su momento; no se llena
--    audit_log de "ediciones" sintéticas de la migración).
-- ============================================================
DO $$
DECLARE
    r RECORD;
BEGIN
    ALTER TABLE detalle_orden_trabajo DISABLE TRIGGER tg_actualizar_stock;
    ALTER TABLE detalle_orden_trabajo DISABLE TRIGGER tg_ajustar_stock;
    ALTER TABLE detalle_orden_trabajo DISABLE TRIGGER tg_revertir_stock;
    ALTER TABLE detalle_orden_trabajo DISABLE TRIGGER tg_audit_detalle_orden_trabajo;

    FOR r IN SELECT cod_taller FROM talleres LOOP
        PERFORM set_config('app.tenant_id', r.cod_taller::text, true);

        UPDATE detalle_orden_trabajo
           SET cantidad_deto = ABS(cantidad_deto),
               cobrar_deto = false,
               motivo_no_cobro_deto = 'Migración 004: cortesía histórica (cantidad negativa)'
         WHERE cod_taller = r.cod_taller
           AND cantidad_deto < 0;
    END LOOP;

    ALTER TABLE detalle_orden_trabajo ENABLE TRIGGER tg_actualizar_stock;
    ALTER TABLE detalle_orden_trabajo ENABLE TRIGGER tg_ajustar_stock;
    ALTER TABLE detalle_orden_trabajo ENABLE TRIGGER tg_revertir_stock;
    ALTER TABLE detalle_orden_trabajo ENABLE TRIGGER tg_audit_detalle_orden_trabajo;
END $$;

-- ============================================================
-- 4. CHECK constraints (después del backfill)
-- ============================================================
ALTER TABLE detalle_orden_trabajo
    ADD CONSTRAINT chk_deto_cantidad_positiva CHECK (cantidad_deto > 0),
    ADD CONSTRAINT chk_deto_motivo_si_no_cobra CHECK (cobrar_deto OR motivo_no_cobro_deto IS NOT NULL);

ALTER TABLE productos
    ADD CONSTRAINT chk_producto_unidad CHECK (unidad_pro IN ('unidad', 'litro', 'galon', 'metro'));

-- ============================================================
-- 5. Triggers reescritos: el stock SIEMPRE se descuenta (se cobre o no).
--    cobrar_deto ya no decide SI afecta inventario, solo el TEXTO del motivo
--    en el kardex. Todas las variables pasan de INTEGER a NUMERIC(12,3); se
--    quita todo ::integer (eso era lo que truncaba 1.5 -> 1).
-- ============================================================
CREATE OR REPLACE FUNCTION fn_actualizar_stock()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo   TEXT;
    v_ant    NUMERIC(12, 3);
    v_nue    NUMERIC(12, 3);
    v_cant   NUMERIC(12, 3);
    v_motivo VARCHAR(255);
    r        RECORD;
BEGIN
    SELECT tipo_pro INTO v_tipo FROM productos
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;

    IF v_tipo = 'SERVICIO' THEN
        RETURN NEW;
    END IF;

    v_motivo := CASE WHEN NEW.cobrar_deto THEN 'Uso en orden de trabajo'
                     ELSE 'Cortesía OT #' || NEW.consecutivo_ot_deto END;

    IF v_tipo = 'PAQUETE' THEN
        FOR r IN
            SELECT pc.cod_pro_comp, pc.cantidad_comp, p.tipo_pro AS tipo_comp
              FROM paquete_componentes pc
              JOIN productos p ON p.cod_pro = pc.cod_pro_comp AND p.cod_taller = pc.cod_taller
             WHERE pc.cod_pro_paq = NEW.cod_pro_deto AND pc.cod_taller = NEW.cod_taller
        LOOP
            IF r.tipo_comp = 'BIEN' THEN
                v_cant := r.cantidad_comp * NEW.cantidad_deto;
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
                   CASE WHEN NEW.cobrar_deto THEN 'Componente de paquete'
                        ELSE 'Componente de paquete (Cortesía OT #' || NEW.consecutivo_ot_deto || ')' END,
                   NEW.documento_usu_deto, 'OT #' || NEW.consecutivo_ot_deto);
            END IF;
        END LOOP;
        RETURN NEW;
    END IF;

    IF v_tipo IS DISTINCT FROM 'BIEN' THEN
        RETURN NEW;
    END IF;

    -- BIEN
    v_cant := NEW.cantidad_deto;
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
       v_motivo, NEW.documento_usu_deto, 'OT #' || NEW.consecutivo_ot_deto);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_revertir_stock_detalle()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo TEXT;
    v_ant  NUMERIC(12, 3);
    v_nue  NUMERIC(12, 3);
    v_cant NUMERIC(12, 3);
    r      RECORD;
BEGIN
    SELECT tipo_pro INTO v_tipo FROM productos
     WHERE cod_pro = OLD.cod_pro_deto AND cod_taller = OLD.cod_taller;

    IF v_tipo = 'PAQUETE' THEN
        FOR r IN
            SELECT pc.cod_pro_comp, pc.cantidad_comp, p.tipo_pro AS tipo_comp
              FROM paquete_componentes pc
              JOIN productos p ON p.cod_pro = pc.cod_pro_comp AND p.cod_taller = pc.cod_taller
             WHERE pc.cod_pro_paq = OLD.cod_pro_deto AND pc.cod_taller = OLD.cod_taller
        LOOP
            IF r.tipo_comp = 'BIEN' THEN
                v_cant := r.cantidad_comp * OLD.cantidad_deto;
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

    IF v_tipo IS DISTINCT FROM 'BIEN' THEN
        RETURN OLD;
    END IF;

    v_cant := OLD.cantidad_deto;
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

CREATE OR REPLACE FUNCTION fn_ajustar_stock_detalle()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo   TEXT;
    v_ant    NUMERIC(12, 3);
    v_nue    NUMERIC(12, 3);
    v_delta  NUMERIC(12, 3);
    v_motivo VARCHAR(255);
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

    v_motivo := CASE WHEN NEW.cobrar_deto THEN 'Edición de OT'
                     ELSE 'Edición de OT (Cortesía OT #' || NEW.consecutivo_ot_deto || ')' END;

    IF v_tipo = 'PAQUETE' THEN
        FOR r IN
            SELECT pc.cod_pro_comp, pc.cantidad_comp, p.tipo_pro AS tipo_comp
              FROM paquete_componentes pc
              JOIN productos p ON p.cod_pro = pc.cod_pro_comp AND p.cod_taller = pc.cod_taller
             WHERE pc.cod_pro_paq = NEW.cod_pro_deto AND pc.cod_taller = NEW.cod_taller
        LOOP
            IF r.tipo_comp = 'BIEN' THEN
                v_delta := r.cantidad_comp * (NEW.cantidad_deto - OLD.cantidad_deto);
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

    IF v_tipo IS DISTINCT FROM 'BIEN' THEN
        RETURN NEW;
    END IF;

    v_delta := NEW.cantidad_deto - OLD.cantidad_deto;
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
       v_motivo, NEW.documento_usu_deto, 'OT #' || NEW.consecutivo_ot_deto);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Los CREATE TRIGGER no cambian (mismo nombre/tabla/evento, ya existen):
-- tg_actualizar_stock, tg_revertir_stock, tg_ajustar_stock.

-- ============================================================
-- 6. Recrear las 9 vistas dropeadas en el paso 1.
--    vw_detalle_ot_productos y vw_resumen_financiero_ot: reescritas para usar
--    cobrar_deto. Las otras 7: mismo texto que ya tenían, solo cambia tipo de
--    columna subyacente (CREATE VIEW, no OR REPLACE, porque se dropearon).
-- ============================================================
CREATE VIEW vw_detalle_ot_productos WITH (security_invoker = on) AS
SELECT
    dot.consecutivo_ot_deto, dot.cod_pro_deto,
    p.nombre_pro, p.descripcion_pro, dot.cantidad_deto, dot.valor_unitario_deto,
    dot.cobrar_deto, dot.motivo_no_cobro_deto,
    (dot.cantidad_deto * dot.valor_unitario_deto) AS subtotal,
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
    COUNT(CASE WHEN dot.cobrar_deto THEN dot.cod_pro_deto END) AS total_items,
    SUM(CASE WHEN dot.cobrar_deto THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS subtotal_productos,
    0 AS total_impuestos,
    SUM(CASE WHEN dot.cobrar_deto THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS total_ot
FROM ordenes_trabajo ot
INNER JOIN detalle_orden_trabajo dot ON ot.consecutivo_ot = dot.consecutivo_ot_deto AND ot.cod_taller = dot.cod_taller
INNER JOIN motos m    ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
GROUP BY ot.consecutivo_ot, ot.fecha_elaboracion_ot, c.nombre_cli, c.apellido_1_cli, m.placa_mot;

CREATE VIEW vw_movimientos_inventario WITH (security_invoker = on) AS
SELECT m.cod_mov, m.cod_pro_mov, p.nombre_pro, m.tipo_mov, m.cantidad_mov,
       m.stock_ant_mov, m.stock_nue_mov, m.motivo_mov, m.documento_usu_mov,
       to_char(m.fecha_mov, 'YYYY-MM-DD HH24:MI') AS fecha_mov, m.referencia_mov
FROM movimientos_inventario m
JOIN productos p ON p.cod_pro = m.cod_pro_mov AND p.cod_taller = m.cod_taller;

CREATE VIEW vw_paquete_componentes WITH (security_invoker = on) AS
SELECT pc.cod_paq_comp, pc.cod_pro_paq, pc.cod_pro_comp, pc.cantidad_comp,
       p.nombre_pro, p.tipo_pro, p.stock_pro
FROM paquete_componentes pc
JOIN productos p ON p.cod_pro = pc.cod_pro_comp AND p.cod_taller = pc.cod_taller;

CREATE VIEW vw_dashboard_resumen WITH (security_invoker = on) AS
SELECT
  (SELECT count(*) FROM clientes)        AS total_clientes,
  (SELECT count(*) FROM motos)           AS total_motos,
  (SELECT count(*) FROM productos)       AS total_productos,
  (SELECT count(*) FROM ordenes_trabajo) AS total_ordenes,
  (SELECT count(*) FROM ordenes_trabajo WHERE cod_ot_est_ot IN (1, 2, 6)) AS ot_activas,
  (SELECT count(*) FROM productos
     WHERE cod_est_pro = 1 AND stock_pro <= stock_pro_min)               AS productos_bajo_stock,
  (SELECT count(*) FROM reclamos)        AS total_reclamos;

CREATE VIEW vw_productos WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
       p.stock_pro, p.stock_pro_min, p.unidad_pro, p.cod_est_pro, e.nombre_est AS estado_producto,
       p.tipo_pro
FROM productos p INNER JOIN estados e ON p.cod_est_pro = e.cod_est;

CREATE VIEW vw_productos_activos WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
       p.stock_pro, p.stock_pro_min, p.unidad_pro, p.cod_est_pro, e.nombre_est AS estado_producto,
       p.tipo_pro
FROM productos p INNER JOIN estados e ON p.cod_est_pro = e.cod_est
WHERE p.cod_est_pro = 1;

CREATE VIEW vw_productos_con_impuestos WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
       p.stock_pro, p.stock_pro_min, p.unidad_pro, e.nombre_est AS estado_producto,
       pi.cod_pro_imp, i.nombre_imp, pi.porcentaje_pro_imp,
       ROUND(p.precio_pro * (pi.porcentaje_pro_imp / 100), 2) AS valor_impuesto,
       ROUND(p.precio_pro + (p.precio_pro * (pi.porcentaje_pro_imp / 100)), 2) AS precio_con_impuesto
FROM productos p
INNER JOIN estados e ON p.cod_est_pro = e.cod_est
LEFT JOIN productos_impuestos pi ON p.cod_pro = pi.cod_pro_pro_imp AND p.cod_taller = pi.cod_taller
LEFT JOIN impuestos i ON pi.cod_imp_pro_imp = i.cod_imp AND pi.cod_taller = i.cod_taller;

CREATE VIEW vw_inventario_alertas WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro,
       p.stock_pro, p.stock_pro_min, p.precio_pro, e.nombre_est AS estado,
       CASE
           WHEN p.stock_pro = 0 THEN 'SIN STOCK'
           WHEN p.stock_pro <= p.stock_pro_min THEN 'STOCK BAJO'
           WHEN p.stock_pro > p.stock_pro_min AND p.stock_pro <= (p.stock_pro_min * 2) THEN 'STOCK MEDIO'
           ELSE 'STOCK NORMAL'
       END AS nivel_alerta,
       (p.stock_pro_min - p.stock_pro) AS cantidad_a_pedir
FROM productos p INNER JOIN estados e ON p.cod_est_pro = e.cod_est;

-- ============================================================
-- 7. Catálogo de permisos -- solo Admin lo tiene por defecto (bypass de rol
--    en require_permiso/usuario_tiene_permiso); no se toca
--    fn_seed_perfiles_taller ni se backfillea perfiles_permisos para
--    Mecánico/Recepcionista a propósito (control de fraude, no conveniencia).
-- ============================================================
-- nombre_prm no tiene UNIQUE (ver tabla permisos) -- se usa WHERE NOT EXISTS
-- en vez de ON CONFLICT para que la migración sea idempotente igual.
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm)
SELECT nextval('seq_permisos'), 'marcar_no_cobro:ordenes-trabajo',
       'Permite marcar un ítem de una orden como "no se cobra" (cortesía)', '/ordenes'
WHERE NOT EXISTS (SELECT 1 FROM permisos WHERE nombre_prm = 'marcar_no_cobro:ordenes-trabajo');
