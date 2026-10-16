"""F1-00: aplica las migraciones versionadas de db/migrations/ contra la base de
datos configurada por las variables DB_* (mismas que usa la app -- ver config.py).

Uso:
    python scripts/migrate.py status   # lista migraciones, no cambia nada
    python scripts/migrate.py up       # aplica las pendientes, en orden

Convenciones de los archivos en db/migrations/ (ver README.md para el checklist
completo de cómo agregar una migración nueva):
  - Nombre NNN_descripcion.sql (3 dígitos, minúsculas, guion bajo).
  - Nunca un BEGIN/COMMIT propio: este script ya envuelve cada archivo en su
    propia transacción. Un COMMIT dentro del archivo la cortaría a la mitad --
    si algo falla después, el archivo ya habría quedado aplicado pero
    schema_migrations nunca se habría actualizado (reintento = doble aplicación).
  - Columnas nuevas siempre al final de su tabla (antes de los CONSTRAINT):
    ALTER TABLE ... ADD COLUMN agrega al final físico: si al foldear el mismo
    cambio a mano en full_schema_v2_multitenant.sql una columna queda en otra
    posición "lógica", el pg_dump de "baseline + migraciones" deja de ser
    idéntico al de full_schema.sql aunque el esquema real sea equivalente.
"""
import re
import sys
import time
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"
VERSION_PATTERN = re.compile(r"^\d{3}_[a-z0-9_]+$")


def connect(intentos: int = 10, espera_segundos: float = 2) -> psycopg.Connection:
    """Reintenta la conexión unos segundos: el paso de deploy usa
    `docker compose run --no-deps`, que no espera el healthcheck de `db`."""
    c = settings.db_config
    ultimo_error: Exception | None = None
    for intento in range(1, intentos + 1):
        try:
            return psycopg.connect(
                host=c.host, port=c.port, user=c.user, password=c.password,
                dbname=c.dbname, connect_timeout=5, autocommit=False,
            )
        except psycopg.OperationalError as e:
            ultimo_error = e
            if intento < intentos:
                time.sleep(espera_segundos)
    sys.exit(f"No se pudo conectar a Postgres tras {intentos} intentos: {ultimo_error}")


def ensure_tracking_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "  version TEXT PRIMARY KEY,"
            "  applied_at TIMESTAMP NOT NULL DEFAULT now()"
            ")"
        )
    conn.commit()


def list_files() -> list[Path]:
    archivos = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for f in archivos:
        if not VERSION_PATTERN.match(f.stem):
            sys.exit(f"Nombre de migración inválido (debe ser NNN_algo): {f.name}")
    return archivos


def applied_versions(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations")
        return {fila[0] for fila in cur.fetchall()}


def cmd_status() -> None:
    conn = connect()
    ensure_tracking_table(conn)
    aplicadas = applied_versions(conn)
    for f in list_files():
        marca = "[x]" if f.stem in aplicadas else "[ ]"
        print(f"{marca} {f.stem}")
    conn.close()


def cmd_up() -> None:
    conn = connect()
    ensure_tracking_table(conn)
    aplicadas = applied_versions(conn)
    pendientes = [f for f in list_files() if f.stem not in aplicadas]

    if not pendientes:
        print("Nada pendiente.")
        conn.close()
        return

    for f in pendientes:
        print(f"Aplicando {f.stem}...")
        print(
            "  recordatorio: si esta migración actualiza/borra filas de una tabla "
            "con RLS, fija app.tenant_id por taller o afectará 0 filas sin error."
        )
        try:
            with conn.cursor() as cur:
                # Sin parámetros: psycopg manda el archivo completo por el
                # protocolo simple de Postgres -- todas las sentencias corren
                # atómicas en la transacción ya abierta (autocommit=False).
                cur.execute(f.read_text(encoding="utf-8"))
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)", (f.stem,)
                )
            conn.commit()
            print("  OK")
        except Exception as e:
            conn.rollback()
            sys.exit(f"Fallo en {f.stem}, revertido: {e}")

    conn.close()


COMANDOS = {"status": cmd_status, "up": cmd_up}


if __name__ == "__main__":
    comando = sys.argv[1] if len(sys.argv) > 1 else ""
    accion = COMANDOS.get(comando)
    if accion is None:
        sys.exit("uso: migrate.py status|up")
    accion()
