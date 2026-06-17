from typing import List, Dict

from repository.base_repository import BaseRepository


class UserBusinessRepository(BaseRepository):
    def __init__(self):
        super().__init__("auth", "user_business", "user_business_id")

    async def get_businesses_by_user_id(self, user_id: int) -> List[Dict]:
        return await self.execute_query(
            "select ub.*, b.business_name, b.code from auth.user_business ub "
            "join core.business b on b.business_id = ub.business_id "
            "where ub.user_id = %s",
            (user_id,),
        )

    async def get_users_by_business_id(self, business_id: int) -> List[Dict]:
        return await self.execute_query(
            "select ub.*, u.user_name, u.email from auth.user_business ub "
            "join auth.user u on u.user_id = ub.user_id "
            "where ub.business_id = %s",
            (business_id,),
        )

    async def add_user_to_business(self, user_id: int, business_id: int) -> None:
        await self.execute_non_query(
            "insert into auth.user_business (user_id, business_id, created_at) values (%s, %s, NOW())",
            (user_id, business_id),
        )

    async def remove_user_from_business(self, user_id: int, business_id: int) -> None:
        await self.execute_non_query(
            "delete from auth.user_business where user_id = %s and business_id = %s",
            (user_id, business_id),
        )
