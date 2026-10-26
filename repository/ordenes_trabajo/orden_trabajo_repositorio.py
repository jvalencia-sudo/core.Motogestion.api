from typing import Dict, List, Optional
from repository.base_repository import BaseRepository


class OrdenTrabajoRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="ordenes_trabajo",
            primary_key="consecutivo_ot",
            omit_key=True  # consecutivo_ot se genera con trigger tg_gen_consecutivo_ot (MAX+1)
        )

    async def obtener_ordenes_completas(self) -> List[Dict]:
        """Obtiene todas las ordenes de trabajo con informacion completa usando vista"""
        query = "SELECT * FROM vw_ordenes_trabajo_completa ORDER BY consecutivo_ot DESC"
        return await self.execute(query, None)

    async def obtener_orden_por_id(self, consecutivo_ot: int) -> Optional[Dict]:
        """Obtiene una orden de trabajo por su consecutivo usando vista"""
        query = "SELECT * FROM vw_ordenes_trabajo_completa WHERE consecutivo_ot = :1"
        return await self.get_one(query, (consecutivo_ot,))

    async def obtener_ordenes_pendientes(self) -> List[Dict]:
        """Obtiene todas las ordenes pendientes de entrega usando vista"""
        query = "SELECT * FROM vw_ot_pendientes ORDER BY dias_pendiente DESC"
        return await self.execute(query, None)

    async def obtener_ordenes_por_cliente(self, documento_cli: str) -> List[Dict]:
        """Obtiene todas las ordenes de un cliente especifico"""
        query = """
            SELECT * FROM vw_ordenes_trabajo_completa
            WHERE documento_cli = :1
            ORDER BY consecutivo_ot DESC
        """
        return await self.execute(query, (documento_cli,))

    async def obtener_ordenes_por_moto(self, placa_mot: str) -> List[Dict]:
        """Obtiene todas las ordenes de una moto especifica"""
        query = """
            SELECT * FROM vw_ordenes_trabajo_completa
            WHERE placa_mot = :1
            ORDER BY consecutivo_ot DESC
        """
        return await self.execute(query, (placa_mot,))

    async def obtener_resumen_financiero(self, consecutivo_ot: int) -> Optional[Dict]:
        """Obtiene el resumen financiero de una orden usando vista"""
        query = "SELECT * FROM vw_resumen_financiero_ot WHERE consecutivo_ot = :1"
        return await self.get_one(query, (consecutivo_ot,))

    async def regenerar_token_publico(self, consecutivo_ot: int) -> Optional[str]:
        """F2-01: genera un token nuevo para el link público de estado --
        invalida el anterior de inmediato (deja de existir ninguna fila con
        ese UUID viejo). Corre bajo el RLS normal (sesión real, sin ningún
        bypass): solo puede regenerar el token de una orden del propio
        taller.

        Usa self.db.insert() (no get_one/execute) porque es el único método
        de Database que hace commit tras un UPDATE ... RETURNING -- get_one()
        es de solo lectura (ver el comentario de actualizar_estado más
        arriba)."""
        query = "UPDATE ordenes_trabajo SET token_publico = gen_random_uuid() WHERE consecutivo_ot = :1"
        resultado = await self.db.insert(query, (consecutivo_ot,), primary_key="token_publico")
        token = resultado.get("token_publico") if resultado else None
        return str(token) if token else None

    async def obtener_historial_estados(self, consecutivo_ot: int) -> List[Dict]:
        """F2-02: hitos reales (con hora) por los que pasó la orden. Vacío
        para órdenes de antes de la migración 015 -- el frontend cae al
        comportamiento anterior en ese caso."""
        query = """
            SELECT consecutivo_ot, cod_ot_est_ot, ocurrido_en
            FROM orden_estado_historial
            WHERE consecutivo_ot = :1
            ORDER BY ocurrido_en ASC
        """
        return await self.execute(query, (consecutivo_ot,))

    async def guardar_diagnostico(self, consecutivo_ot: int, texto: str) -> None:
        """F2-02: diagnóstico que ve el cliente final (separado de
        observacion_ot, que es interno)."""
        await self.update_field(consecutivo_ot, 'diagnostico_ot', texto)

    async def actualizar_estado(self, consecutivo_ot: int, cod_estado: int) -> None:
        """Actualiza el estado de una orden de trabajo"""
        await self.update_field(consecutivo_ot, 'cod_ot_est_ot', cod_estado)

    async def registrar_entrega(
        self,
        consecutivo_ot: int,
        fecha_entrega,
        km_salida: Optional[int],
    ) -> bool:
        """Registra la entrega de una orden de trabajo. fecha_fin_garantia_ot
        no se fija acá -- F1-04: el trigger fn_calc_fecha_garantia la calcula
        a partir del MAX(dias_garantia_pro) de los ítems de la orden en cuanto
        este UPDATE deja cod_ot_est_ot = 4."""
        query = """
            UPDATE ordenes_trabajo
            SET fecha_entrega_ot = :1,
                kilometraje_salida_ot = :2,
                cod_ot_est_ot = 4
            WHERE consecutivo_ot = :3
        """
        # Mismo motivo que actualizar_estado: UPDATE sin RETURNING necesita
        # execute_non_query (execute() es solo para SELECT y no confirma).
        await self.execute_non_query(query, (fecha_entrega, km_salida, consecutivo_ot))
        return True

    @staticmethod
    def statement_anular(consecutivo_ot: int, motivo: str, documento_usu: str):
        """F1-05: parte de una transacción más grande (junto con la devolución
        de stock) -- no ejecuta nada por sí sola, ver OrdenTrabajoServicio.anular_orden."""
        return (
            "UPDATE ordenes_trabajo SET cod_ot_est_ot = 5, motivo_anulacion_ot = :1, "
            "fecha_anulacion_ot = now(), documento_usu_anulacion_ot = :2 "
            "WHERE consecutivo_ot = :3",
            (motivo, documento_usu, consecutivo_ot),
        )

    async def existe_orden(self, consecutivo_ot: int) -> bool:
        """Verifica si existe una orden de trabajo"""
        return await self.exists('consecutivo_ot', consecutivo_ot)

    async def actualizar_campos(self, consecutivo_ot: int, campos: dict) -> bool:
        """Actualiza campos específicos de una orden de trabajo"""
        # Construir SET clause dinámicamente
        set_clauses = []
        params = []

        for campo, valor in campos.items():
            if campo != 'CONSECUTIVO_OT':  # Excluir primary key
                set_clauses.append(f"{campo} = :{len(params) + 1}")
                params.append(valor)

        if not set_clauses:
            return True

        # Agregar consecutivo_ot al final de params
        params.append(consecutivo_ot)

        query = f"""
            UPDATE ordenes_trabajo
            SET {', '.join(set_clauses)}
            WHERE consecutivo_ot = :{len(params)}
        """

        await self.execute_non_query(query, tuple(params))
        return True

    async def obtener_orden_anterior(self, placa_mot: str, consecutivo_ot: int) -> Optional[Dict]:
        """Obtiene la orden anterior entregada de una moto (excluyendo la orden actual)"""
        query = """
            SELECT fecha_fin_garantia_ot, fecha_entrega_ot
            FROM ordenes_trabajo
            WHERE placa_mot_ot = :1
              AND consecutivo_ot != :2
              AND fecha_entrega_ot IS NOT NULL
            ORDER BY fecha_entrega_ot DESC
            FETCH FIRST 1 ROW ONLY
        """
        return await self.get_one(query, (placa_mot, consecutivo_ot))
