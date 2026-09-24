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
# -E (errtrace): sin esto, el trap ERR de más abajo NO se ejecuta cuando el error
# ocurre dentro de una función (dump, subir_fuera_de_la_vm) — que es donde pasa
# todo el trabajo real de este script. Sin -E, un pg_dump/gzip/curl fallido corta
# el script por `set -e` en silencio, sin avisar_falla ni el ping a /fail.
set -Eeuo pipefail

cd "$(dirname "$0")/.."

# Las dos variables de arriba viven en el .env de la app (no en el contenedor de
# Postgres). NO se hace `source .env`: ese archivo está pensado para Docker Compose,
# no para bash, y una contraseña con '$' o '&' (perfectamente válida ahí) rompería el
# script al ejecutarse como código en vez de leerse como texto. Se lee solo lo que
# hace falta, como texto plano.
leer_env() {
    [ -f .env ] || return 0
    # `tr -d '\r'`: si el .env se editó alguna vez desde Windows, las líneas quedan
    # con \r al final; grep en Linux no lo quita solo, y un \r invisible al final de
    # la URL hace que curl falle de forma difícil de diagnosticar en los logs.
    # El `|| true` es necesario: con `pipefail`, que la variable simplemente no esté
    # en el .env (grep sin match, el caso normal) abortaría el script entero.
    grep -E "^$1=" .env | tail -n1 | cut -d= -f2- | tr -d '\r' \
        | sed 's/^"//; s/"$//; s/^'"'"'//; s/'"'"'$//' || true
}
BACKUP_PAR_URL="${BACKUP_PAR_URL:-$(leer_env BACKUP_PAR_URL)}"
BACKUP_HEALTHCHECK_URL="${BACKUP_HEALTHCHECK_URL:-$(leer_env BACKUP_HEALTHCHECK_URL)}"

BACKUP_DIR="${BACKUP_DIR:-$PWD/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
STAMP="$(date +%Y%m%d_%H%M%S)"

# Definido temprano (antes del chequeo de más abajo) para que el aviso inmediato de
# falla cubra también el caso de configuración inválida, no solo los errores de
# pg_dump/gzip/curl que pasan por acá vía el trap ERR.
avisar_falla() {
    rm -f "$BACKUP_DIR"/*.tmp 2>/dev/null || true
    # Aviso inmediato en vez de esperar el periodo de gracia de Healthchecks.
    [ -n "$BACKUP_HEALTHCHECK_URL" ] && curl -fsS --max-time 10 "${BACKUP_HEALTHCHECK_URL%/}/fail" > /dev/null || true
}
trap avisar_falla ERR

# El modo "solo local" (sin BACKUP_PAR_URL) tiene sentido en desarrollo, pero en
# producción ya hay heartbeat configurado — si un día falta el PAR (.env recreado,
# despliegue nuevo) el backup dejaría de salir de la VM y Healthchecks seguiría en
# verde igual. Falla fuerte en vez de fallar en silencio. `exit` no dispara el trap
# ERR, así que se llama a avisar_falla a mano para no esperar el periodo de gracia.
if [ -n "$BACKUP_HEALTHCHECK_URL" ] && [ -z "$BACKUP_PAR_URL" ]; then
    echo "$(date -Is) ERROR hay BACKUP_HEALTHCHECK_URL pero falta BACKUP_PAR_URL: el backup no saldría de la VM" >&2
    avisar_falla
    exit 1
fi

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

# Si BACKUP_PAR_URL no está configurada y tampoco hay heartbeat (el caso de
# desarrollo, sin bucket todavía), el backup sigue siendo válido pero solo local. Si
# hay heartbeat sin PAR, el chequeo de arriba ya abortó el script antes de llegar acá.
subir_fuera_de_la_vm() {
    local file="$1"
    local nombre
    nombre="$(basename "$file")"
    if [ -z "${BACKUP_PAR_URL:-}" ]; then
        echo "$(date -Is) AVISO BACKUP_PAR_URL no configurada: $nombre queda solo local"
        return 0
    fi
    # -T sube el archivo en streaming (PUT), sin cargarlo entero en memoria como hacía
    # --data-binary — importa en una VM chica a medida que crece la base. El timeout
    # queda holgado porque la BD de n8n (historial de ejecuciones) puede crecer rápido.
    curl -fsS --max-time 300 -X PUT -T "$file" \
        "${BACKUP_PAR_URL%/}/$nombre" > /dev/null
    echo "$(date -Is) OK subido a Object Storage: $nombre"
}

dump motogestion POSTGRES_DB
dump n8n N8N_DB_NAME

find "$BACKUP_DIR" -name '*.sql.gz' -mtime +"$KEEP_DAYS" -delete

# Heartbeat AL FINAL, solo si todo lo de arriba (dump + gzip + subida) salió bien —
# set -e ya habría abortado el script antes de llegar acá si algo falló. Un fallo
# de red pegándole a Healthchecks.io no debe hacer fallar un backup que sí funcionó.
if [ -n "${BACKUP_HEALTHCHECK_URL:-}" ]; then
    curl -fsS --max-time 10 --retry 3 "$BACKUP_HEALTHCHECK_URL" > /dev/null || true
fi
