from typing import Dict, List, Optional
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from domain.models.ordenes_trabajo.reclamo_modelo import ReclamoModelo, VwReclamosCompleto
from infrastructure.commons.enums.warranty_status import WarrantyStatusEnum
from domain.contracts.ordenes_trabajo.reclamo_contract import (
    ReclamoCreateContract,
    ReclamoUpdateContract,
    ReclamoResponseContract,
    ReclamoResumenContract
)
from domain.services.base_service import BaseService
from repository.ordenes_trabajo.reclamo_repositorio import ReclamoRepositorio
from repository.ordenes_trabajo.orden_trabajo_repositorio import OrdenTrabajoRepositorio
from infrastructure.exceptions.domain_exception import DomainException


class ReclamoServicio(BaseService[ReclamoModelo, ReclamoRepositorio]):
    def __init__(self):
        super().__init__(ReclamoRepositorio())
        self.orden_trabajo_repository = OrdenTrabajoRepositorio()

    def __parse__(self, record: Dict) -> ReclamoModelo:
        return ReclamoModelo.model_validate(record)

    async def obtener_todos_reclamos(self) -> List[ReclamoResumenContract]:
        """Obtiene todos los reclamos con información resumida"""
        reclamos_dict = await self.repository.obtener_reclamos_completos()
        reclamos_modelos = self.__parse_all_custom__(reclamos_dict, VwReclamosCompleto)

        resultado = []
        for reclamo in reclamos_modelos:
            resultado.append(ReclamoResumenContract(
                cod_rec=reclamo.cod_rec,
                descripcion_rec=reclamo.descripcion_rec,
                consecutivo_ot_rec=reclamo.consecutivo_ot_rec,
                placa_mot=reclamo.placa_mot,
                nombre_completo_cliente=reclamo.nombre_completo_cliente,
                telefono_cli=reclamo.telefono_cli,
                estado_ot=reclamo.estado_ot,
                fecha_elaboracion_ot=reclamo.fecha_elaboracion_ot,
                estado_garantia=reclamo.estado_garantia
            ))

        return resultado

    async def obtener_reclamo_por_id(self, cod_rec: int) -> ReclamoResponseContract:
        """Obtiene un reclamo completo con todos sus detalles"""
        reclamo_dict = await self.repository.obtener_reclamo_por_id(cod_rec)

        if not reclamo_dict:
            raise DomainException(
                f"Reclamo con código {cod_rec} no encontrado",
                HTTP_404_NOT_FOUND
            )

        # Mapear a modelo Pydantic usando tipado estático
        reclamo_modelo = self.__parse_custom__(reclamo_dict, VwReclamosCompleto)

        return ReclamoResponseContract(
            cod_rec=reclamo_modelo.cod_rec,
            descripcion_rec=reclamo_modelo.descripcion_rec,
            consecutivo_ot_rec=reclamo_modelo.consecutivo_ot_rec,
            fecha_elaboracion_ot=reclamo_modelo.fecha_elaboracion_ot,
            fecha_entrega_ot=reclamo_modelo.fecha_entrega_ot,
            kilometraje_ingreso_ot=reclamo_modelo.kilometraje_ingreso_ot,
            observacion_cli_ot=reclamo_modelo.observacion_cli_ot,
            observacion_ot=reclamo_modelo.observacion_ot,
            fecha_fin_garantia_ot=reclamo_modelo.fecha_fin_garantia_ot,
            estado_ot=reclamo_modelo.estado_ot,
            placa_mot=reclamo_modelo.placa_mot,
            modelo_mot=reclamo_modelo.modelo_mot,
            color_mot=reclamo_modelo.color_mot,
            cilindraje_mot=reclamo_modelo.cilindraje_mot,
            marca_moto=reclamo_modelo.marca_moto,
            moto_completa=reclamo_modelo.moto_completa,
            documento_cli=reclamo_modelo.documento_cli,
            nombre_completo_cliente=reclamo_modelo.nombre_completo_cliente,
            telefono_cli=reclamo_modelo.telefono_cli,
            correo_cli=reclamo_modelo.correo_cli,
            direccion_cli=reclamo_modelo.direccion_cli,
            documento_recepcionista=reclamo_modelo.documento_recepcionista,
            recepcionista=reclamo_modelo.recepcionista,
            documento_mecanico=reclamo_modelo.documento_mecanico,
            mecanico=reclamo_modelo.mecanico,
            estado_garantia=reclamo_modelo.estado_garantia,
            dias_garantia_restantes=reclamo_modelo.dias_garantia_restantes
        )

    async def obtener_reclamos_por_orden(self, consecutivo_ot: int) -> List[ReclamoResumenContract]:
        """Obtiene todos los reclamos asociados a una orden de trabajo"""
        # Validar que la orden existe
        if not await self.orden_trabajo_repository.existe_orden(consecutivo_ot):
            raise DomainException(
                f"Orden de trabajo con consecutivo {consecutivo_ot} no encontrada",
                HTTP_404_NOT_FOUND
            )

        reclamos_dict = await self.repository.obtener_reclamos_por_orden(consecutivo_ot)
        reclamos_modelos = self.__parse_all_custom__(reclamos_dict, VwReclamosCompleto)

        resultado = []
        for reclamo in reclamos_modelos:
            resultado.append(ReclamoResumenContract(
                cod_rec=reclamo.cod_rec,
                descripcion_rec=reclamo.descripcion_rec,
                consecutivo_ot_rec=reclamo.consecutivo_ot_rec,
                placa_mot=reclamo.placa_mot,
                nombre_completo_cliente=reclamo.nombre_completo_cliente,
                telefono_cli=reclamo.telefono_cli,
                estado_ot=reclamo.estado_ot,
                fecha_elaboracion_ot=reclamo.fecha_elaboracion_ot,
                estado_garantia=reclamo.estado_garantia
            ))

        return resultado

    async def obtener_reclamos_por_cliente(self, documento_cli: str) -> List[ReclamoResumenContract]:
        """Obtiene todos los reclamos de un cliente específico"""
        reclamos_dict = await self.repository.obtener_reclamos_por_cliente(documento_cli)
        reclamos_modelos = self.__parse_all_custom__(reclamos_dict, VwReclamosCompleto)

        resultado = []
        for reclamo in reclamos_modelos:
            resultado.append(ReclamoResumenContract(
                cod_rec=reclamo.cod_rec,
                descripcion_rec=reclamo.descripcion_rec,
                consecutivo_ot_rec=reclamo.consecutivo_ot_rec,
                placa_mot=reclamo.placa_mot,
                nombre_completo_cliente=reclamo.nombre_completo_cliente,
                telefono_cli=reclamo.telefono_cli,
                estado_ot=reclamo.estado_ot,
                fecha_elaboracion_ot=reclamo.fecha_elaboracion_ot,
                estado_garantia=reclamo.estado_garantia
            ))

        return resultado

    async def obtener_reclamos_por_moto(self, placa_mot: str) -> List[ReclamoResumenContract]:
        """Obtiene todos los reclamos de una moto específica"""
        reclamos_dict = await self.repository.obtener_reclamos_por_moto(placa_mot)
        reclamos_modelos = self.__parse_all_custom__(reclamos_dict, VwReclamosCompleto)

        resultado = []
        for reclamo in reclamos_modelos:
            resultado.append(ReclamoResumenContract(
                cod_rec=reclamo.cod_rec,
                descripcion_rec=reclamo.descripcion_rec,
                consecutivo_ot_rec=reclamo.consecutivo_ot_rec,
                placa_mot=reclamo.placa_mot,
                nombre_completo_cliente=reclamo.nombre_completo_cliente,
                telefono_cli=reclamo.telefono_cli,
                estado_ot=reclamo.estado_ot,
                fecha_elaboracion_ot=reclamo.fecha_elaboracion_ot,
                estado_garantia=reclamo.estado_garantia
            ))

        return resultado

    async def obtener_reclamos_por_estado_garantia(self, estado_garantia: str) -> List[ReclamoResumenContract]:
        """Obtiene reclamos filtrados por estado de garantía (VIGENTE, VENCIDA, SIN INFORMACIÓN)"""
        # Validar que el estado sea válido usando enum
        try:
            estado_enum = WarrantyStatusEnum(estado_garantia.upper())
            estado_validado = estado_enum.value
        except ValueError:
            estados_validos = [e.value for e in WarrantyStatusEnum]
            raise DomainException(
                f"Estado de garantía inválido. Valores permitidos: {', '.join(estados_validos)}",
                HTTP_400_BAD_REQUEST
            )

        reclamos_dict = await self.repository.obtener_reclamos_por_estado_garantia(estado_validado)
        reclamos_modelos = self.__parse_all_custom__(reclamos_dict, VwReclamosCompleto)

        resultado = []
        for reclamo in reclamos_modelos:
            resultado.append(ReclamoResumenContract(
                cod_rec=reclamo.cod_rec,
                descripcion_rec=reclamo.descripcion_rec,
                consecutivo_ot_rec=reclamo.consecutivo_ot_rec,
                placa_mot=reclamo.placa_mot,
                nombre_completo_cliente=reclamo.nombre_completo_cliente,
                telefono_cli=reclamo.telefono_cli,
                estado_ot=reclamo.estado_ot,
                fecha_elaboracion_ot=reclamo.fecha_elaboracion_ot,
                estado_garantia=reclamo.estado_garantia
            ))

        return resultado

    async def crear_reclamo(self, contract: ReclamoCreateContract) -> ReclamoResponseContract:
        """Crea un nuevo reclamo"""
        # Validar que la orden de trabajo existe
        if not await self.orden_trabajo_repository.existe_orden(contract.consecutivo_ot_rec):
            raise DomainException(
                f"Orden de trabajo con consecutivo {contract.consecutivo_ot_rec} no encontrada",
                HTTP_404_NOT_FOUND
            )

        # Crear el modelo de reclamo
        reclamo_modelo = ReclamoModelo(
            descripcion_rec=contract.descripcion_rec,
            consecutivo_ot_rec=contract.consecutivo_ot_rec
        )

        # Crear el reclamo
        cod_rec = await self.repository.create(reclamo_modelo)

        # Retornar el reclamo creado completo
        return await self.obtener_reclamo_por_id(cod_rec)

    async def actualizar_reclamo(
        self,
        cod_rec: int,
        contract: ReclamoUpdateContract
    ) -> ReclamoResponseContract:
        """Actualiza un reclamo existente"""
        # Verificar que el reclamo existe
        reclamo_actual = await self.repository.obtener_reclamo_por_id(cod_rec)
        if not reclamo_actual:
            raise DomainException(
                f"Reclamo con código {cod_rec} no encontrado",
                HTTP_404_NOT_FOUND
            )

        # Actualizar solo si se proporciona nueva descripción
        if contract.descripcion_rec is not None:
            await self.repository.actualizar_descripcion(cod_rec, contract.descripcion_rec)

        return await self.obtener_reclamo_por_id(cod_rec)

    async def eliminar_reclamo(self, cod_rec: int) -> bool:
        """Elimina un reclamo"""
        # Verificar que el reclamo existe
        if not await self.repository.existe_reclamo(cod_rec):
            raise DomainException(
                f"Reclamo con código {cod_rec} no encontrado",
                HTTP_404_NOT_FOUND
            )

        # Eliminar el reclamo
        await self.repository.delete(cod_rec)
        return True
