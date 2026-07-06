from typing import Dict, List, Optional

from repository.base_repository import BaseRepository


class InventarioRepositorio(BaseRepository):
    """Kardex de inventario + ajustes de stock. Todo acotado por RLS al taller actual."""

    def __init__(self):
        super().__init__(
            schema="",
            table_name="movimientos_inventario",
            primary_key="cod_mov",
            omit_key=True,
        )

    async def listar_movimientos(self, cod_pro: Optional[int]) -> List[Dict]:
        base = (
            "select m.cod_mov, m.cod_pro_mov, p.nombre_pro, m.tipo_mov, m.cantidad_mov, "
            "       m.stock_ant_mov, m.stock_nue_mov, m.motivo_mov, m.documento_usu_mov, "
            "       to_char(m.fecha_mov, 'YYYY-MM-DD HH24:MI') as fecha_mov, m.referencia_mov "
            "from movimientos_inventario m "
            "join productos p on p.cod_pro = m.cod_pro_mov and p.cod_taller = m.cod_taller "
        )
        orden = " order by m.fecha_mov desc, m.cod_mov desc"
        if cod_pro:
            return await self.execute(base + "where m.cod_pro_mov = :1" + orden, (cod_pro,))
        return await self.execute(base + orden, None)

    async def listar_productos(self) -> List[Dict]:
        return await self.execute(
            "select cod_pro, nombre_pro, coalesce(stock_pro, 0) as stock_pro, stock_pro_min "
            "from productos where coalesce(cod_est_pro, 1) = 1 order by nombre_pro",
            None,
        )

    async def get_stock(self, cod_pro: int) -> Optional[int]:
        row = await self.get_one(
            "select stock_pro from productos where cod_pro = :1", (cod_pro,)
        )
        return row.get("STOCK_PRO") if row else None

    async def aplicar_movimiento(
        self,
        cod_pro: int,
        tipo: str,
        cantidad: int,
        stock_ant: int,
        stock_nue: int,
        motivo: Optional[str],
        documento_usu: Optional[str],
    ) -> None:
        """Actualiza el stock del producto y registra el movimiento (entrada/ajuste)."""
        await self.execute_non_query(
            "update productos set stock_pro = :1 where cod_pro = :2", (stock_nue, cod_pro)
        )
        await self.execute_non_query(
            "insert into movimientos_inventario "
            "(cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov, "
            " motivo_mov, documento_usu_mov) "
            "values (:1, :2, :3, :4, :5, :6, :7)",
            (cod_pro, tipo, cantidad, stock_ant, stock_nue, motivo, documento_usu),
        )
