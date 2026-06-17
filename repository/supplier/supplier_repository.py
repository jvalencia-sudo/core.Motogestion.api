from typing import List, Dict

from repository.base_repository import BaseRepository


class SupplierRepository(BaseRepository):
    def __init__(self):
        super().__init__("supplier", "supplier", "supplier_id")

    async def update_status_supplier(self, supplier_id: int, status: bool) -> None:
        query = f"UPDATE {self.table_name} SET status = %s WHERE {self.primary_key} = %s"
        await self.execute_non_query(query, (status, supplier_id))

    async def get_suppliers_by_status(self, status: bool) -> List[Dict]:
        return await self.execute(
            f"SELECT * FROM {self.table_name} WHERE status = %s",
            (status,),
        )
