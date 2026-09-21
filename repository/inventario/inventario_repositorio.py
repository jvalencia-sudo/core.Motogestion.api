from typing import Dict, List, Optional, Union
from decimal import Decimal

from repository.base_repository import BaseRepository

Cantidad = Union[int, Decimal]


class InventarioRepositorio(BaseRepository):
    """Kardex de inventario: SOLO la tabla movimientos_inventario. El stock de los
    productos lo maneja ProductoRepositorio (orquestado por InventarioServicio)."""

    def __init__(self):
        super().__init__(
            schema="",
            table_name="movimientos_inventario",
            primary_key="cod_mov",
            omit_key=True,
        )

    async def listar_movimientos(self, cod_pro: Optional[int]) -> List[Dict]:
        """Kardex (lee de la vista de dominio, que ya trae el nombre del producto)."""
        base = "SELECT * FROM vw_movimientos_inventario "
        orden = " ORDER BY fecha_mov DESC, cod_mov DESC"
        if cod_pro:
            return await self.execute(base + "WHERE cod_pro_mov = :1" + orden, (cod_pro,))
        return await self.execute(base + orden, None)

    async def insertar_movimiento(
        self,
        cod_pro: int,
        tipo: str,
        cantidad: Cantidad,
        stock_ant: Optional[int],
        stock_nue: Optional[int],
        motivo: Optional[str],
        documento_usu: Optional[str],
    ) -> None:
        """Registra un movimiento en el kardex. NO toca el stock del producto (eso es
        responsabilidad de ProductoRepositorio)."""
        await self.execute_non_query(
            "INSERT INTO movimientos_inventario "
            "(cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov, "
            " motivo_mov, documento_usu_mov) "
            "VALUES (:1, :2, :3, :4, :5, :6, :7)",
            (cod_pro, tipo, cantidad, stock_ant, stock_nue, motivo, documento_usu),
        )
