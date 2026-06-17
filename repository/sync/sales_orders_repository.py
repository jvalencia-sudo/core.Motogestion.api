from repository.base_repository import BaseRepository


class SalesOrdersRepository(BaseRepository):
    def __init__(self):
        super().__init__("sync", "sales_order", "sales_order_number")

    async def get_by_order_number(self, order_number: str) -> list[dict]:
        return await self.execute(
            f"{self.build_select()} where sales_order_number = %s", (order_number,)
        )

    async def get_all_without_details(self) -> list[dict]:
        return await self.execute(
            "select * from sync.vw_sales_order_without_details", None
        )
