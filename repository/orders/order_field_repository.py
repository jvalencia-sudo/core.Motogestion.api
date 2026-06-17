from typing import Dict, List

from repository.base_repository import BaseRepository


class OrderFieldRepository(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="orders", table_name="order_fields", primary_key="order_field_id"
        )

    async def get_by_order(self, order_id: int) -> List[Dict]:
        return await self.execute(
            "select * from orders.vw_order_fields where order_id = %s", (order_id,)
        )
