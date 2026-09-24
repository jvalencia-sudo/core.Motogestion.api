#!/usr/bin/env bash
# Backup de Postgres (BD de la app + BD de n8n) con pg_dump, comprimido, con rotación
# local Y copia fuera de la VM (Oracle Object Storage) — si se pierde la máquina, el
# backup sobrevive.
#
# Uso manual:   ./scripts/backup_postgres.sh
# Con cron (todos los días 03:00, hora del servidor = UTC en Oracle):
#   0 3 * * * /home/ubuntu/app/scripts/backup_postgres.sh >> /home/ubuntu/app/backups/backup.log 2>&1
#
# Variables opcionales: BACKUP_DIR (por defecto ./backups) y KEEP_DAYS (por defecto 7,
# retención LOCAL — la del bucket es una regla de ciclo de vida de 30 días, configurada
# en la consola de Oracle, no acá).
#
# Variables del .env de producción (ver .env.prod.example), ambas opcionales — si
# faltan, el backup sigue siendo solo local, como antes:
#   BACKUP_PAR_URL          Pre-Authenticated Request de Object Storage, SOLO
#                           escritura, sobre el bucket de backups.
#   BACKUP_HEALTHCHECK_URL  Ping de Healthchecks.io al terminar con éxito (si un día
#                           no llega, Healthchecks.io avisa por correo).
set -euo pipefail

cd "$(dirname "$0")/.."

# Las dos variables de arriba viven en el .env de la app (no en el contenedor de
# Postgres), así que se cargan acá si el archivo existe.
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

BACKUP_DIR="${BACKUP_DIR:-$PWD/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# pg_dump corre DENTRO del contenedor con el superusuario, así que lee los nombres
# de BD de las variables del propio contenedor (no hace falta el .env para esto).
dump() { # $1 = nombre del archivo, $2 = variable del contenedor con el nombre de la BD
    local out="$BACKUP_DIR/$1_$STAMP.sql.gz"
    docker compose exec -T db sh -c "pg_dump -U \"\$POSTGRES_USER\" -d \"\$$2\"" \
        | gzip > "$out.tmp"
    gzip -t "$out.tmp"           # verifica que el archivo no quedó corrupto
    mv "$out.tmp" "$out"
    echo "$(date -Is) OK $out ($(du -h "$out" | cut -f1))"
    subir_fuera_de_la_vm "$out"
}

# Si BACKUP_PAR_URL no está configurada, el backup sigue siendo válido pero solo
# local (comportamiento de antes) — no falla el script por no tener aún el bucket.
subir_fuera_de_la_vm() {
    local file="$1"
    local nombre
    nombre="$(basename "$file")"
    if [ -z "${BACKUP_PAR_URL:-}" ]; then
        echo "$(date -Is) AVISO BACKUP_PAR_URL no configurada: $nombre queda solo local"
        return 0
    fi
    curl -fsS --max-time 120 -X PUT --data-binary "@$file" \
        "${BACKUP_PAR_URL%/}/$nombre" > /dev/null
    echo "$(date -Is) OK subido a Object Storage: $nombre"
}

trap 'rm -f "$BACKUP_DIR"/*.tmp' ERR
dump motogestion POSTGRES_DB
dump n8n N8N_DB_NAME

find "$BACKUP_DIR" -name '*.sql.gz' -mtime +"$KEEP_DAYS" -delete

# Heartbeat AL FINAL, solo si todo lo de arriba (dump + gzip + subida) salió bien —
# set -e ya habría abortado el script antes de llegar acá si algo falló. Un fallo
# de red pegándole a Healthchecks.io no debe hacer fallar un backup que sí funcionó.
if [ -n "${BACKUP_HEALTHCHECK_URL:-}" ]; then
    curl -fsS --max-time 10 --retry 3 "$BACKUP_HEALTHCHECK_URL" > /dev/null || true
fi
