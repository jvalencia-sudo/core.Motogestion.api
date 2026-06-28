# Migración Oracle → PostgreSQL + reorganización en dos repos — Handoff

> Documento de contexto para retomar el trabajo (humano u otra IA). Resume **qué se
> hizo, por qué, y los detalles no obvios**. Fecha del trabajo: 2026-06.

## 1. Punto de partida y objetivo

El proyecto original `moto.gestion-api` (FastAPI) estaba acoplado a **Oracle** y no
arrancaba en local (no había Oracle: error `DPY-6005`). Objetivos:

1. **Migrar la persistencia de Oracle a PostgreSQL**, con la BD corriendo en **Docker**
   y el esquema cargándose solo.
2. **Reorganizar en dos repos nuevos** (Git, remoto en GitHub `jvalencia-sudo`):
   - **`core.Motogestion.api`** → TODO el backend Python (este repo).
   - **`core.Motogestion.middle`** → el front (Next.js/React). *No es parte de la
     migración de BD; solo se copió y se le ajustó el `.env` para apuntar al backend nuevo.*

### Rutas en disco
| Rol | Ruta |
|---|---|
| Backend viejo (Oracle, **intacto**) | `…\Universidad\PPI\moto.gestion-api` |
| Front viejo (**intacto**) | `…\Universidad\PPI\moto.gestion-front` |
| **Backend nuevo (este repo)** | `…\Trabajo\Personal\core.Motogestion.api` |
| **Front nuevo** | `…\Trabajo\Personal\core.Motogestion.middle` |

## 2. Hallazgos clave del análisis (antes de migrar)

- `psycopg` (driver Postgres) **ya estaba** en dependencias; el proyecto venía a medias.
- **Ninguna lógica de negocio se invoca por PL/SQL desde Python** (los `call_procedure`/
  `call_function` no se usaban). La lógica vive en Python o en triggers de la BD.
- **Solo 15 repositorios están activos** (dominio español: clientes, motos, productos,
  ordenes_trabajo, marcas, auth, admin). Todos heredan de `BaseRepository` y usan
  `OracleDb` + `build_insert`/`build_update`.
- Hay **14 repos "en inglés"** (`repository/orders|supplier|operation|sync`,
  `auth/user_business_repository.py`) que son **CÓDIGO MUERTO** (plantilla, no enganchada
  al router, apuntan a esquemas inexistentes `orders.`, `core.business`). No se migraron.
  Siguen presentes; se pueden borrar.

## 3. Decisiones de alcance (acordadas con el usuario)

1. **Triggers**: portar **solo los funcionales**. Las validaciones de formato/rango se
   omiten (hoy NO se validan en la BD — ver §6).
2. **Auditoría**: el paquete Oracle `PKG_AUDITORIA` (escribía `.txt` con `UTL_FILE`) se
   reemplazó por una **tabla `audit_log`** + triggers.
3. **Constraints**: se **agregaron PK y FK** (Oracle no las definía).

## 4. Qué se hizo — Base de datos (`db/init/`, Docker)

`docker-compose.yaml` levanta `postgres:16`, publica `5432`, persiste en volumen `pgdata`
y monta `db/init/` en `/docker-entrypoint-initdb.d` (se ejecuta en orden alfabético en el
**primer** arranque). Credenciales desde `.env` (`DB_USER`/`DB_PASSWORD`/`DB_NAME`).

| Script | Contenido |
|---|---|
| `01_sequences.sql` | 8 secuencias (`seq_marcas`, `seq_productos`, …) |
| `02_tables.sql` | 18 tablas con **PK y FK**. Tipos Oracle→PG (`VARCHAR2`→`VARCHAR`, `NUMBER`→`INTEGER`/`NUMERIC`), sin `TABLESPACE`. Las PK autogeneradas usan `DEFAULT nextval('seq_*')`. `detalle_orden_trabajo` lleva PK surrogate `id_deto` IDENTITY. |
| `03_views.sql` | 24 vistas. `SYSDATE`→`CURRENT_DATE`, `TRUNC(SYSDATE-fecha)`→`(CURRENT_DATE-fecha)`. Incluye `vw_permisos` best-effort (no existía y el repo la ordenaba por una columna inexistente). |
| `04_triggers.sql` | Triggers **funcionales** en PL/pgSQL: `tg_actualizar_stock`, `tg_gen_consecutivo_ot`, `tg_calc_fecha_garantia`. |
| `05_audit.sql` | Tabla `audit_log` + función `fn_audit()` + triggers AFTER I/U/D en clientes, productos, ordenes_trabajo, detalle_orden_trabajo, usuarios. |
| `06_seed.sql` | Datos semilla (traducidos de Oracle: `seq.NEXTVAL`→`nextval('seq')`; `TO_DATE` y `COMMIT` válidos en PG). |

Para recargar desde cero: `docker compose down -v && docker compose up -d`.

## 5. Qué se hizo — Capa Python (`oracledb` → `psycopg3`)

| Archivo | Cambio |
|---|---|
| `config.py` | `DbConfig`: `service_name`→`dbname` (alias `DB_NAME`), puerto 5432. |
| `repository/data/db_pool.py` | Reescrito: pool async `psycopg_pool.AsyncConnectionPool`. Test de arranque `SELECT 1`. |
| `repository/data/oracle_db.py` | **Conserva el nombre `OracleDb` y su API** (para no tocar los repos). Internamente psycopg. Dos piezas clave: (a) **shim `_translate`** que convierte binds Oracle `:1 → %s` (escapando `%` literales primero); (b) devuelve las columnas en **MAYÚSCULAS** para replicar Oracle, porque TODO el dominio lee claves en mayúsculas (`db.get("NOMBRE_USU")`). `insert()` usa `RETURNING` + `fetchone()`. |
| `infrastructure/utils/query.py` | `build_insert`/`build_update` emiten `%s`; se eliminó la rama `seq.NEXTVAL` (el valor lo da el DEFAULT/trigger). |
| `main.py` | Sin `import oracledb`/handler Oracle. **Se mantiene** `WindowsSelectorEventLoopPolicy` (psycopg async en Windows lo necesita). |
| `repository/data/db_factory.py` | Reescrito a psycopg (estaba sin uso). |
| `repository/.../detalle_orden_trabajo_repositorio.py` | `SYSDATE`→`CURRENT_DATE` en un INSERT. |
| `repository/marcas/marca_repositorio.py` | Quitado `import oracledb` sin uso. |
| `pyproject.toml` / `requirements.txt` | Eliminado `oracledb`. Añadido `[tool.uv] link-mode = "copy"`. |

**Por qué el shim de mayúsculas + binds es la clave:** evita editar los 15 repos y toda la
capa de dominio. Los repos siguen escribiendo `:1` y leyendo `RESULT["COD_MAR"]` como en
Oracle; el wrapper traduce en el borde. Las consultas con `%s` (de los builders) se dejan
intactas. `OFFSET :n ROWS FETCH NEXT :m ROWS ONLY` es válido en PG tal cual.

## 6. ⚠️ Lo que ya NO valida la BD (reglas omitidas)

Se omitieron todos los triggers de validación de Oracle. **Estas reglas hoy no se
aplican** (ni en BD ni necesariamente en backend) — reimplementar si se requieren:
- Formato email (clientes/usuarios), teléfono numérico, formato de placa.
- Rangos: modelo, cilindraje, kilometraje, stock ≥ 0, precio > 0.
- `fecha_entrega ≥ fecha_elaboracion`, recepcionista ≠ mecánico, fecha confirmación no futura.
- `tg_val_stock_disponible` (stock suficiente antes de agregar detalle) — *semi-funcional, omitido*.
- `tg_val_ot_entregada` (reclamo solo si OT "Entregada") — *semi-funcional, omitido*.
- `tg_alerta_stock_bajo` — descartado a propósito (era bloqueante).

Las **PK/FK sí** protegen la integridad referencial.

## 7. Gotchas de entorno (Windows + OneDrive) — IMPORTANTES

1. **El venv debe ir FUERA de OneDrive.** OneDrive no soporta hardlinks y bloquea
   archivos → `uv sync` falla dentro del repo. Solución usada:
   `UV_PROJECT_ENVIRONMENT=%USERPROFILE%\.venvs\coremotogestion-api` (+ `link-mode=copy`).
2. **`PYTHONUTF8=1`** al correr: los `print` con emojis revientan con cp1252 si la salida
   se redirige.
3. **Arrancar con `python main.py`, NO `uvicorn main:app` por CLI.** En Windows psycopg
   async requiere `SelectorEventLoop`; `main.py` fija la política **antes** de uvicorn.
   Con el CLI, uvicorn crea el loop (Proactor) antes de importar `main` → `PoolTimeout`.

## 8. Verificación realizada (todo OK)

- Esquema carga sin errores: 18 tablas, 24 vistas, 19 triggers, `audit_log` poblada.
- App arranca contra Postgres (`/` → healthy).
- Lecturas: `/api/marcas`, `/api/marcas/1` (bind `:1`), vistas (resumen, productos+impuestos,
  **órdenes con 6 JOINs**), clientes.
- Escrituras: POST marca → `codMar:11` (secuencia + RETURNING); POST cliente → `audit_log`
  registró el INSERT.
- Endpoints GET de lectura son **públicos** (sin Auth0); las mutaciones igualmente
  respondieron 201 sin token en estas pruebas.

## 9. Cómo correr (resumen — ver `RUN.md`)

```powershell
# BD
docker compose up -d
# Backend
$env:UV_PROJECT_ENVIRONMENT="$env:USERPROFILE\.venvs\coremotogestion-api"; $env:PYTHONUTF8="1"
uv run python main.py            # http://localhost:8000  (/docs para Swagger)
```
Conexión DBeaver: host `localhost`, port `5432`, db `motogestion`, user `us_ppi`, pass `123`.

Front (`core.Motogestion.middle`, Next.js + pnpm): `pnpm install && pnpm dev` (→ :3000).
Su `.env` ya apunta al backend nuevo: `BASE_API_URL=http://localhost:8000/api` y
`NEXT_PUBLIC_API_URL=http://localhost:8000`.

## 10. Limpieza ya hecha y pendientes opcionales

- **Borrado** (basura Oracle): `DDl.sql`, `db_dump.py`, `Scriptsmotogestion/`.
- **Pendiente opcional** (no tocado):
  - Despliegue stale Oracle/GCP: `Dockerfile.prod`, `docker-compose.prod.yaml`,
    `deploy-gcp.sh`, `DEPLOYMENT.md`, `UPDATE_DEPLOYMENT.md`.
  - Código muerto: los 14 repos en inglés (`repository/orders|supplier|operation|sync`,
    `auth/user_business_repository.py`).
  - Reimplementar validaciones de §6 si se necesitan.
  - Renombrar `package.json` del front (`"iluma.base-front"`).
  - Ningún repo nuevo tiene commit aún (solo el `README.md` inicial). Falta `git add/commit/push`.

## 11. Notas para quien retome

- El nombre de clase `OracleDb` y el archivo `oracle_db.py` **son intencionales** (compat);
  internamente es PostgreSQL. Renombrar es opcional y de bajo valor.
- Los secretos (Auth0, DB) están en `.env` (gitignored). Hay `.env.example` de referencia.
- Plan original (previo, desactualizado): `~/.claude/plans/hagamos-el-plan-entonces-playful-wadler.md`.
