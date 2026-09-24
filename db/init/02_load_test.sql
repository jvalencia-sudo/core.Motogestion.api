-- Carga el mismo esquema multi-tenant en motogestion_test (creada en 00_roles.sql),
-- para los tests de integración. Mismo patrón que 01_load.sql pero en la otra BD.
\c motogestion_test
SET ROLE mt_app;
\i /schema.sql
