from pydantic import BaseModel


def build_insert(model: BaseModel, key: str, table_name: str, omit_key: bool, sequence_name: str = None):
    """Construye un INSERT para PostgreSQL (placeholders %s de psycopg).

    Si omit_key=True la columna de la llave primaria se OMITE del INSERT: en
    Postgres el valor lo aporta el DEFAULT nextval('seq_*') de la secuencia
    (o un trigger, p.ej. ordenes_trabajo). El parametro sequence_name se conserva
    por compatibilidad de firma pero ya no se usa para generar el valor.
    """
    params = model.model_dump()
    keys = [k for k in params.keys() if key != k]

    if not omit_key:
        keys.append(key)

    values = [params[k] for k in keys]

    columns = ", ".join(keys)
    placeholders = ", ".join(["%s"] * len(values))

    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    return query, tuple(values)


def build_update(model: BaseModel, key: str, table_name: str):
    """
    Construye un UPDATE para PostgreSQL (placeholders %s de psycopg).

    Args:
        model (BaseModel): instancia Pydantic con los datos a actualizar.
        key (str): nombre de la llave primaria (condicion del WHERE).
        table_name (str): nombre de la tabla.

    Returns:
        tuple: (query: str, values: tuple)
    """
    params = model.model_dump()

    keys = [k for k in params.keys() if key != k]
    values = [params[k] for k in keys]

    set_clause = ", ".join([f"{k} = %s" for k in keys])

    values.append(params[key])

    query = f"UPDATE {table_name} SET {set_clause} WHERE {key} = %s"

    return query, tuple(values)
