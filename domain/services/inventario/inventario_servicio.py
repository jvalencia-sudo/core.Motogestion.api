from typing import Dict, List, Optional

from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from domain.models.inventario.inventario_model import (
    EntradaContract,
    MovimientoItem,
    ProductoStock,
    TomaFisicaContract,
)
from infrastructure.exceptions.domain_exception import DomainException
from repository.inventario.inventario_repositorio import InventarioRepositorio

ROLES_GESTOR = (1, 3)  # Administrador, Recepcionista gestionan inventario


class InventarioServicio:
    def __init__(self):
        self.repo = InventarioRepositorio()

    @staticmethod
    def _exigir_gestor(current: Optional[Dict]) -> str:
        """Solo Admin/Recepcionista pueden mover inventario. Devuelve su documento."""
        if current is None:
            raise DomainException("No autenticado", HTTP_403_FORBIDDEN)
        if current.get("COD_ROL_PRF_USU") not in ROLES_GESTOR:
            raise DomainException("Sin permisos para gestionar el inventario", HTTP_403_FORBIDDEN)
        return current.get("DOCUMENTO_USU")

    async def listar_movimientos(self, cod_pro: Optional[int]) -> List[MovimientoItem]:
        filas = await self.repo.listar_movimientos(cod_pro)
        return [self._map(f) for f in filas]

    async def listar_productos(self) -> List[ProductoStock]:
        filas = await self.repo.listar_productos()
        return [
            ProductoStock(
                cod_pro=f.get("COD_PRO"),
                nombre=f.get("NOMBRE_PRO"),
                stock=int(f.get("STOCK_PRO") or 0),
                stock_min=f.get("STOCK_PRO_MIN"),
            )
            for f in filas
        ]

    async def entrada(self, current: Optional[Dict], contract: EntradaContract) -> Dict:
        documento = self._exigir_gestor(current)
        stock = await self.repo.get_stock(contract.cod_pro)
        if stock is None:
            raise DomainException("Producto no encontrado", HTTP_404_NOT_FOUND)
        nuevo = stock + contract.cantidad
        await self.repo.aplicar_movimiento(
            contract.cod_pro, "ENTRADA", contract.cantidad, stock, nuevo,
            contract.motivo or "Reabastecimiento", documento,
        )
        return {"cod_pro": contract.cod_pro, "stock_nuevo": nuevo}

    async def toma_fisica(self, current: Optional[Dict], contract: TomaFisicaContract) -> Dict:
        documento = self._exigir_gestor(current)
        motivo = contract.motivo or "Toma física"
        ajustados = 0
        for item in contract.items:
            stock = await self.repo.get_stock(item.cod_pro)
            if stock is None or item.cantidad_fisica == stock:
                continue
            diff = item.cantidad_fisica - stock
            await self.repo.aplicar_movimiento(
                item.cod_pro, "AJUSTE", diff, stock, item.cantidad_fisica, motivo, documento,
            )
            ajustados += 1
        return {"ajustados": ajustados}

    @staticmethod
    def _map(f: Dict) -> MovimientoItem:
        return MovimientoItem(
            cod_mov=f.get("COD_MOV"),
            cod_pro=f.get("COD_PRO_MOV"),
            nombre_pro=f.get("NOMBRE_PRO"),
            tipo=f.get("TIPO_MOV"),
            cantidad=f.get("CANTIDAD_MOV"),
            stock_ant=f.get("STOCK_ANT_MOV"),
            stock_nue=f.get("STOCK_NUE_MOV"),
            motivo=f.get("MOTIVO_MOV"),
            documento_usu=f.get("DOCUMENTO_USU_MOV"),
            fecha=f.get("FECHA_MOV"),
            referencia=f.get("REFERENCIA_MOV"),
        )
