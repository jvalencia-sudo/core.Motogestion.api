from typing import List, Dict

from repository.base_repository import BaseRepository


class OrderProductRepository(BaseRepository):
    def __init__(self):
        super().__init__("orders", "order_product", "order_product_id")

    async def get_by_order(self, order_id: int) -> List[Dict]:
        return await self.execute(
            "select * from orders.vw_order_product where order_id = %s", (order_id,)
        )
