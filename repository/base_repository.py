from typing import Dict, List, Optional, Tuple, Any

from pydantic import BaseModel
from six import string_types
from typing_extensions import NoReturn

from infrastructure.utils.query import build_insert, build_update
from repository.data.database import Database

Params = Tuple[Any, ...]


class BaseRepository:
    def __init__(
        self,
        schema: str,
        table_name: str,
        primary_key: str,
        omit_key: bool = True,
        sequence_name: str = None,
        db: Database = Database(),
    ):
        self.db = db
        self.schema = schema
        self.table_name = table_name
        self.primary_key = primary_key
        self.omit_key = omit_key
        self.sequence_name = sequence_name

    def __quote_sql_string__(self, value):
        """
        If `value` is a string type, escapes single quotes in the string
        and returns the string enclosed in single quotes.
        """
        if isinstance(value, string_types):
            new_value = str(value)
            new_value = new_value.replace("'", "''")
            return "'{}'".format(new_value)
        return value

    def build_select(self):
        return f"SELECT * FROM {self.table_name}"

    def build_delete(self):
        return f"DELETE FROM {self.table_name}"

    async def get_all(self) -> List[Dict]:
        """
        Builds and execute the select DML command for the specific entity
        :return: All the elements contained in the entity table
        """
        return await self.db.execute(self.build_select())

    async def get_by_id(self, entity_id: int) -> Dict:
        """
        Builds and execute a select command with a WHERE condition where the value is the entity id
        :param entity_id: The entity id value
        :return: A dict with the record values
        """
        return await self.db.get_first(
            f"SELECT * FROM {self.table_name} WHERE {self.primary_key} = :1",
            (entity_id,),
        )

    async def get_by_field(self, field_name: str, field_value: Any) -> List[Dict]:
        """
        Builds and execute a select command with a WHERE condition for any field
        :param field_name: The field name to filter by
        :param field_value: The field value to filter with
        :return: A list of dicts with the matching records
        """
        return await self.db.execute(
            f"SELECT * FROM {self.table_name} WHERE {field_name} = :1",
            (field_value,),
        )

    async def delete(self, entity_id: int) -> None:
        """
        Builds and execute a delete command with a WHERE condition where the value is the entity id
        :param entity_id: The entity id value
        """
        await self.db.execute_non_query(
            f"DELETE FROM {self.table_name} WHERE {self.primary_key} = :1",
            (entity_id,),
        )

    def parse_model_list(self, model: List[BaseModel]) -> Tuple[str, List[Tuple]]:
        params_list = []
        query = ""
        for m in model:
            q, params = build_insert(
                m, self.primary_key, f"{self.table_name}", self.omit_key, self.sequence_name
            )
            params_list.append(params)
            query = q
        return query, params_list

    async def create(self, model: BaseModel) -> Optional[int]:
        print(f"=== DEBUG CREATE BaseRepository ===")
        # ... tu debug actual ...

        query, params = build_insert(
            model, self.primary_key, f"{self.table_name}", self.omit_key, self.sequence_name
        )

        print(f"Generated query: {query}")
        print(f"Generated params: {params}")
        print(f"Sequence name: {self.sequence_name}")

        # Si usamos secuencia explícita, necesitamos RETURNING para obtener el ID generado
        # Si no hay secuencia pero omit_key=True, también usamos RETURNING (para IDENTITY)
        pk_for_returning = self.primary_key if self.omit_key else None

        new_record = await self.db.insert(query, params, primary_key=pk_for_returning)
        print(f"Insert result: {new_record}")
        print(f"Insert result type: {type(new_record)}")

        # Manejo mejorado del resultado
        if new_record:
            if isinstance(new_record, dict) and self.primary_key in new_record:
                return new_record[self.primary_key]
            else:
                print(
                    f"Available keys in new_record: {new_record.keys() if isinstance(new_record, dict) else 'Not a dict'}")

        # Si no hay resultado, obtener el valor del modelo
        model_data = model.model_dump() if hasattr(model, 'model_dump') else model.dict()
        return model_data.get(self.primary_key)

    async def update(self, model: BaseModel) -> None:
        print(f"=== DEBUG UPDATE BaseRepository ===")
        print(f"Model: {model}")
        print(f"Table: {self.table_name}")
        print(f"Primary key: {self.primary_key}")

        query, params = build_update(
            model, self.primary_key, f"{self.table_name}"
        )

        print(f"Generated update query: {query}")
        print(f"Generated update params: {params}")

        await self.db.execute_non_query(query, params)

    async def execute(self, query: str, params: Optional[Params]) -> List[Dict]:
        return await self.db.execute(query, params)

    async def execute_values(self, model: List[BaseModel]) -> NoReturn:
        query, params = self.parse_model_list(model)
        await self.db.execute_values(query, params)

    async def execute_non_query(self, query: str, params: Optional[Params]) -> NoReturn:
        return await self.db.execute_non_query(query, params)

    async def get_one(self, query: str, params: Optional[Params]) -> Dict:
        return await self.db.get_first(query, params)

    async def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Executes a custom SQL query
        :param query: The SQL query to execute
        :param params: Optional parameters for the query
        :return: Query results as a list of dictionaries
        """
        return await self.db.execute(query, params)

    # Métodos auxiliares adicionales
    async def get_by_multiple_fields(self, conditions: Dict[str, Any]) -> List[Dict]:
        """
        Get records by multiple field conditions
        :param conditions: Dictionary of field_name: field_value pairs
        :return: List of matching records
        """
        if not conditions:
            return await self.get_all()

        where_clauses = []
        params = []

        for i, (field_name, field_value) in enumerate(conditions.items(), 1):
            where_clauses.append(f"{field_name} = :{i}")
            params.append(field_value)

        where_clause = " AND ".join(where_clauses)
        query = f"SELECT * FROM {self.table_name} WHERE {where_clause}"

        return await self.db.execute(query, tuple(params))

    async def get_with_pagination(self, page: int = 1, page_size: int = 10, order_by: str = None) -> Dict:
        """
        Get paginated results from the table
        :param page: Page number (1-based)
        :param page_size: Number of records per page
        :param order_by: Optional ORDER BY clause
        :return: Dictionary with 'data', 'total', 'page', 'page_size'
        """
        offset = (page - 1) * page_size

        # Count total records
        count_query = f"SELECT COUNT(*) as total FROM {self.table_name}"
        total_result = await self.db.get_first(count_query)
        total = total_result.get('TOTAL', 0) if total_result else 0

        # Build main query with pagination
        base_query = f"SELECT * FROM {self.table_name}"
        if order_by:
            base_query += f" ORDER BY {order_by}"

        # Paginación con OFFSET/FETCH
        paginated_query = f"""
        {base_query}
        OFFSET :1 ROWS FETCH NEXT :2 ROWS ONLY
        """

        data = await self.db.execute(paginated_query, (offset, page_size))

        return {
            'data': data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }

    async def exists(self, field_name: str, field_value: Any) -> bool:
        """
        Check if a record exists with the given field value
        :param field_name: Field name to check
        :param field_value: Field value to check
        :return: True if exists, False otherwise
        """
        query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE {field_name} = :1"
        result = await self.db.get_first(query, (field_value,))
        return result.get('COUNT', 0) > 0 if result else False

    async def get_distinct_values(self, field_name: str) -> List[Any]:
        """
        Get distinct values for a specific field
        :param field_name: Field name to get distinct values from
        :return: List of distinct values
        """
        query = f"SELECT DISTINCT {field_name} FROM {self.table_name} WHERE {field_name} IS NOT NULL ORDER BY {field_name}"
        results = await self.db.execute(query)
        return [row[field_name] for row in results] if results else []

    async def bulk_insert(self, models: List[BaseModel]) -> None:
        """
        Insert multiple records in a single transaction
        :param models: List of model instances to insert
        """
        if not models:
            return

        # Use the first model to build the query structure
        first_model = models[0]
        query, _ = build_insert(first_model, self.primary_key, self.table_name, self.omit_key, self.sequence_name)

        # Build parameters for all models
        params_list = []
        for model in models:
            _, params = build_insert(model, self.primary_key, self.table_name, self.omit_key, self.sequence_name)
            params_list.append(params)

        await self.db.execute_values(query, params_list)

    async def soft_delete(self, entity_id: int, deleted_field: str = 'DELETED', deleted_value: Any = 1) -> None:
        """
        Perform soft delete by updating a field instead of actually deleting the record
        :param entity_id: The entity id value
        :param deleted_field: Field name to mark as deleted
        :param deleted_value: Value to set for the deleted field
        """
        query = f"UPDATE {self.table_name} SET {deleted_field} = :1 WHERE {self.primary_key} = :2"
        await self.db.execute_non_query(query, (deleted_value, entity_id))

    async def get_active_records(self, deleted_field: str = 'DELETED', active_value: Any = 0) -> List[Dict]:
        """
        Get all active (non-soft-deleted) records
        :param deleted_field: Field name that marks records as deleted
        :param active_value: Value that indicates record is active
        :return: List of active records
        """
        query = f"SELECT * FROM {self.table_name} WHERE {deleted_field} = :1"
        return await self.db.execute(query, (active_value,))
