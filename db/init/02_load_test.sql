-- Carga el mismo esquema multi-tenant en motogestion_test (creada en 00_roles.sql),
-- para los tests de integración. Mismo patrón que 01_load.sql pero en la otra BD.
\c motogestion_test
SET ROLE mt_app;
\i /schema.sql
-- tests/superadmin_test.py reutiliza al admin demo (sub-1000000001) como
-- fixture de super-admin -- esta BD también necesita el seed de demo.
\i /seed_demo.sql

-- F1-00: ver el mismo bloque en 01_load.sql -- deja constancia de que
-- full_schema.sql ya incluye estas migraciones, para que scripts/migrate.py no
-- intente reaplicarlas.
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
