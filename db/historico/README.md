# Migraciones históricas (pre-F1-00)

Archivos de antes del sistema de migraciones versionadas (`db/migrations/` +
`schema_migrations`, ver `README.md` en la raíz del repo). Todos ya están
aplicados tanto a producción como foldeados en `db/full_schema_v2_multitenant.sql`
-- quedan acá solo de referencia histórica. Ninguna herramienta los lee ni los
vuelve a correr.

**`migration_super_admin.sql` es un caso aparte**: no es un script para ejecutar
de corrido -- es un procedimiento manual documentado (con su propia verificación
dentro de la misma transacción, pensado para correrse línea por línea a mano). Por
eso nunca se convirtió en una migración numerada de `db/migrations/`.
