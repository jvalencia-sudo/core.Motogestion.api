-- Rol de la aplicación: NO superusuario y DUEÑO del schema public.
-- Es clave que NO sea superusuario: así el RLS (FORCE ROW LEVEL SECURITY) aísla
-- los datos por taller. Si la app usara un superusuario, el RLS se saltaría.
-- (Credenciales de DESARROLLO local; en producción se usan otras.)
CREATE ROLE mt_app LOGIN PASSWORD 'test123' NOSUPERUSER;
ALTER SCHEMA public OWNER TO mt_app;
GRANT ALL ON SCHEMA public TO mt_app;

-- BD separada para los tests de integración (tests/conftest.py): así los tests que
-- siembran y borran datos (aislamiento multi-tenant, cobertura de RLS) nunca tocan
-- la BD de desarrollo. Cargada por 02_load_test.sql.
CREATE DATABASE motogestion_test OWNER mt_app;
