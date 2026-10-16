-- ============================================================
-- Migración: anti-abuso del trial (Fase 1, item 1).
-- Un correo = un taller. La ventana de 30 días se materializa en código
-- (TallerServicio.registrar fija fecha_fin_susc_tal = hoy + 30).
-- Idempotente. Correr como el rol DUEÑO de las tablas (mt_app local).
-- ============================================================

CREATE UNIQUE INDEX IF NOT EXISTS ux_talleres_correo
    ON talleres (lower(correo_tal));
