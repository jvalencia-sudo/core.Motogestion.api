from typing import Dict

from domain.models.productos.impuesto_modelo import ImpuestoModelo
from domain.services.base_service import BaseService
from repository.productos.impuesto_repositorio import ImpuestoRepositorio


class ImpuestoServicio(BaseService[ImpuestoModelo, ImpuestoRepositorio]):
    def __init__(self):
        super().__init__(ImpuestoRepositorio())

    def __parse__(self, record: Dict) -> ImpuestoModelo:
        return ImpuestoModelo.model_validate(record)
