# Cómo correr (desarrollo local) — PostgreSQL multi-tenant

Backend FastAPI sobre **PostgreSQL**. La BD corre en Docker y, en el primer arranque,
crea el rol de la app y carga el **esquema multi-tenant + datos semilla** automáticamente.

## Requisitos
- **Docker Desktop**
- **uv** (gestor de Python de Astral) · **Python 3.11**

## 1. Variables de entorno

Copia `.env.example` a `.env`. La sección de BD ya viene lista (la app se conecta como
`mt_app`, un rol NO superusuario, para que el RLS aísle los datos por taller):

```
DB_HOST=localhost
DB_PORT=5432
DB_USER=mt_app
DB_PASSWORD=test123
DB_NAME=motogestion
```

⚠️ La sección **Auth0** trae placeholders. Para poder **iniciar sesión** necesitas los
valores del tenant de desarrollo (pídeselos a quien administra el proyecto y pégalos en tu
`.env`). Sin ellos la API arranca igual, pero el login no funcionará.

## 2. Levantar PostgreSQL en Docker

```powershell
docker compose up -d           # 1ª vez: crea mt_app + carga el esquema multi-tenant + seed
docker compose ps              # debe verse motogestion-db (healthy)
```

En el primer arranque, `db/init/` corre en orden:
`00_roles.sql` (crea el rol `mt_app` no-superusuario, dueño del schema) →
`01_load.sql` (carga `db/full_schema_v2_multitenant.sql` **como mt_app**, con RLS por taller
y el taller demo `MotoGestión Demo` sembrado).

> Para recargar la BD desde cero: `docker compose down -v` y vuelve a `docker compose up -d`
> (el `-v` borra el volumen `pgdata`).

## 3. Instalar dependencias (uv)

> ⚠️ Si el proyecto está en OneDrive (no soporta *hardlinks* y bloquea archivos), crea el
> entorno virtual **fuera de OneDrive**:

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$env:USERPROFILE\.venvs\coremotogestion-api"
uv sync
```

(Si NO estás en OneDrive, basta con `uv sync`.)

## 4. Arrancar la API

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$env:USERPROFILE\.venvs\coremotogestion-api"
$env:PYTHONUTF8 = "1"          # evita errores de codificación con los emojis de los logs
uv run python main.py
```

- Usa **`python main.py`** (no `uvicorn main:app` por CLI): en Windows, `psycopg` async
  necesita el `SelectorEventLoop`, que `main.py` configura **antes** de arrancar uvicorn.
- API en http://localhost:8000 · Swagger en http://localhost:8000/docs

## 5. Verificación rápida

```powershell
curl http://localhost:8000/health           # {"status":"ok"}
curl http://localhost:8000/api/marcas        # lista de marcas del taller demo (lee de la BD)
```

## 6. (Opcional) Poder iniciar sesión con tu correo

El login es **cerrado**: solo entra un correo ya registrado. Con Auth0 configurado, para
habilitar tu cuenta pre-regístrala como admin del taller demo:

```powershell
docker exec -e PGPASSWORD=test123 motogestion-db psql -U mt_app -d motogestion -c "SET app.tenant_id='1'; INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu) VALUES ('9000000001','TU_NOMBRE','Apellido','TU_CORREO@ejemplo.com','auth0_managed',1,1,NULL,1,1);"
```

(cambia `TU_CORREO@ejemplo.com` por el correo con el que inicias sesión en Auth0/Google).

## Notas

- **VS Code**: selecciona el intérprete del venv externo
  (`%USERPROFILE%\.venvs\coremotogestion-api\Scripts\python.exe`) para quitar los avisos de
  "paquete no instalado".
- La capa de datos (`repository/data/database.py`, clase `Database`) usa `psycopg`/PostgreSQL,
  fija `app.tenant_id` por request (multi-tenant) y devuelve columnas en MAYÚSCULAS.
- El admin del contenedor es `postgres/postgres` (solo para administrar Postgres); la app
  nunca lo usa.
