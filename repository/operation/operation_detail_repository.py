from typing import List, Dict

from repository.base_repository import BaseRepository


class OperationDetailRepository(BaseRepository):
    def __init__(self):
        super().__init__("operation", "operation_detail", "operation_detail_id")

    async def get_vw_operation_detail_by_operation_id(
        self, operation_id: int
    ) -> List[Dict]:
        return await self.execute(
            "select * from operation.vw_operation_detail where  operation_id = %s",
            (operation_id,),
        )
