-- ============================================================
-- Migración 001: landing y planes coherentes (F0-08).
-- Un solo plan de pago ("Taller"), precio fundador para los primeros 10
-- talleres, Premium queda inactivo (no se borra: pagos ya lo referencian) y
-- la prueba deja de tener límite de usuarios.
-- Idempotente. Correr como el rol DUEÑO de las tablas (mt_app local), DESPUÉS
-- de un backup.
-- ============================================================

BEGIN;

ALTER TABLE planes ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE talleres ADD COLUMN IF NOT EXISTS precio_susc_tal INTEGER;

-- Premium no se borra (puede estar referenciado por pagos/talleres ya existentes):
-- solo se oculta del catálogo.
UPDATE planes SET activo = false WHERE nombre_plan = 'Premium';

-- Renombrar Profesional -> Taller. talleres.plan_tal referencia nombre_plan, así
-- que las dos tablas se actualizan en la misma transacción.
UPDATE planes SET nombre_plan = 'Taller', precio_plan = 69000 WHERE nombre_plan = 'Profesional';
UPDATE talleres SET plan_tal = 'Taller' WHERE plan_tal = 'Profesional';

-- La prueba ya no limita usuarios (la landing siempre dijo "todas las funciones";
-- el límite de la BD nunca se aplicó en código, pero quedaba inconsistente).
UPDATE planes SET max_usuarios = NULL WHERE nombre_plan = 'Prueba';

COMMIT;
