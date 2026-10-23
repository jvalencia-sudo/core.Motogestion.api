-- Carga el esquema multi-tenant COMO mt_app (para que las tablas sean suyas y el
-- RLS FORCE aplique). El archivo se monta en /schema.sql desde docker-compose.
SET ROLE mt_app;
\i /schema.sql
-- Seed de demo (taller/usuarios de ejemplo) -- solo local, nunca producción.
\i /seed_demo.sql

-- F1-00: full_schema.sql YA incluye todo lo que hay en db/migrations/ a esta
-- fecha (se foldea a mano, ver README.md) -- esto solo deja constancia en
-- schema_migrations para que scripts/migrate.py no intente reaplicarlo.
-- Actualizar esta lista junto con full_schema.sql cada vez que se agregue una
-- migración nueva (ver el checklist de README.md).
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT now()
);
INSERT INTO schema_migrations (version) VALUES
    ('000_baseline'),
    ('001_mi_taller_campos'),
    ('002_garantia_pred_trigger'),
    ('003_orden_rapida_mecanico_opcional'),
    ('004_cortesias_y_stock_decimal'),
    ('005_busqueda_placa'),
    ('006_corregir_kilometraje_salida'),
    ('007_roles_simplificados'),
    ('008_anulacion_auditoria'),
    ('009_garantia_por_producto'),
    ('010_pagos_orden'),
    ('011_personalizacion_pdf'),
    ('012_tipo_documento_y_ciudad_placa')
ON CONFLICT (version) DO NOTHING;
