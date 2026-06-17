from typing import Dict, Optional
from repository.base_repository import BaseRepository


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__("auth", "USUARIOS", "documento_usu",omit_key=False)

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        # Cambiar %s por :1 (Oracle placeholder)
        # Agregar comillas dobles porque USER es palabra reservada en Oracle
        return await self.get_one(f'select * from {self.table_name} where email = :1', (email,))

    async def get_user_by_sub(self, sub: str) -> Optional[Dict]:
        # Cambiar %s por :1 (Oracle placeholder)

        return await self.get_one(f'select * from {self.table_name} where sub_id_usu = :1', (sub,))

    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        # Cambiar %s por :1 (Oracle placeholder)
        return await self.get_one(f'select * from {self.table_name} where documento_usu = :1', (user_id,))
