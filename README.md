# core.Motogestion.api

## Seguridad multi-tenant (RLS)

Cada taller solo ve sus propios datos gracias a Row-Level Security (RLS) de Postgres:
las tablas de negocio tienen columna `cod_taller` y `FORCE ROW LEVEL SECURITY` con una
policy que compara contra `current_setting('app.tenant_id')`. El tenant se resuelve del
JWT en cada request (`infrastructure/dependencies/tenant_request.py::resolve_tenant`) y
se fija en la sesión de BD antes de cada query
(`repository/data/database.py::_apply_tenant`); sin sesión válida, `app.tenant_id` cae a
`-1` (ningún taller), no a "todos los talleres".

**Esto solo funciona si el rol de BD de la app no es superusuario ni tiene
`BYPASSRLS`** — cualquiera de los dos anula el RLS por completo y de forma silenciosa.
Por eso la app verifica el rol al arrancar (`repository/data/db_pool.py::init_pool`) y
**se niega a arrancar** si detecta un rol privilegiado.

`tests/rls_coverage_test.py` corre en CI contra Postgres real y falla si: alguna tabla
nueva con `cod_taller` queda sin RLS forzado, alguna vista `vw_*` pierde
`security_invoker`, alguna policy queda incompleta (sin `USING`/`WITH CHECK` para todos
los comandos), o aparece una función `SECURITY DEFINER` propiedad de un superusuario.

### Excepciones documentadas al RLS

Tres tablas con `cod_taller` **no** llevan RLS a propósito (lista también en
`infrastructure/utils/rls_policy.py::EXCEPCIONES_RLS`, fuente única de verdad citada
por el test de cobertura):

| Tabla | Por qué no tiene RLS | Cómo se aísla en su lugar |
|---|---|---|
| `pagos` | Billing de plataforma; el webhook de Wompi llega sin sesión de usuario y debe poder resolver el pago por su referencia. | Filtro explícito `WHERE cod_taller = :1` en `PagoRepositorio`, usando el taller del usuario autenticado (`require_admin`). |
| `usuarios_identidad` | Resuelve el taller del usuario a partir del `sub` de Auth0 **antes** de poder fijar `app.tenant_id` — es el mecanismo que hace posible el resto del RLS. | Es de solo lectura interna; ningún endpoint la expone directamente. |
| `talleres` | Es la raíz del tenant (no tiene un tenant "padre" contra el cual aislarse). | Los endpoints que reciben `cod_taller` como parámetro (`GET`/`PUT /talleres/{cod_taller}`) están protegidos con `require_super_admin`, no con RLS. |

El aislamiento a nivel de aplicación de estas tres excepciones se prueba en
`tests/aislamiento_multitenant_test.py`.

## Backups y restauración

`scripts/backup_postgres.sh` corre por cron todos los días a las 03:00 (hora del
servidor) en la VM de producción y hace, por cada BD (`motogestion` y `n8n`):

1. `pg_dump` comprimido con `gzip`, verificado con `gzip -t` antes de darlo por bueno.
2. Copia fuera de la VM: `PUT` a un bucket de Oracle Object Storage vía una
   **Pre-Authenticated Request de solo escritura** (`BACKUP_PAR_URL` en `.env` —
   ver `.env.prod.example`). Sin esta variable, el backup sigue corriendo pero
   queda solo local (para no romper si el bucket aún no existe).
3. Rotación local a 7 días (`KEEP_DAYS`). En el bucket, 30 días por una regla de
   ciclo de vida configurada directamente en la consola de Oracle (Object Storage →
   bucket → Lifecycle Policy Rules) — el script no la gestiona.
4. Si todo lo anterior salió bien, un ping a Healthchecks.io (`BACKUP_HEALTHCHECK_URL`
   en `.env`). Si un día el backup no corre o falla, Healthchecks.io avisa por correo
   por no haber recibido el ping a tiempo.

### Restaurar un backup

El PAR de subida es **solo de escritura** a propósito (si alguien comprometiera esa
URL, no podría leer ni borrar backups existentes) — para restaurar hace falta bajar
el archivo con otro método: una PAR de lectura generada al momento en la consola
(Object Storage → bucket → objeto → Pre-Authenticated Request), o el botón
"Download" de la consola.

```bash
# 1. Bajar el backup (reemplaza la URL por la que generes para leer ese objeto)
curl -o motogestion.sql.gz "<PAR_DE_LECTURA_O_URL_FIRMADA>"

# 2. Restaurar en una BD limpia (ejemplo con un Postgres nuevo, ajusta host/usuario):
gunzip -c motogestion.sql.gz | psql -U mt_app -h <host> -d motogestion_restaurada

# 3. Apuntar una instancia de la API a esa BD (DB_NAME=motogestion_restaurada en su
#    .env) y confirmar que responde: GET /health y algún endpoint que lea datos
#    reales (ej. GET /api/clientes con un usuario válido).
```
