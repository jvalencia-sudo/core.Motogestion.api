#!/bin/sh
# Init de PRODUCCIÓN de Postgres. La imagen lo ejecuta UNA sola vez, cuando el
# volumen db_data está vacío (no se re-ejecuta en reinicios ni en `up --build`).
#
# 1. Crea el rol de la app: NO superusuario y DUEÑO del schema public. Es clave:
#    un superusuario se salta el RLS aunque la tabla tenga FORCE ROW LEVEL SECURITY.
# 2. Crea la BD y el usuario de n8n, separados de los de la app.
# 3. Carga el esquema multi-tenant COMO el rol de la app (las tablas quedan suyas
#    y el RLS aplica).
#
# Las contraseñas llegan por variables de entorno (.env) y se pasan a psql con -v
# para que se escapen bien (:'var' = literal, :"var" = identificador).
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v app_db="$POSTGRES_DB" \
    -v app_user="$APP_DB_USER" -v app_pw="$APP_DB_PASSWORD" \
    -v n8n_db="$N8N_DB_NAME" \
    -v n8n_user="$N8N_DB_USER" -v n8n_pw="$N8N_DB_PASSWORD" <<'EOSQL'
-- App
CREATE ROLE :"app_user" LOGIN PASSWORD :'app_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE;
ALTER SCHEMA public OWNER TO :"app_user";
GRANT ALL ON SCHEMA public TO :"app_user";
REVOKE CONNECT ON DATABASE :"app_db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"app_db" TO :"app_user";

-- n8n (BD propia, no mezcla tablas con las de la app)
CREATE ROLE :"n8n_user" LOGIN PASSWORD :'n8n_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE DATABASE :"n8n_db" OWNER :"n8n_user";
REVOKE CONNECT ON DATABASE :"n8n_db" FROM PUBLIC;
EOSQL

# Durante el init el servidor temporal solo acepta el socket unix (auth trust).
psql -v ON_ERROR_STOP=1 --username "$APP_DB_USER" --dbname "$POSTGRES_DB" -f /schema.sql
