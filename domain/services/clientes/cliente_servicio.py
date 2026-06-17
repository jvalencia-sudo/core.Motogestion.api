from typing import Dict, List
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from domain.contracts.clientes.cliente_contract import (
    ClienteCreateContract,
    ClienteUpdateContract,
    ClienteResponseContract
)
from domain.models.clientes.cliente_modelo import ClienteModelo
from domain.models.clientes.vw_cliente_completo_modelo import VwClienteModelo, VwClienteResumenModelo
from domain.services.base_service import BaseService
from infrastructure.exceptions.domain_exception import DomainException
from repository.clientes.cliente_repositorio import ClienteRepositorio


class ClienteServicio(BaseService[ClienteModelo, ClienteRepositorio]):
    def __init__(self):
        super().__init__(ClienteRepositorio())

    def __parse__(self, record: Dict) -> ClienteModelo:
        normalized = self.__normalize_keys__(record)
        return ClienteModelo.model_validate(normalized)

    async def obtener_todos_clientes(self) -> List[ClienteResponseContract]:
        """Obtiene todos los clientes con resumen de motos"""
        clientes_dict = await self.repository.obtener_clientes_resumen()
        clientes_modelos = self.__parse_all_custom__(clientes_dict, VwClienteResumenModelo)

        return [ClienteResponseContract(
            documento_cli=c.documento_cli,
            nombre_completo=c.nombre_completo,
            telefono_cli=c.telefono_cli,
            correo_cli=c.correo_cli,
            direccion_cli=c.direccion_cli,
            total_motos=c.total_motos
        ) for c in clientes_modelos]

    async def obtener_cliente_por_documento(self, documento_cli: str) -> ClienteResponseContract:
        """Obtiene cliente por documento"""
        if not documento_cli or len(documento_cli) < 8:
            raise DomainException(
                "Documento de cliente inválido",
                HTTP_400_BAD_REQUEST
            )

        cliente_dict = await self.repository.obtener_cliente_resumen_por_documento(documento_cli)
        if not cliente_dict:
            raise DomainException(
                f"Cliente con documento {documento_cli} no encontrado",
                HTTP_404_NOT_FOUND
            )

        cliente_modelo = self.__parse_custom__(cliente_dict, VwClienteResumenModelo)
        return ClienteResponseContract(
            documento_cli=cliente_modelo.documento_cli,
            nombre_completo=cliente_modelo.nombre_completo,
            telefono_cli=cliente_modelo.telefono_cli,
            correo_cli=cliente_modelo.correo_cli,
            direccion_cli=cliente_modelo.direccion_cli,
            total_motos=cliente_modelo.total_motos
        )

    async def crear_cliente(self, contract: ClienteCreateContract) -> ClienteResponseContract:
        """Crea nuevo cliente"""
        try:
            # Validar documento único
            existe = await self.repository.existe_cliente(contract.documento_cli)
            if existe:
                raise DomainException(
                    f"Cliente con documento {contract.documento_cli} ya existe",
                    HTTP_400_BAD_REQUEST
                )

            # Validar correo único
            existe_correo = await self.repository.existe_correo(contract.correo_cli)
            if existe_correo:
                raise DomainException(
                    f"Ya existe cliente con correo {contract.correo_cli}",
                    HTTP_400_BAD_REQUEST
                )

            modelo = ClienteModelo(**contract.model_dump(exclude_unset=True))
            print(f"DEBUG: Modelo cliente creado: {modelo}")
            print(f"DEBUG: Modelo dump: {modelo.model_dump()}")

            await self.repository.create(modelo)

            nombre_completo = f"{contract.nombre_cli} {contract.apellido_1_cli}"
            if contract.apellido_2_cli:
                nombre_completo += f" {contract.apellido_2_cli}"

            return ClienteResponseContract(
                documento_cli=contract.documento_cli,
                nombre_completo=nombre_completo,
                telefono_cli=contract.telefono_cli,
                correo_cli=contract.correo_cli,
                direccion_cli=contract.direccion_cli,
                total_motos=0
            )
        except DomainException:
            raise
        except Exception as e:
            print(f"Error inesperado en crear_cliente: {e}")
            import traceback
            traceback.print_exc()
            raise DomainException(
                f"Error al crear cliente: {str(e)}",
                HTTP_400_BAD_REQUEST
            )

    async def actualizar_cliente(self, documento_cli: str, contract: ClienteUpdateContract) -> ClienteResponseContract:
        """Actualiza cliente"""
        try:
            # Validar existencia
            cliente_dict = await self.repository.get_by_id(documento_cli)

            if not cliente_dict:
                raise DomainException(
                    f"Cliente con documento {documento_cli} no encontrado",
                    HTTP_404_NOT_FOUND
                )
            cliente_modelo = self.__parse__(cliente_dict)
            # Validar correo único (si cambió)
            if contract.correo_cli and contract.correo_cli != cliente_modelo.correo_cli:
                existe_correo = await self.repository.existe_correo(contract.correo_cli, documento_actual=documento_cli)
                if existe_correo:
                    raise DomainException(
                        f"Ya existe otro cliente con correo {contract.correo_cli}",
                        HTTP_400_BAD_REQUEST
                    )

            # Actualizar cliente
            cliente_modelo = self.__parse__(cliente_dict)

            # Actualizar solo los campos que vienen en el contrato
            update_data = contract.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if value is not None:
                    setattr(cliente_modelo, key, value)

            await self.repository.update(cliente_modelo)

            # Obtener datos actualizados desde la vista
            cliente_actualizado = await self.repository.obtener_cliente_resumen_por_documento(documento_cli)
            cliente_modelo = self.__parse_custom__(cliente_actualizado, VwClienteResumenModelo)

            return ClienteResponseContract(
                documento_cli=cliente_modelo.documento_cli,
                nombre_completo=cliente_modelo.nombre_completo,
                telefono_cli=cliente_modelo.telefono_cli,
                correo_cli=cliente_modelo.correo_cli,
                direccion_cli=cliente_modelo.direccion_cli,
                total_motos=cliente_modelo.total_motos
            )
        except DomainException:
            raise
        except Exception as e:
            print(f"Error inesperado en actualizar_cliente: {e}")
            import traceback
            traceback.print_exc()
            raise DomainException(
                f"Error al actualizar cliente: {str(e)}",
                HTTP_400_BAD_REQUEST
            )

    async def eliminar_cliente(self, documento_cli: str) -> bool:
        """Elimina cliente"""
        try:
            cliente_dict = await self.repository.get_by_id(documento_cli)
            if not cliente_dict:
                raise DomainException(
                    f"Cliente con documento {documento_cli} no encontrado",
                    HTTP_404_NOT_FOUND
                )

            # TODO: Validar que no tenga motos registradas antes de eliminar

            return await self.repository.delete(documento_cli)
        except DomainException:
            raise
        except Exception as e:
            error_msg = str(e)
            # Manejar errores de integridad referencial
            if "ERROR_INTEGRIDAD_REFERENCIAL" in error_msg or "foreign key" in error_msg.lower() or "constraint" in error_msg.lower():
                raise DomainException(
                    f"No se puede eliminar el cliente. Tiene registros asociados (motos u órdenes)",
                    HTTP_400_BAD_REQUEST
                )
            raise DomainException(
                f"Error al eliminar cliente: {error_msg}",
                HTTP_400_BAD_REQUEST
            )
