# Cómo correr (desarrollo local) — PostgreSQL

Backend FastAPI sobre **PostgreSQL**. La base de datos corre en Docker y
carga el esquema + datos semilla automáticamente.

## 1. Variables de entorno

Copia `.env.example` a `.env` (ya hay uno listo para local). La sección de BD apunta al
contenedor:

```
DB_HOST=localhost
DB_PORT=5432
DB_USER=us_ppi
DB_PASSWORD=123
DB_NAME=motogestion
```

## 2. Levantar PostgreSQL en Docker

```powershell
docker compose up -d           # crea la BD y carga db/init/*.sql (solo la 1ª vez)
docker compose ps              # debe verse motogestion-db (healthy)
```

Los scripts en `db/init/` se ejecutan en orden en el primer arranque:
`01_sequences` → `02_tables` (PK/FK) → `03_views` → `04_triggers` (stock, consecutivo OT,
garantía) → `05_audit` (tabla `audit_log` + triggers) → `06_seed` (datos de prueba).

> Para recargar el esquema desde cero: `docker compose down -v` y vuelve a `up -d`
> (el `-v` borra el volumen `pgdata`).

## 3. Instalar dependencias (uv)

> ⚠️ El proyecto está en OneDrive, que no soporta *hardlinks* y a veces bloquea
> archivos. Por eso el entorno virtual se crea **fuera de OneDrive**.

PowerShell:

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$env:USERPROFILE\.venvs\coremotogestion-api"
uv sync
```

(El `link-mode = "copy"` ya está fijado en `pyproject.toml`.)

## 4. Arrancar la API

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$env:USERPROFILE\.venvs\coremotogestion-api"
$env:PYTHONUTF8 = "1"          # evita errores de codificación con los emojis de los logs
uv run python main.py
```

- Usa **`python main.py`** (no `uvicorn main:app` por CLI): en Windows, `psycopg` async
  necesita el `SelectorEventLoop`, que `main.py` configura **antes** de arrancar uvicorn.
- API en http://localhost:8000  · Swagger en http://localhost:8000/docs

## 5. Verificación rápida

```powershell
curl http://localhost:8000/                 # {"message":"healthy"}
curl http://localhost:8000/api/marcas       # lista de marcas (lee de la BD)
```

## Notas

- **VS Code**: selecciona el intérprete del venv externo
  (`%USERPROFILE%\.venvs\coremotogestion-api\Scripts\python.exe`) para quitar los avisos
  de "paquete no instalado".
- La capa de datos (`repository/data/database.py`, clase `Database`) usa `psycopg`/PostgreSQL.
  Traduce binds `:1 → %s` y devuelve las columnas en MAYÚSCULAS para no tocar el dominio.
