from typing import Dict, List, Optional

from repository.base_repository import BaseRepository


class MessageRepository(BaseRepository):
    def __init__(self):
        super().__init__("orders", "message", "message_id")

    async def get_by_order(self, order_id: int) -> List[Dict]:
        return await self.execute(
            f"{self.build_select()} where order_id = %s", (order_id,)
        )

    async def get_recent_messages(self, customer_id: Optional[int]) -> List[Dict]:
        if customer_id:
            return await self.execute(
                "select * from orders.vw_message where customer_id = %s order by created_at desc limit 5",
                (customer_id,),
            )
        return await self.execute(
            "select * from orders.vw_message order by created_at desc limit 5",
            None,
        )
