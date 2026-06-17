from pydantic import BaseModel


def build_insert(model: BaseModel, key: str, table_name: str, omit_key: bool, sequence_name: str = None):
    params = model.model_dump()
    keys = [k for k in params.keys() if key != k]

    if not omit_key:
        keys.append(key)

    values = [params[k] for k in keys]

    # Si se proporciona una secuencia, agregar la columna de primary key
    # y usar sequence_name.NEXTVAL como valor
    if sequence_name and omit_key:
        columns_list = [key] + keys
        # El primer valor es la secuencia, los demás son los parámetros
        query_values_list = [f"{sequence_name}.NEXTVAL"] + [f":{i + 1}" for i in range(len(values))]

        columns = ", ".join(columns_list)
        query_values = ", ".join(query_values_list)
    else:
        columns = ", ".join(keys)
        query_values = ", ".join([f":{i + 1}" for i in range(len(values))])

    # INSERT simple sin RETURNING
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({query_values})"

    return query, tuple(values)


def build_update(model: BaseModel, key: str, table_name: str):
    """
    Constructs an SQL UPDATE statement for Oracle database.

    This function generates an SQL UPDATE query based on the attributes of the provided Pydantic model. It returns the query and a tuple of values to be updated.

    Args:
        model (BaseModel): An instance of a Pydantic BaseModel containing the data to be updated in the database.
        key (str): The primary key field name of the table, used for identifying the row to update.
        table_name (str): The name of the table where the data will be updated.

    Returns:
        tuple: A tuple containing:
            - query (str): The SQL UPDATE statement as a string.
            - values (tuple): A tuple of values to be updated in the table.
    """

    params = model.model_dump()

    keys = [k for k in params.keys() if key != k]
    values = [params[k] for k in keys]

    # Prepare the columns and query placeholders for the SET clause
    # Oracle placeholders: field = :1, field = :2, etc.
    keys_placeholders = [f"{k} = :{i + 1}" for i, k in enumerate(keys)]

    values.append(params[key])

    columns = ", ".join(keys_placeholders)
    # The WHERE clause uses the next placeholder number
    where_placeholder = f":{len(values)}"
    query = f"UPDATE {table_name} SET {columns} WHERE {key} = {where_placeholder}"

    return query, tuple(values)
