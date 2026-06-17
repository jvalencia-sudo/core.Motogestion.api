from typing import Dict, List, Optional
from repository.base_repository import BaseRepository


class ClienteRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="clientes",
            primary_key="documento_cli",
            omit_key=False  # documento es PK pero no es GENERATED
        )

    async def existe_cliente(self, documento_cli: str) -> bool:
        """Verifica si existe cliente por documento"""
        query = "SELECT COUNT(*) as count FROM clientes WHERE documento_cli = :1"
        result = await self.get_one(query, (documento_cli,))
        return result.get('COUNT', 0) > 0 if result else False

    async def existe_correo(self, correo_cli: str, documento_actual: Optional[str] = None) -> bool:
        """Verifica si existe otro cliente con ese email"""
        if documento_actual:
            query = "SELECT COUNT(*) as count FROM clientes WHERE correo_cli = :1 AND documento_cli != :2"
            result = await self.get_one(query, (correo_cli, documento_actual))
        else:
            query = "SELECT COUNT(*) as count FROM clientes WHERE correo_cli = :1"
            result = await self.get_one(query, (correo_cli,))

        return result.get('COUNT', 0) > 0 if result else False

    async def obtener_clientes(self) -> List[Dict]:
        """Obtiene todos los clientes (vw_clientes)"""
        query = "SELECT * FROM vw_clientes ORDER BY nombre_cli"
        return await self.execute(query, None)

    async def obtener_clientes_resumen(self) -> List[Dict]:
        """Obtiene clientes con total de motos (vw_clientes_resumen)"""
        query = "SELECT * FROM vw_clientes_resumen ORDER BY nombre_completo"
        return await self.execute(query, None)

    async def obtener_cliente_resumen_por_documento(self, documento_cli: str) -> Optional[Dict]:
        """Obtiene un cliente por documento desde la vista vw_clientes_resumen"""
        query = "SELECT * FROM vw_clientes_resumen WHERE documento_cli = :1"
        return await self.get_one(query, (documento_cli,))
