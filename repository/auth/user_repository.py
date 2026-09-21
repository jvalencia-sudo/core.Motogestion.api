from typing import Dict, Optional
from repository.base_repository import BaseRepository


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__("auth", "USUARIOS", "documento_usu",omit_key=False)

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        return await self.get_one(f'select * from {self.table_name} where email = :1', (email,))

    async def get_user_by_sub(self, sub: str) -> Optional[Dict]:
        return await self.get_one(f'select * from {self.table_name} where sub_id_usu = :1', (sub,))

    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        # documento_usu es VARCHAR: el parámetro debe ir como texto (Postgres no
        # castea implícitamente varchar = bigint en el WHERE).
        return await self.get_one(f'select * from {self.table_name} where documento_usu = :1', (str(user_id),))

    async def crear_pre_registrado(self, documento: str, nombre: str, apellido: str,
                                   correo: str, cod_prf: int, cod_rol: int) -> None:
        # Usuario PRE-REGISTRADO en el taller actual (cod_taller lo pone el DEFAULT
        # = app.tenant_id). sub NULL hasta su primer login.
        await self.execute_non_query(
            "INSERT INTO usuarios "
            "(documento_usu, nombre_usu, apellido_1_usu, correo_usu, contrasena_usu, "
            " cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu) "
            "VALUES (:1, :2, :3, :4, 'auth0_managed', 1, 1, NULL, :5, :6)",
            (documento, nombre, apellido, correo, cod_prf, cod_rol),
        )

    async def vincular_sub(self, documento_usu: str, sub: str) -> None:
        # Vincula el sub de Auth0 al usuario pre-registrado (RLS acota al taller actual).
        await self.execute_non_query(
            'update usuarios set sub_id_usu = :1 where documento_usu = :2',
            (sub, documento_usu)
        )
