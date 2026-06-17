from typing import Dict, List

from repository.base_repository import BaseRepository


class OrderStepRepository(BaseRepository):
    def __init__(self):
        super().__init__("orders", "order_step", "order_step_id")

    async def get_by_order(self, order_id: int) -> List[Dict]:
        return await self.execute(
            "select * from orders.vw_order_step where order_id = %s", (order_id,)
        )
