from typing import Dict, List

from domain.models.productos.producto_impuesto_modelo import ProductoImpuestoModelo
from domain.models.productos.vw_producto_impuesto_modelo import VwProductoImpuestoModelo
from domain.services.base_service import BaseService
from repository.productos.producto_impuesto_repositorio import ProductoImpuestoRepositorio


class ProductoImpuestoServicio(BaseService[ProductoImpuestoModelo, ProductoImpuestoRepositorio]):
    def __init__(self):
        super().__init__(ProductoImpuestoRepositorio())

    def __parse__(self, record: Dict) -> ProductoImpuestoModelo:
        return ProductoImpuestoModelo.model_validate(record)

    async def obtener_impuestos_por_producto(self, cod_pro: int) -> List[VwProductoImpuestoModelo]:
        """Obtiene todos los impuestos asociados a un producto usando la vista"""
        registros = await self.repository.obtener_impuestos_por_producto(cod_pro)
        return self.__parse_all_custom__(registros, VwProductoImpuestoModelo)

    async def eliminar_impuestos_producto(self, cod_pro: int) -> None:
        """Elimina todos los impuestos asociados a un producto"""
        await self.repository.eliminar_impuestos_producto(cod_pro)

    async def existe_impuesto_en_producto(self, cod_pro: int, cod_imp: int) -> bool:
        """Verifica si un impuesto ya está asociado a un producto"""
        return await self.repository.existe_impuesto_en_producto(cod_pro, cod_imp)

    async def actualizar_porcentaje_impuesto(self, cod_pro: int, cod_imp: int, porcentaje: float) -> None:
        """Actualiza el porcentaje de un impuesto en un producto"""
        await self.repository.actualizar_porcentaje_impuesto(cod_pro, cod_imp, porcentaje)
