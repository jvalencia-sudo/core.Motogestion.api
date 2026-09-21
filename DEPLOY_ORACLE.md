# Despliegue en Oracle Cloud (VM ARM, Ubuntu 24.04)

Stack: Caddy (HTTPS) + Postgres 16 + backend FastAPI + n8n, todo con
`docker-compose.prod.yml`. Solo Caddy publica puertos (80/443).

- API: https://api-jfv.duckdns.org
- n8n: https://n8n-jfv.duckdns.org

En la VM la carpeta de trabajo es `~/app` (ahí ya está el `Caddyfile`; el deploy
no lo pisa). Ejemplos con usuario `ubuntu`; cambia `<IP_VM>` y `<LLAVE.key>`.

## 0. Antes de empezar (una sola vez)

- DuckDNS: `api-jfv` y `n8n-jfv` apuntan a la IP pública de la VM.
- Puertos 80 y 443 abiertos en **dos** sitios: la Security List de la VCN (consola de
  Oracle) y el firewall de la propia VM (las imágenes de Ubuntu de Oracle bloquean todo
  con `iptables`):
  ```bash
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
  sudo netfilter-persistent save
  ```
- Sin esto Let's Encrypt no puede validar el dominio y Caddy no obtiene certificado.

## 1. Copiar el proyecto a la VM (desde tu PC)

No uses `git clone` en la VM mientras tengas cambios sin commitear: no viajarían.
Cada comando va en **una sola línea** y sirve igual en `cmd` que en PowerShell.
Reemplaza `C:\ruta\llave.key` por tu llave privada y `1.2.3.4` por la IP de la VM.

```
cd C:\Users\USUARIO\OneDrive\Documentos\Trabajo\Personal\core.Motogestion.api

tar --exclude=.venv --exclude=.git --exclude=.claude --exclude=__pycache__ --exclude=.env --exclude=backups --exclude=*.sqlite --exclude=docker-compose.yaml -czf ..\motogestion.tgz .

scp -i C:\ruta\llave.key ..\motogestion.tgz ubuntu@1.2.3.4:~/

ssh -i C:\ruta\llave.key ubuntu@1.2.3.4 "mkdir -p ~/app && chmod -R u+w ~/app && tar --delay-directory-restore -xzf ~/motogestion.tgz -C ~/app 2>&1 | grep -v SCHILY; chmod -R u+w ~/app; rm ~/motogestion.tgz"
```

`--delay-directory-restore` es necesario: el `tar` de Windows guarda las carpetas como
solo lectura (`dr-xr-xr-x`, por el atributo de OneDrive) y mezcla sus entradas; sin la
opción, Linux bloquea cada carpeta antes de terminar de llenarla y falla con
`Permission denied`. El `grep -v SCHILY` oculta solo los avisos `SCHILY.fflags`
(inofensivos) y deja pasar los errores reales.

El `.tgz` se crea en la carpeta de arriba (`..`) para que no se empaquete a sí mismo.

Extraer sobre `~/app` conserva tu `Caddyfile`, tu `.env` y tus volúmenes.

## 2. Crear el `.env` real (en la VM)

```bash
ssh -i C:\ruta\llave.key ubuntu@1.2.3.4
cd ~/app
cp .env.prod.example .env
chmod 600 .env

# Genera y muestra los secretos (cópialos al .env con nano)
echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
echo "APP_DB_PASSWORD=$(openssl rand -hex 24)"
echo "N8N_DB_PASSWORD=$(openssl rand -hex 24)"
echo "N8N_ENCRYPTION_KEY=$(openssl rand -hex 32)"
nano .env
```

Rellena además `CORS_ORIGINS` y `FRONTEND_URL` (dominio de Vercel, con `https://` y sin
`/` final) y los valores de Auth0. Guarda `N8N_ENCRYPTION_KEY` en un gestor de
contraseñas. Deja `COMPOSE_FILE=docker-compose.prod.yml` tal cual.

Comprueba antes de levantar (no imprime secretos si solo miras el código de salida):
```bash
docker compose config -q && echo "compose OK"
ls Caddyfile
```

## 3. Levantar

```bash
cd ~/app
docker compose up -d --build     # la primera vez compila el backend en la VM (2-5 min)
docker compose ps                # db y backend deben quedar "healthy"
```

El primer arranque crea el rol de la app, la BD de n8n y carga
`db/full_schema_v2_multitenant.sql`. Ese init **solo corre con el volumen vacío**.

Verifica:
```bash
curl -s https://api-jfv.duckdns.org/health        # {"status":"ok"}
curl -sI https://n8n-jfv.duckdns.org | head -1     # HTTP/2 200
```
Abre https://n8n-jfv.duckdns.org **de inmediato** y crea la cuenta owner: la primera
persona que entre se queda con la instancia.

## 4. Logs y operación diaria

```bash
docker compose logs -f backend          # seguir logs (Ctrl+C para salir)
docker compose logs --tail=100 caddy    # certificados / errores de proxy
docker compose logs --tail=100 n8n
docker compose ps
docker compose restart backend
docker stats --no-stream
```

## 5. Actualizar el backend después de un cambio

Repite el paso 1 (empaquetar y copiar) y luego, en la VM:
```bash
cd ~/app
docker compose up -d --build backend
docker compose logs -f backend
```
Solo se reconstruye el backend; db, n8n y Caddy no se tocan.

Si el cambio incluye un SQL nuevo (migración), aplícalo como el rol de la app para
que las tablas sigan siendo suyas:
```bash
docker compose exec -T db sh -c 'PGPASSWORD="$APP_DB_PASSWORD" psql -h 127.0.0.1 -U "$APP_DB_USER" -d "$POSTGRES_DB"' < db/migration_XXXX.sql
```

## 6. Backups

```bash
chmod +x scripts/backup_postgres.sh
./scripts/backup_postgres.sh            # prueba manual → ./backups/*.sql.gz
crontab -e
```
Línea de cron (diario 03:00 UTC, conserva 7 días):
```
0 3 * * * /home/ubuntu/app/scripts/backup_postgres.sh >> /home/ubuntu/app/backups/backup.log 2>&1
```
Los backups viven en la misma VM: copia `~/app/backups` fuera de vez en cuando
(por ejemplo `scp` a tu PC o rclone al Object Storage de Oracle).

Restaurar la BD de la app (vacía el schema y recarga el dump):
```bash
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public AUTHORIZATION $APP_DB_USER;"'
gunzip -c backups/motogestion_YYYYMMDD_HHMMSS.sql.gz | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## 7. Configurar Vercel (el front hoy apunta al backend de David)

En Vercel → Project → Settings → Environment Variables (Production):

| Variable | Valor nuevo |
|---|---|
| `BASE_API_URL` | `https://api-jfv.duckdns.org/api` |
| `NEXT_PUBLIC_API_URL` | `https://api-jfv.duckdns.org` |

Luego **Redeploy** desactivando "Use existing Build Cache": `NEXT_PUBLIC_*` se incrusta
en el build, así que sin rebuild seguiría apuntando al backend viejo.

- `BASE_API_URL` la usa el middleware de Next para reescribir `/api/*` hacia el backend
  (servidor → servidor, sin CORS). `NEXT_PUBLIC_API_URL` arma las URLs de los PDF.
- CORS del backend (`CORS_ORIGINS` en la VM) debe ser el dominio de Vercel, exacto. Tras
  cambiarlo: `docker compose up -d backend` (recrea el contenedor con el `.env` nuevo).
- Auth0: el backend valida contra el mismo tenant, así que no cambia nada mientras el
  dominio de Vercel sea el mismo. Si cambia, actualiza Allowed Callback/Logout/Web Origins.

## 8. Notas

- Todas las contraseñas de BD deben ser hex/alfanuméricas: el backend arma el DSN de
  Postgres sin comillas y un espacio o símbolo lo rompería.
- BD nueva = solo el taller 1 de demo y sin usuarios. Puedes registrar un taller desde
  `/registro` en el front, o pre-registrar correos con SQL (mira `db/seed_usuarios_demo.sql`
  y ajústalo antes de correrlo).
- n8n avisa que Postgres 16 está "fuera del rango soportado" (compatibilidad parcial).
  Funciona (probado: n8n crea sus tablas y responde en `/healthz`). Subir `db` a
  `postgres:17` quitaría el aviso, pero el esquema de la app solo está probado en 16.
- Oracle puede reclamar VMs Always Free casi sin uso; pasar la cuenta a Pay-As-You-Go
  (sin salirte de lo gratis) lo evita.
