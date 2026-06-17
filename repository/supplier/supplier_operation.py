import uuid
from typing import Dict, Optional

from repository.base_repository import BaseRepository


class SupplierOperationRepository(BaseRepository):
    def __init__(self):
        super().__init__("supplier", "supplier_operation", "supplier_operation_id")

    async def get_operation_by_key(self, key: uuid.UUID) -> Optional[Dict]:
        return await self.get_one(
            "SELECT * FROM supplier.supplier_operation WHERE key = %s",
            (key,),
        )

    async def get_supplier_operation(
        self, operation_id: int, supplier_id: int
    ) -> Optional[Dict]:
        return await self.get_one(
            query="select * from supplier.supplier_operation WHERE operation_id = %s AND supplier_id = %s",
            params=(operation_id, supplier_id),
        )
