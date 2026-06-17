from typing import Dict, List, Optional
from repository.base_repository import BaseRepository


class ReclamoRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="reclamos",
            primary_key="cod_rec",
            omit_key=True,  # cod_rec se genera con secuencia
            sequence_name="seq_reclamos"  # Usar la secuencia existente
        )

    async def obtener_reclamos_completos(self) -> List[Dict]:
        """Obtiene todos los reclamos con información completa usando vista"""
        query = "SELECT * FROM vw_reclamos_completo ORDER BY cod_rec DESC"
        return await self.execute(query, None)

    async def obtener_reclamo_por_id(self, cod_rec: int) -> Optional[Dict]:
        """Obtiene un reclamo por su código usando vista"""
        query = "SELECT * FROM vw_reclamos_completo WHERE cod_rec = :1"
        return await self.get_one(query, (cod_rec,))

    async def obtener_reclamos_por_orden(self, consecutivo_ot: int) -> List[Dict]:
        """Obtiene todos los reclamos asociados a una orden de trabajo"""
        query = """
            SELECT * FROM vw_reclamos_completo
            WHERE consecutivo_ot_rec = :1
            ORDER BY cod_rec DESC
        """
        return await self.execute(query, (consecutivo_ot,))

    async def obtener_reclamos_por_cliente(self, documento_cli: str) -> List[Dict]:
        """Obtiene todos los reclamos de un cliente específico"""
        query = """
            SELECT * FROM vw_reclamos_completo
            WHERE documento_cli = :1
            ORDER BY cod_rec DESC
        """
        return await self.execute(query, (documento_cli,))

    async def obtener_reclamos_por_moto(self, placa_mot: str) -> List[Dict]:
        """Obtiene todos los reclamos de una moto específica"""
        query = """
            SELECT * FROM vw_reclamos_completo
            WHERE placa_mot = :1
            ORDER BY cod_rec DESC
        """
        return await self.execute(query, (placa_mot,))

    async def obtener_reclamos_por_estado_garantia(self, estado_garantia: str) -> List[Dict]:
        """Obtiene reclamos filtrados por estado de garantía (VIGENTE, VENCIDA, SIN INFORMACIÓN)"""
        query = """
            SELECT * FROM vw_reclamos_completo
            WHERE estado_garantia = :1
            ORDER BY cod_rec DESC
        """
        return await self.execute(query, (estado_garantia,))

    async def existe_reclamo(self, cod_rec: int) -> bool:
        """Verifica si existe un reclamo"""
        query = "SELECT COUNT(*) AS count FROM reclamos WHERE cod_rec = :1"
        result = await self.get_one(query, (cod_rec,))
        return result and result.get('COUNT', 0) > 0

    async def existe_reclamo_para_orden(self, consecutivo_ot: int) -> bool:
        """Verifica si existe al menos un reclamo para una orden de trabajo"""
        query = "SELECT COUNT(*) AS count FROM reclamos WHERE consecutivo_ot_rec = :1"
        result = await self.get_one(query, (consecutivo_ot,))
        return result and result.get('COUNT', 0) > 0

    async def actualizar_descripcion(self, cod_rec: int, descripcion: str) -> bool:
        """Actualiza la descripción de un reclamo"""
        query = """
            UPDATE reclamos
            SET descripcion_rec = :1
            WHERE cod_rec = :2
        """
        await self.execute_non_query(query, (descripcion, cod_rec))
        return True
