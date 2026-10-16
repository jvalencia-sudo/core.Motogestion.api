from typing import Dict, List

from repository.base_repository import BaseRepository


class NotaRepositorio(BaseRepository):
    """Tabla `notas_taller` (SIN RLS -- dato del super-admin sobre el taller, no
    dato del tenant; ver infrastructure/utils/rls_policy.py)."""

    def __init__(self):
        super().__init__(schema="", table_name="notas_taller", primary_key="id", omit_key=True)

    async def crear(self, cod_taller: int, autor: str, texto: str) -> int:
        res = await self.db.insert(
            "INSERT INTO notas_taller (cod_taller, autor, texto) VALUES (:1, :2, :3)",
            (cod_taller, autor, texto),
            primary_key="id",
        )
        return res["id"]

    async def listar_por_taller(self, cod_taller: int) -> List[Dict]:
        return await self.db.execute(
            "SELECT id, autor, to_char(fecha, 'YYYY-MM-DD HH24:MI') AS fecha, texto "
            "FROM notas_taller WHERE cod_taller = :1 ORDER BY fecha DESC",
            (cod_taller,),
        )
