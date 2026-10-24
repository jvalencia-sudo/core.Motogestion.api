from typing import Dict, Optional

from repository.data.db_pool import get_pool


class OrdenTrabajoPublicaRepositorio:
    """F2-01: único punto del sistema que fija app.public_order_token (ver la
    policy de ordenes_trabajo en db/migrations/013_link_estado_publico.sql).

    Abre su propia conexión -- no pasa por Database/_apply_tenant -- porque
    este GUC NO debe fijarse en ninguna otra query de la app; solo esta
    consulta puntual lo necesita para resolver "¿de qué taller es este
    token?" sin tener sesión."""

    async def resolver_token(self, token: str) -> Optional[Dict]:
        """Si el token no existe (o no es un UUID válido), devuelve None --
        0 filas, nunca un error: mismo criterio de aislamiento seguro por
        defecto que usa el resto del RLS."""
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                try:
                    # app.tenant_id también se fija a mano (como "-1", igual que
                    # _apply_tenant cuando no hay sesión): esta conexión viene del
                    # mismo pool que usa Database, así que puede llegar con el
                    # tenant_id de un request anterior pegado -- o, una vez que
                    # cualquier transacción tocó ese GUC, con '' (ver la nota de
                    # NULLIF en la policy). Sin esto, la policy intentaría castear
                    # ese valor viejo a integer y la búsqueda del token fallaría
                    # (o reventaría) por una razón que no tiene nada que ver con
                    # el token en sí.
                    await cursor.execute("SELECT set_config('app.tenant_id', '-1', true)")
                    await cursor.execute(
                        "SELECT set_config('app.public_order_token', %s, true)", (token,)
                    )
                    await cursor.execute(
                        "SELECT cod_taller, consecutivo_ot FROM ordenes_trabajo "
                        "WHERE token_publico = %s",
                        (token,),
                    )
                except Exception:
                    # Token con formato inválido (no castea a uuid) -> no existe.
                    await conn.rollback()
                    return None
                fila = await cursor.fetchone()
                await conn.commit()
                if not fila:
                    return None
                return {"COD_TALLER": fila[0], "CONSECUTIVO_OT": fila[1]}
