from typing import Dict, List

from repository.base_repository import BaseRepository


class DocumentRepository(BaseRepository):
    def __init__(self):
        super().__init__("orders", "document", "document_id")

    async def get_by_order(self, order_id: int) -> List[Dict]:
        return await self.execute(
            "select * from orders.vw_document where order_id = %s", (order_id,)
        )
