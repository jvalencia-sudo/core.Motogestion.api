from typing import Dict, List
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from domain.contracts.motos.marca_contract import (
    MarcaCreateContract,
    MarcaUpdateContract,
    MarcaResponseContract
)
from domain.models.motos.marca_modelo import MarcaModelo
from domain.models.motos.vw_marca_estadistica_modelo import VwMarcaResumenModelo
from domain.services.base_service import BaseService
from infrastructure.exceptions.domain_exception import DomainException
from repository.marcas.marca_repositorio import MarcaRepositorio


class MarcaServicio(BaseService[MarcaModelo, MarcaRepositorio]):
    def __init__(self):
        super().__init__(MarcaRepositorio())

    def __parse__(self, record: Dict) -> MarcaModelo:
        normalized = self.__normalize_keys__(record)
        return MarcaModelo.model_validate(normalized)

    async def obtener_todas_marcas(self) -> List[MarcaResponseContract]:
        """Obtiene todas las marcas"""
        marcas_dict = await self.repository.get_all()
        marcas_modelos = self.__parse_all__(marcas_dict)
        return [MarcaResponseContract(cod_mar=m.cod_mar, nombre_mar=m.nombre_mar) for m in marcas_modelos]

    async def obtener_marcas_con_resumen(self) -> List[VwMarcaResumenModelo]:
        """Obtiene marcas con total de motos registradas"""
        marcas_dict = await self.repository.obtener_marcas_con_resumen()
        return self.__parse_all_custom__(marcas_dict, VwMarcaResumenModelo)

    async def obtener_marca_por_id(self, cod_mar: int) -> MarcaResponseContract:
        """Obtiene marca por código"""
        if not cod_mar or cod_mar <= 0:
            raise DomainException(
                "Código de marca inválido",
                HTTP_400_BAD_REQUEST
            )

        marca_dict = await self.repository.get_by_id(cod_mar)
        if not marca_dict:
            raise DomainException(
                f"Marca con código {cod_mar} no encontrada",
                HTTP_404_NOT_FOUND
            )

        marca_modelo = self.__parse__(marca_dict)
        return MarcaResponseContract(cod_mar=marca_modelo.cod_mar, nombre_mar=marca_modelo.nombre_mar)

    async def crear_marca(self, contract: MarcaCreateContract) -> MarcaResponseContract:
        """Crea nueva marca"""
        # Validar nombre único
        existe = await self.repository.existe_marca(contract.nombre_mar)
        if existe:
            raise DomainException(
                f"Ya existe una marca con el nombre '{contract.nombre_mar}'",
                HTTP_400_BAD_REQUEST
            )

        modelo = MarcaModelo(nombre_mar=contract.nombre_mar)
        cod_mar = await self.repository.create(modelo)

        return MarcaResponseContract(cod_mar=cod_mar, nombre_mar=contract.nombre_mar)

    async def actualizar_marca(self, cod_mar: int, contract: MarcaUpdateContract) -> MarcaResponseContract:
        """Actualiza marca"""
        # Validar existencia
        marca_dict = await self.repository.get_by_id(cod_mar)
        if not marca_dict:
            raise DomainException(
                f"Marca con código {cod_mar} no encontrada",
                HTTP_404_NOT_FOUND
            )
        marca_modelo = self.__parse__(marca_dict)
        # Validar nombre único (si cambió)
        if contract.nombre_mar and contract.nombre_mar != marca_modelo.nombre_mar:
            existe = await self.repository.existe_marca(contract.nombre_mar, excluir_cod=cod_mar)
            if existe:
                raise DomainException(
                    f"Ya existe una marca con el nombre '{contract.nombre_mar}'",
                    HTTP_400_BAD_REQUEST
                )

        # Actualizar solo los campos que vienen en el contrato
        marca_modelo = self.__parse__(marca_dict)
        marca_modelo.cod_mar = cod_mar

        if contract.nombre_mar:
            marca_modelo.nombre_mar = contract.nombre_mar

        await self.repository.update(marca_modelo)
        return MarcaResponseContract(cod_mar=marca_modelo.cod_mar, nombre_mar=marca_modelo.nombre_mar)
