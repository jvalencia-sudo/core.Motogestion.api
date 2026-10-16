-- ============================================================
-- Migración: INVENTARIO ligero (movimientos de stock).
-- Registra cada cambio de stock (ENTRADA/SALIDA/AJUSTE) como kardex por taller.
-- Amplía el trigger de stock para que las salidas por OT también queden registradas.
-- Preparada para crecer: para compras/proveedores solo se agregan tablas + una
-- columna cod_compra a esta, sin rehacer nada.
-- Idempotente. Correr como el rol DUEÑO de las tablas (mt_app local / motogestion prod).
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS seq_movimientos_inventario START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;

CREATE TABLE IF NOT EXISTS movimientos_inventario (
    cod_taller        INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_mov           INTEGER NOT NULL DEFAULT nextval('seq_movimientos_inventario'),
    cod_pro_mov       INTEGER NOT NULL,
    tipo_mov          VARCHAR(10) NOT NULL,   -- ENTRADA / SALIDA / AJUSTE
    cantidad_mov      INTEGER NOT NULL,       -- delta aplicado al stock (+entra, -sale)
    stock_ant_mov     INTEGER,
    stock_nue_mov     INTEGER,
    motivo_mov        VARCHAR(255),
    documento_usu_mov VARCHAR(11),            -- quién lo hizo (sin FK: es auditoría)
    fecha_mov         TIMESTAMP NOT NULL DEFAULT now(),
    referencia_mov    VARCHAR(50),            -- ej. "OT #12"; a futuro el cod_compra
    CONSTRAINT pk_mov_inv     PRIMARY KEY (cod_taller, cod_mov),
    CONSTRAINT fk_mov_taller  FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_mov_producto FOREIGN KEY (cod_taller, cod_pro_mov) REFERENCES productos (cod_taller, cod_pro),
    CONSTRAINT chk_mov_tipo   CHECK (tipo_mov IN ('ENTRADA', 'SALIDA', 'AJUSTE'))
);

-- RLS por taller
ALTER TABLE movimientos_inventario ENABLE ROW LEVEL SECURITY;
ALTER TABLE movimientos_inventario FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON movimientos_inventario;
CREATE POLICY tenant_isolation ON movimientos_inventario
  USING (cod_taller = current_setting('app.tenant_id', true)::integer)
  WITH CHECK (cod_taller = current_setting('app.tenant_id', true)::integer);

-- Ampliar el trigger de stock: además de descontar, deja el movimiento SALIDA (kardex).
CREATE OR REPLACE FUNCTION fn_actualizar_stock()
RETURNS TRIGGER AS $$
DECLARE
    v_ant INTEGER;
    v_nue INTEGER;
BEGIN
    SELECT stock_pro INTO v_ant FROM productos
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;
    v_nue := COALESCE(v_ant, 0) - NEW.cantidad_deto;

    UPDATE productos SET stock_pro = v_nue
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;

    INSERT INTO movimientos_inventario
      (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
       motivo_mov, documento_usu_mov, referencia_mov)
    VALUES
      (NEW.cod_taller, NEW.cod_pro_deto, 'SALIDA', -NEW.cantidad_deto, v_ant, v_nue,
       'Uso en orden de trabajo', NEW.documento_usu_deto, 'OT #' || NEW.consecutivo_ot_deto);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
