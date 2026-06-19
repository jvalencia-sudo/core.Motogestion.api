-- ============================================================
-- 05_audit.sql
-- Auditoria en Postgres. Reemplaza el paquete Oracle PKG_AUDITORIA +
-- UTL_FILE (que escribia a archivos .txt) por una TABLA audit_log poblada
-- por una funcion trigger generica.
-- ============================================================

CREATE TABLE audit_log (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha           TIMESTAMP    NOT NULL DEFAULT now(),
    usuario         VARCHAR(100) DEFAULT session_user,
    tabla           VARCHAR(100),
    evento          CHAR(1),          -- I = insert, U = update, D = delete
    valor_anterior  JSONB,
    valor_nuevo     JSONB
);

CREATE OR REPLACE FUNCTION fn_audit()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (tabla, evento, valor_nuevo)
        VALUES (TG_TABLE_NAME, 'I', to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (tabla, evento, valor_anterior, valor_nuevo)
        VALUES (TG_TABLE_NAME, 'U', to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (tabla, evento, valor_anterior)
        VALUES (TG_TABLE_NAME, 'D', to_jsonb(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Triggers de auditoria sobre las tablas clave del negocio
CREATE TRIGGER tg_audit_clientes
AFTER INSERT OR UPDATE OR DELETE ON clientes
FOR EACH ROW EXECUTE FUNCTION fn_audit();

CREATE TRIGGER tg_audit_productos
AFTER INSERT OR UPDATE OR DELETE ON productos
FOR EACH ROW EXECUTE FUNCTION fn_audit();

CREATE TRIGGER tg_audit_ordenes_trabajo
AFTER INSERT OR UPDATE OR DELETE ON ordenes_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_audit();

CREATE TRIGGER tg_audit_detalle_orden_trabajo
AFTER INSERT OR UPDATE OR DELETE ON detalle_orden_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_audit();

CREATE TRIGGER tg_audit_usuarios
AFTER INSERT OR UPDATE OR DELETE ON usuarios
FOR EACH ROW EXECUTE FUNCTION fn_audit();
