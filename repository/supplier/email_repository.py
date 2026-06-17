from typing import List, Dict

from repository.base_repository import BaseRepository


class EmailRepository(BaseRepository):
    def __init__(self):
        super().__init__("supplier", "email", "email_id")

    async def get_by_supplier(self, supplier_id: int) -> List[Dict]:
        return await self.execute(
            f"SELECT * FROM {self.table_name} WHERE supplier_id = %s",
            (supplier_id,),
        )

    async def get_emails_by_status(self, status: bool) -> List[Dict]:
        return await self.execute(
            f"SELECT * FROM {self.table_name} WHERE status = %s",
            (status,),
        )
