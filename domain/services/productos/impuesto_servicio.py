from typing import Dict, List

from domain.contracts.productos.producto_contract import ImpuestoResponseContract
from domain.models.productos.impuesto_modelo import ImpuestoModelo
from domain.services.base_service import BaseService
from repository.productos.impuesto_repositorio import ImpuestoRepositorio


class ImpuestoServicio(BaseService[ImpuestoModelo, ImpuestoRepositorio]):
    def __init__(self):
        super().__init__(ImpuestoRepositorio())

    def __parse__(self, record: Dict) -> ImpuestoModelo:
        return ImpuestoModelo.model_validate(record)

    async def listar(self) -> List[ImpuestoResponseContract]:
        """Catálogo de impuestos del taller (para el front, en vez de hardcodearlos)."""
        filas = await self.repository.listar()
        return [
            ImpuestoResponseContract(
                cod_imp=f.get("COD_IMP"),
                nombre_imp=f.get("NOMBRE_IMP"),
                porcentaje=f.get("PORCENTAJE_IMP"),
            )
            for f in filas
        ]
