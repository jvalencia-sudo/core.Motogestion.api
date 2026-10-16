-- F0-13 (cierre): campos reales del comprobante en "Mi taller" -- dirección,
-- teléfono (ya existían), texto de pie del comprobante y días de garantía
-- por defecto.
--
-- Aún no aplicada a producción real al momento de escribir esta migración (F1-00):
-- es la primera que corre el sistema automático de db/migrations/, vía
-- `scripts/migrate.py up` (local/CI) o el paso de deploy (prod).

ALTER TABLE talleres ADD COLUMN IF NOT EXISTS direccion_tal VARCHAR(200);
ALTER TABLE talleres ADD COLUMN IF NOT EXISTS texto_pie_comprobante VARCHAR(300);
ALTER TABLE talleres ADD COLUMN IF NOT EXISTS dias_garantia_pred INTEGER NOT NULL DEFAULT 30;
