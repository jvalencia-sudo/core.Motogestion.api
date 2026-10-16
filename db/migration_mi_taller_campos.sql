-- F0-13 (cierre): campos reales del comprobante en "Mi taller" -- dirección,
-- teléfono (ya existían), texto de pie del comprobante y días de garantía
-- por defecto. Aplicar a mano en la BD de producción (igual que
-- migration_super_admin.sql). CI/fresh DBs ya tienen esto en
-- full_schema_v2_multitenant.sql -- este archivo es solo la versión
-- incremental para una BD ya desplegada.

ALTER TABLE talleres ADD COLUMN IF NOT EXISTS direccion_tal VARCHAR(200);
ALTER TABLE talleres ADD COLUMN IF NOT EXISTS texto_pie_comprobante VARCHAR(300);
ALTER TABLE talleres ADD COLUMN IF NOT EXISTS dias_garantia_pred INTEGER NOT NULL DEFAULT 30;
