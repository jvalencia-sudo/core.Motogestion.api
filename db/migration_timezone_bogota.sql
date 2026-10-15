-- ============================================================
-- Migración: zona horaria de la BD a America/Bogota.
-- Todas las columnas de fecha (pagos.fecha, talleres.fecha_creacion_tal,
-- fecha_fin_susc_tal, etc.) son TIMESTAMP sin zona con DEFAULT now(). La BD
-- de Docker corre en UTC, así que now() quedaba 5h adelantado respecto a
-- Colombia -- un pago de las 8:17pm se veía como la 1:17am del día
-- siguiente. Las filas ya escritas quedan en UTC (son pocas y de prueba);
-- esto solo corrige now() para todo lo que se escriba de acá en adelante.
-- A futuro (F1-00): pasar estas columnas a TIMESTAMPTZ.
-- Idempotente. Correr como superusuario (dueño de la BD, no mt_app).
-- ============================================================

ALTER DATABASE motogestion SET timezone = 'America/Bogota';
