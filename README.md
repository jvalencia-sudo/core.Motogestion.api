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
2. Copia fuera de la VM: `PUT` en streaming (sin cargar el archivo entero en memoria)
   a un bucket de Oracle Object Storage vía una **Pre-Authenticated Request de solo
   escritura** (`BACKUP_PAR_URL` en `.env` — ver `.env.prod.example`). Sin esta
   variable, el backup sigue corriendo pero queda solo local (para no romper si el
   bucket aún no existe) — **excepto si ya hay heartbeat configurado**: en ese caso
   faltar el PAR es un error de configuración, no un modo válido, y el script aborta
   en vez de quedar en verde sin subir nada.
3. Rotación local a 7 días (`KEEP_DAYS`). En el bucket, 30 días por una regla de
   ciclo de vida configurada directamente en la consola de Oracle (Object Storage →
   bucket → Lifecycle Policy Rules) — el script no la gestiona.
4. Si todo lo anterior salió bien, un ping a Healthchecks.io (`BACKUP_HEALTHCHECK_URL`
   en `.env`). Si un día el backup no corre o falla, Healthchecks.io avisa por correo
   por no haber recibido el ping a tiempo; además, si algún paso falla, el script
   avisa de inmediato (`.../fail`) en vez de esperar el periodo de gracia.

Las dos variables de arriba se leen del `.env` como texto plano (solo esas dos líneas),
**nunca con `source .env`**: ese archivo está pensado para Docker Compose, no para
bash, y una contraseña con `$` o `&` (válida ahí) ejecutada como código rompería el
backup de un día para otro.

### Mantenimiento periódico

- **`backups/backup.log` crece sin límite** — en la VM está configurado con
  `logrotate` (`/etc/logrotate.d/motogestion-backup`, rotación semanal, 8 semanas de
  histórico, comprimido).
- **Simulacro de restauración**: repetir el procedimiento de abajo cada 3 meses, no
  solo cuando algo se rompe. El objetivo es notar si el procedimiento se desactualizó
  antes de necesitarlo de verdad.
- **PAR de subida y objetos inmutables**: la PAR es de solo escritura (no puede leer
  ni listar), pero *sí* puede sobrescribir un objeto existente si alguien adivina o
  filtra su nombre (son predecibles: `motogestion_AAAAMMDD_HHMMSS.sql.gz`). Mitigado
  con una **Retention Rule de 30 días** en el bucket (Object Storage → bucket →
  Retention Rules → Create — misma duración que la Lifecycle Rule de borrado), que
  hace los objetos inmutables mientras dura la retención: ni el dueño del bucket ni
  quien tenga la PAR pueden sobrescribirlos o borrarlos antes de esos 30 días.

### Restaurar un backup

El PAR de subida es **solo de escritura** a propósito (si alguien comprometiera esa
URL, no podría leer ni borrar backups existentes) — para restaurar hace falta bajar
el archivo con otro método: una PAR de lectura generada al momento en la consola
(Object Storage → bucket → objeto → Pre-Authenticated Request), o el botón
"Download" de la consola.

```bash
# 1. Bajar el backup (botón Download en la consola, o una PAR de lectura generada
#    al momento para ese objeto) y verificar que no quedó corrupto.
gzip -t motogestion_<fecha>.sql.gz

# 2. Postgres limpio y separado (no toca la BD real). El dump no crea la BD ni el
#    rol — el esquema restaurado espera que el dueño (mt_app) ya exista:
docker run -d --name restore-test-db -e POSTGRES_PASSWORD=<algo> -p 15432:5432 postgres:16
docker exec restore-test-db psql -U postgres -c \
  "CREATE ROLE mt_app LOGIN PASSWORD '<algo>' NOSUPERUSER;"
docker exec restore-test-db createdb -U postgres -O mt_app motogestion_restaurada

# 3. Restaurar (-v ON_ERROR_STOP=1 para que cualquier error real corte el restore
#    en vez de seguir de largo):
gunzip -c motogestion_<fecha>.sql.gz \
  | docker exec -i restore-test-db psql -U postgres -d motogestion_restaurada -v ON_ERROR_STOP=1

# 4. Confirmar RLS intacto y datos reales presentes (ajusta el cod_taller):
docker exec restore-test-db psql -U mt_app -d motogestion_restaurada -c \
  "SET app.tenant_id='1'; SELECT count(*) FROM clientes; SELECT count(*) FROM ordenes_trabajo;"

# 5. La prueba fuerte: la API real, apuntada a esta BD restaurada, respondiendo con
#    datos reales (no solo la BD sirviendo queries sueltas):
docker run -d --name restore-test-backend -p 18000:8000 \
  --link restore-test-db \
  -e DB_HOST=restore-test-db -e DB_PORT=5432 -e DB_USER=mt_app -e DB_PASSWORD=<algo> \
  -e DB_NAME=motogestion_restaurada \
  -e ENVIRONMENT=prod -e PROJECT_NAME=restore-test -e FRONTEND_URL=https://x.example.com \
  -e CORS_ORIGINS=https://x.example.com -e AUTH0_DOMAIN=x.auth0.com -e AUTH0_ALGORITHMS=RS256 \
  -e AUTH0_API_AUDIENCE=https://x.example.com/api -e AUTH0_MANAGEMENT_CLIENT_ID=x \
  -e AUTH0_MANAGEMENT_CLIENT_SECRET=x -e AUTH0_MANAGEMENT_AUDIENCE=https://x.auth0.com/api/v2/ \
  -e AUTH0_CONNECTION_ID=Username-Password-Authentication -e AUTH0_CUSTOMER_ROLE=x -e AUTH0_ADMIN_ROLE=x \
  ghcr.io/jvalencia-sudo/motogestion-backend:<tag-actual-en-produccion>
curl http://localhost:18000/health                    # {"status":"ok"}
curl http://localhost:18000/api/suscripciones/planes   # catálogo público, lee de la BD restaurada

# 6. Limpieza (no afecta producción, todo esto vivió en contenedores aparte):
docker rm -f restore-test-backend restore-test-db
```

**Restauración probada de extremo a extremo el 2026-09-24**: se bajó un backup real
generado ese día desde el bucket (`motogestion_20260924_212528.sql.gz`), se restauró
en un Postgres 16 limpio replicando el rol `mt_app`, el RLS quedó intacto
(`relrowsecurity`/`relforcerowsecurity` en `true`, datos reales visibles solo bajo el
tenant correcto — 10 clientes y 5 órdenes de trabajo para el taller de prueba), y la
imagen real del backend (`ghcr.io/jvalencia-sudo/motogestion-backend`), apuntada a esa
BD restaurada, respondió `{"status":"ok"}` en `/health` y devolvió datos reales en
`/api/suscripciones/planes`.
