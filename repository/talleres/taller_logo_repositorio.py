from typing import Dict, Optional

from repository.data.database import Database


class TallerLogoRepositorio:
    """F1-09: logo del taller, en tabla aparte de `talleres` (ver
    011_personalizacion_pdf.sql). Sin RLS: mismo criterio que `talleres`."""

    def __init__(self):
        self.db = Database()

    async def obtener(self, cod_taller: int) -> Optional[Dict]:
        return await self.db.get_first(
            "SELECT logo, content_type FROM taller_logo WHERE cod_taller = :1",
            (cod_taller,),
        )

    async def existe(self, cod_taller: int) -> bool:
        row = await self.db.get_first(
            "SELECT 1 FROM taller_logo WHERE cod_taller = :1", (cod_taller,)
        )
        return row is not None

    async def guardar(self, cod_taller: int, contenido: bytes, content_type: str) -> None:
        """Upsert: un taller tiene a lo sumo un logo."""
        await self.db.execute_non_query(
            "INSERT INTO taller_logo (cod_taller, logo, content_type, actualizado_en) "
            "VALUES (:1, :2, :3, now()) "
            "ON CONFLICT (cod_taller) DO UPDATE SET logo = :4, content_type = :5, actualizado_en = now()",
            (cod_taller, contenido, content_type, contenido, content_type),
        )
