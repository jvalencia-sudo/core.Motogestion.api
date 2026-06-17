from typing import List, Dict

from repository.base_repository import BaseRepository


class SupplierOperationEmailRepository(BaseRepository):
    def __init__(self):
        super().__init__(
            "supplier", "supplier_operation_email", "supplier_operation_email_id"
        )

    async def get_suppliers_notified(self, operation_id: int) -> List[Dict]:
        return await self.execute(
            "select * from supplier.vw_supplier_operation_email where operation_id = %s",
            (operation_id,),
        )

    async def get_notified_suppliers_by_operation_supplier(
        self, operation_id: int, supplier_id: int
    ) -> List[Dict]:
        return await self.execute(
            "select * from supplier.vw_supplier_operation_email where operation_id = %s and supplier_id = %s",
            (operation_id, supplier_id),
        )
