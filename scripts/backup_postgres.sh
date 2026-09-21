#!/usr/bin/env bash
# Backup de Postgres (BD de la app + BD de n8n) con pg_dump, comprimido y con rotación.
#
# Uso manual:   ./scripts/backup_postgres.sh
# Con cron (todos los días 03:00, hora del servidor = UTC en Oracle):
#   0 3 * * * /home/ubuntu/app/scripts/backup_postgres.sh >> /home/ubuntu/app/backups/backup.log 2>&1
#
# Variables opcionales: BACKUP_DIR (por defecto ./backups) y KEEP_DAYS (por defecto 7).
# OJO: los backups quedan en la MISMA VM. Copia la carpeta fuera (rclone, scp, Object
# Storage de Oracle) para sobrevivir a la pérdida de la máquina.
set -euo pipefail

cd "$(dirname "$0")/.."
BACKUP_DIR="${BACKUP_DIR:-$PWD/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# pg_dump corre DENTRO del contenedor con el superusuario, así que lee los nombres
# de BD de las variables del propio contenedor (no hace falta cargar el .env aquí).
dump() { # $1 = nombre del archivo, $2 = variable del contenedor con el nombre de la BD
    local out="$BACKUP_DIR/$1_$STAMP.sql.gz"
    docker compose exec -T db sh -c "pg_dump -U \"\$POSTGRES_USER\" -d \"\$$2\"" \
        | gzip > "$out.tmp"
    gzip -t "$out.tmp"           # verifica que el archivo no quedó corrupto
    mv "$out.tmp" "$out"
    echo "$(date -Is) OK $out ($(du -h "$out" | cut -f1))"
}

trap 'rm -f "$BACKUP_DIR"/*.tmp' ERR
dump motogestion POSTGRES_DB
dump n8n N8N_DB_NAME

find "$BACKUP_DIR" -name '*.sql.gz' -mtime +"$KEEP_DAYS" -delete
