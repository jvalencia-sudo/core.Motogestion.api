from typing import List, Dict, Optional

from infrastructure.commons.enums.operation_status import OperationStatus
from repository.base_repository import BaseRepository


class OperationRepository(BaseRepository):
    def __init__(self):
        super().__init__("operation", "operation", "operation_id")

    async def get_vw_operations_by_user(self, user_id: int) -> List[Dict]:
        return await self.execute(
            "select * from operation.vw_operation where  user_id = %s", (user_id,)
        )

    async def get_vw_operations_by_operation(self, operation_id: int) -> Dict:
        return await self.get_one(
            "select * from operation.vw_operation where  operation_id = %s",
            (operation_id,),
        )

    async def get_all_operations(self) -> Dict:
        return await self.execute(
            "select * from operation.vw_operation",
        )

    async def get_vw_operations_details_by_operation_id(
        self, operation_id: int
    ) -> Optional[Dict]:
        return await self.get_one(
            "select * from operation.vw_operation_details where operation_id = %s",
            (operation_id,),
        )

    async def update_status_operation(
        self, operation_id: int, status_id: OperationStatus
    ) -> None:
        query = f"UPDATE {self.table_name} SET operation_status_id = %s WHERE {self.primary_key} = %s"
        await self.execute_non_query(query, (status_id, operation_id))
