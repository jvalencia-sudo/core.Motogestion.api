from typing import Dict, List, Optional
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from domain.contracts.motos.moto_contract import (
    MotoCreateContract,
    MotoUpdateContract,
    MotoResponseContract,
    MotoClienteResponseContract
)
from domain.models.motos.moto_modelo import MotoModelo
from domain.models.motos.vw_moto_completo_modelo import VwMotoDetalleModelo, VwMotoMarcasModelo
from domain.services.base_service import BaseService
from domain.services.marcas.marca_servicio import MarcaServicio
from domain.services.clientes.cliente_servicio import ClienteServicio
from infrastructure.exceptions.domain_exception import DomainException
from repository.motos.moto_repositorio import MotoRepositorio


class MotoServicio(BaseService[MotoModelo, MotoRepositorio]):
    def __init__(self):
        super().__init__(MotoRepositorio())
        self.marca_servicio = MarcaServicio()
        self.cliente_servicio = ClienteServicio()

    def __parse__(self, record: Dict) -> MotoModelo:
        normalized = self.__normalize_keys__(record)
        return MotoModelo.model_validate(normalized)

    async def obtener_todas_motos(self) -> List[MotoResponseContract]:
        """Obtiene todas las motos con información completa"""
        motos_dict = await self.repository.obtener_motos_detalle()

        resultado = []
        for m_dict in motos_dict:
            try:
                m = self.__parse_custom__(m_dict, VwMotoDetalleModelo)
                resultado.append(MotoResponseContract(
                    placa_mot=m.placa_mot,
                    modelo_mot=m.modelo_mot,
                    color_mot=m.color_mot,
                    cilindraje_mot=m.cilindraje_mot,
                    marca=m.marca,
                    propietario=m.nombre_completo_cliente,
                    telefono_cli=m.telefono_cli,
                    total_ordenes=0
                ))
            except Exception as e:
                print(f"Error parseando moto {m_dict}: {e}")
                continue

        return resultado

    async def obtener_motos_por_cliente(self, documento_cli: str) -> List[MotoResponseContract]:
        """Obtiene motos de un cliente específico"""
        motos_dict = await self.repository.obtener_motos_por_cliente(documento_cli)
        if not motos_dict:
            return []

        resultado = []
        for m_dict in motos_dict:
            try:
                m = self.__parse_custom__(m_dict, VwMotoDetalleModelo)
                resultado.append(MotoResponseContract(
                    placa_mot=m.placa_mot,
                    modelo_mot=m.modelo_mot,
                    color_mot=m.color_mot,
                    cilindraje_mot=m.cilindraje_mot,
                    marca=m.marca,
                    propietario=m.nombre_completo_cliente,
                    telefono_cli=m.telefono_cli,
                    total_ordenes=0
                ))
            except Exception as e:
                print(f"Error parseando moto {m_dict}: {e}")
                continue

        return resultado

    async def obtener_motos_cliente_simple(self, documento_cli: str) -> List[MotoClienteResponseContract]:
        """Obtiene motos de un cliente específico con información de marca"""
        # Validar que el cliente existe
        try:
            await self.cliente_servicio.obtener_cliente_por_documento(documento_cli)
        except DomainException:
            raise DomainException(
                f"Cliente con documento {documento_cli} no encontrado",
                HTTP_404_NOT_FOUND
            )

        # Obtener motos directamente de la tabla motos
        motos_dict = await self.repository.get_by_field("documento_cli_mot", documento_cli)
        if not motos_dict:
            return []

        resultado = []
        for m_dict in motos_dict:
            try:
                m = self.__parse__(m_dict)

                # Obtener información de la marca
                nombre_marca = ""
                try:
                    marca = await self.marca_servicio.obtener_marca_por_id(m.cod_marca_mot)
                    nombre_marca = marca.nombre_mar
                except Exception as e:
                    print(f"Error obteniendo marca {m.cod_marca_mot}: {e}")
                    nombre_marca = "Desconocida"

                resultado.append(MotoClienteResponseContract(
                    placa_mot=m.placa_mot,
                    modelo_mot=m.modelo_mot,
                    color_mot=m.color_mot,
                    cilindraje_mot=m.cilindraje_mot,
                    documento_cli_mot=m.documento_cli_mot,
                    cod_marca_mot=m.cod_marca_mot,
                    nombre_marca=nombre_marca
                ))
            except Exception as e:
                print(f"Error parseando moto {m_dict}: {e}")
                continue

        return resultado

    async def obtener_motos_por_marca(self, cod_marca_mot: int) -> List[MotoResponseContract]:
        """Obtiene motos de una marca específica"""
        motos_dict = await self.repository.obtener_motos_por_marca(cod_marca_mot)
        if not motos_dict:
            return []

        resultado: List[MotoResponseContract] = []

        for m_dict in motos_dict:
            try:
                # Parsear con modelo tipado para la vista vw_motos_marcas
                moto_vista = self.__parse_custom__(m_dict, VwMotoMarcasModelo)

                # Obtener información del cliente
                propietario: str = ""
                telefono: str = ""

                try:
                    cliente = await self.cliente_servicio.obtener_cliente_por_documento(
                        moto_vista.documento_cli_mot
                    )
                    propietario = cliente.nombre_completo
                    telefono = cliente.telefono_cli
                except DomainException:
                    # Cliente no encontrado, dejar valores por defecto
                    pass
                except Exception as e:
                    print(f"Error obteniendo cliente {moto_vista.documento_cli_mot}: {e}")

                resultado.append(MotoResponseContract(
                    placa_mot=moto_vista.placa_mot,
                    modelo_mot=moto_vista.modelo_mot,
                    color_mot=moto_vista.color_mot,
                    cilindraje_mot=moto_vista.cilindraje_mot,
                    marca=moto_vista.marca,
                    propietario=propietario,
                    telefono_cli=telefono,
                    total_ordenes=0
                ))
            except Exception as e:
                print(f"Error procesando moto {m_dict}: {e}")
                continue

        return resultado

    async def obtener_moto_por_id(self, placa_mot: str) -> MotoResponseContract:
        """Obtiene moto por placa"""
        if not placa_mot or len(placa_mot) != 6:
            raise DomainException(
                "Placa de moto inválida",
                HTTP_400_BAD_REQUEST
            )

        moto_dict = await self.repository.get_by_id(placa_mot)
        if not moto_dict:
            raise DomainException(
                f"Moto con placa {placa_mot} no encontrada",
                HTTP_404_NOT_FOUND
            )

        # Parsear como moto básica
        moto_modelo = self.__parse__(moto_dict)

        # Obtener información del cliente y marca para completar la respuesta
        propietario = ""
        telefono = ""
        marca_nombre = ""

        try:
            cliente = await self.cliente_servicio.obtener_cliente_por_documento(
                moto_modelo.documento_cli_mot
            )
            propietario = cliente.nombre_completo
            telefono = cliente.telefono_cli
        except Exception as e:
            print(f"Error obteniendo cliente {moto_modelo.documento_cli_mot}: {e}")

        try:
            marca = await self.marca_servicio.obtener_marca_por_id(moto_modelo.cod_marca_mot)
            marca_nombre = marca.nombre_mar
        except Exception as e:
            print(f"Error obteniendo marca {moto_modelo.cod_marca_mot}: {e}")

        return MotoResponseContract(
            placa_mot=moto_modelo.placa_mot,
            modelo_mot=moto_modelo.modelo_mot,
            color_mot=moto_modelo.color_mot,
            cilindraje_mot=moto_modelo.cilindraje_mot,
            marca=marca_nombre,
            propietario=propietario,
            telefono_cli=telefono,
            total_ordenes=0
        )

    async def crear_moto(self, contract: MotoCreateContract) -> MotoResponseContract:
        """Crea nueva moto"""
        try:
            # Validar placa única
            existe = await self.repository.existe_moto(contract.placa_mot)
            if existe:
                raise DomainException(
                    f"Moto con placa {contract.placa_mot} ya existe",
                    HTTP_400_BAD_REQUEST
                )

            # Validar cliente existe
            try:
                cliente = await self.cliente_servicio.obtener_cliente_por_documento(
                    contract.documento_cli_mot
                )
                if not cliente:
                    raise DomainException(
                        f"Cliente con documento {contract.documento_cli_mot} no existe",
                        HTTP_404_NOT_FOUND
                    )
            except DomainException:
                raise

            # Validar marca existe
            try:
                marca = await self.marca_servicio.obtener_marca_por_id(contract.cod_marca_mot)
                if not marca:
                    raise DomainException(
                        f"Marca con código {contract.cod_marca_mot} no existe",
                        HTTP_404_NOT_FOUND
                    )
            except DomainException:
                raise

            modelo = MotoModelo(**contract.model_dump(exclude_unset=True))
            await self.repository.create(modelo)

            return MotoResponseContract(
                placa_mot=contract.placa_mot,
                modelo_mot=contract.modelo_mot,
                color_mot=contract.color_mot,
                cilindraje_mot=contract.cilindraje_mot,
                marca=marca.nombre_mar,
                propietario=cliente.nombre_completo,
                telefono_cli=cliente.telefono_cli,
                total_ordenes=0
            )
        except DomainException:
            raise
        except Exception as e:
            print(f"Error inesperado en crear_moto: {e}")
            raise DomainException(
                f"Error al crear la moto: {str(e)}",
                HTTP_400_BAD_REQUEST
            )

    async def actualizar_moto(self, placa_mot: str, contract: MotoUpdateContract) -> MotoResponseContract:
        """Actualiza moto"""
        # Validar existencia
        moto_dict = await self.repository.get_by_id(placa_mot)
        if not moto_dict:
            raise DomainException(
                f"Moto con placa {placa_mot} no encontrada",
                HTTP_404_NOT_FOUND
            )
        moto_modelo = self.__parse__(moto_dict)
        # Validar cliente si cambió
        if contract.documento_cli_mot and contract.documento_cli_mot != moto_modelo.documento_cli_mot:
            try:
                cliente = await self.cliente_servicio.obtener_cliente_por_documento(
                    contract.documento_cli_mot
                )
                if not cliente:
                    raise DomainException(
                        f"Cliente con documento {contract.documento_cli_mot} no existe",
                        HTTP_404_NOT_FOUND
                    )
            except DomainException:
                raise

        # Validar marca si cambió
        if contract.cod_marca_mot and contract.cod_marca_mot != moto_modelo.cod_marca_mot:
            try:
                marca = await self.marca_servicio.obtener_marca_por_id(contract.cod_marca_mot)
                if not marca:
                    raise DomainException(
                        f"Marca con código {contract.cod_marca_mot} no existe",
                        HTTP_404_NOT_FOUND
                    )
            except DomainException:
                raise

        # Actualizar moto
        moto_modelo = self.__parse__(moto_dict)

        update_data = contract.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(moto_modelo, key, value)

        await self.repository.update(moto_modelo)

        # Obtener datos actualizados
        moto_actualizada = await self.repository.get_by_id(placa_mot)
        moto_modelo = self.__parse__(moto_actualizada)

        # Obtener información complementaria
        propietario = ""
        telefono = ""
        marca_nombre = ""

        try:
            cliente = await self.cliente_servicio.obtener_cliente_por_documento(
                moto_modelo.documento_cli_mot
            )
            propietario = cliente.nombre_completo
            telefono = cliente.telefono_cli
        except Exception as e:
            print(f"Error obteniendo cliente: {e}")

        try:
            marca = await self.marca_servicio.obtener_marca_por_id(moto_modelo.cod_marca_mot)
            marca_nombre = marca.nombre_mar
        except Exception as e:
            print(f"Error obteniendo marca: {e}")

        return MotoResponseContract(
            placa_mot=moto_modelo.placa_mot,
            modelo_mot=moto_modelo.modelo_mot,
            color_mot=moto_modelo.color_mot,
            cilindraje_mot=moto_modelo.cilindraje_mot,
            marca=marca_nombre,
            propietario=propietario,
            telefono_cli=telefono,
            total_ordenes=0
        )

    async def eliminar_moto(self, placa_mot: str) -> bool:
        """Elimina moto"""
        try:
            moto_dict = await self.repository.get_by_id(placa_mot)
            if not moto_dict:
                raise DomainException(
                    f"Moto con placa {placa_mot} no encontrada",
                    HTTP_404_NOT_FOUND
                )

            return await self.repository.delete(placa_mot)
        except DomainException:
            raise
        except Exception as e:
            error_msg = str(e)
            # Manejar errores de integridad referencial
            if "ERROR_INTEGRIDAD_REFERENCIAL" in error_msg or "foreign key" in error_msg.lower() or "constraint" in error_msg.lower():
                raise DomainException(
                    f"No se puede eliminar la moto. Tiene registros asociados (órdenes o servicios)",
                    HTTP_400_BAD_REQUEST
                )
            raise DomainException(
                f"Error al eliminar moto: {error_msg}",
                HTTP_400_BAD_REQUEST
            )
