from typing import Dict, List, Optional
from repository.base_repository import BaseRepository


class MotoRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="motos",
            primary_key="placa_mot",
            omit_key=False  # placa es PK pero no es GENERATED
        )

    async def existe_moto(self, placa_mot: str) -> bool:
        """Verifica si existe moto"""
        query = "SELECT COUNT(*) as count FROM motos WHERE placa_mot = :1"
        result = await self.get_one(query, (placa_mot,))
        return result.get('COUNT', 0) > 0 if result else False

    async def obtener_motos(self) -> List[Dict]:
        """Obtiene todas las motos (vw_motos)"""
        query = "SELECT * FROM vw_motos ORDER BY placa_mot"
        return await self.execute(query, None)

    async def obtener_motos_marcas(self) -> List[Dict]:
        """Obtiene motos con información de marca (vw_motos_marcas)"""
        query = "SELECT * FROM vw_motos_marcas ORDER BY placa_mot"
        return await self.execute(query, None)

    async def obtener_motos_detalle(self) -> List[Dict]:
        """Obtiene motos con información completa (vw_motos_detalle)"""
        query = "SELECT * FROM vw_motos_detalle ORDER BY placa_mot"
        return await self.execute(query, None)

    async def obtener_motos_por_cliente(self, documento_cli: str) -> List[Dict]:
        """Obtiene motos de un cliente específico (vw_motos_detalle filtrada)"""
        query = "SELECT * FROM vw_motos_detalle WHERE documento_cli = :1 ORDER BY placa_mot"
        return await self.execute(query, (documento_cli,))

    async def obtener_motos_por_marca(self, cod_marca_mot: int) -> List[Dict]:
        """Obtiene motos de una marca específica (vw_motos_marcas filtrada)"""
        query = "SELECT * FROM vw_motos_marcas WHERE cod_marca_mot = :1 ORDER BY placa_mot"
        return await self.execute(query, (cod_marca_mot,))
