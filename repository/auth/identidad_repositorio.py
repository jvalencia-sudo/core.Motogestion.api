from typing import Dict, Optional

from repository.base_repository import BaseRepository


class IdentidadRepositorio(BaseRepository):
    """Tabla `usuarios_identidad` (SIN RLS): resuelve el taller/documento del usuario
    a partir del sub de Auth0 o del correo, ANTES de fijar app.tenant_id (la tabla
    `usuarios` sí tiene RLS). Es una tabla propia; se sincroniza desde `usuarios` por
    trigger, así que aquí solo se LEE."""

    def __init__(self):
        super().__init__(
            schema="",
            table_name="usuarios_identidad",
            primary_key="documento_usu",
            omit_key=False,
        )

    async def get_taller_by_sub(self, sub: str) -> Optional[int]:
        row = await self.get_one(
            "SELECT cod_taller FROM usuarios_identidad WHERE sub_id_usu = :1", (sub,)
        )
        return row.get("COD_TALLER") if row else None

    async def get_acceso_por_correo(self, correo: str) -> Optional[Dict]:
        """Identifica al usuario por CORREO (clave estable entre login con Google y
        con usuario/contraseña, que tienen sub distinto). Devuelve taller y documento
        para vincular/actualizar el sub de la sesión actual."""
        return await self.get_one(
            "SELECT cod_taller, documento_usu FROM usuarios_identidad "
            "WHERE lower(correo_usu) = lower(:1) LIMIT 1",
            (correo,),
        )
