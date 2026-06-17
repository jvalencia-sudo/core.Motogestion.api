from typing import Dict, List
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from domain.contracts.productos.producto_contract import (
    ProductoCreateContract,
    ProductoUpdateContract,
    ProductoResponseContract,
    ImpuestoResponseContract
)
from domain.models.productos.producto_modelo import ProductoModelo
from domain.models.productos.producto_impuesto_modelo import ProductoImpuestoModelo
from domain.models.productos.vw_producto_modelo import VwProductoModelo
from domain.services.base_service import BaseService
from domain.services.productos.producto_impuesto_servicio import ProductoImpuestoServicio
from infrastructure.exceptions.domain_exception import DomainException
from repository.productos.producto_repositorio import ProductoRepositorio


class ProductoServicio(BaseService[ProductoModelo, ProductoRepositorio]):
    def __init__(self):
        super().__init__(ProductoRepositorio())
        self.producto_impuesto_service = ProductoImpuestoServicio()

    def __parse__(self, record: Dict) -> ProductoModelo:
        return ProductoModelo.model_validate(record)

    async def obtener_todos_productos(self) -> List[ProductoResponseContract]:
        """Obtiene todos los productos con sus impuestos mapeando a modelos Pydantic"""
        productos_dict = await self.repository.obtener_todos_con_impuestos()

        # Mapear a modelo Pydantic usando __parse_all_custom__
        productos_modelos = self.__parse_all_custom__(productos_dict, VwProductoModelo)

        resultado = []
        for producto_modelo in productos_modelos:
            # Obtener impuestos del producto usando el servicio
            impuestos_modelos = await self.producto_impuesto_service.obtener_impuestos_por_producto(
                producto_modelo.cod_pro
            )

            # Mapear impuestos a contratos de respuesta
            impuestos_lista = [
                ImpuestoResponseContract(
                    cod_imp=imp.cod_imp_pro_imp,
                    nombre_imp=imp.nombre_imp,
                    porcentaje=imp.porcentaje_pro_imp
                )
                for imp in impuestos_modelos
            ]

            # Crear el contrato de respuesta del producto
            resultado.append(ProductoResponseContract(
                cod_pro=producto_modelo.cod_pro,
                nombre_pro=producto_modelo.nombre_pro,
                descripcion_pro=producto_modelo.descripcion_pro,
                stock_pro=producto_modelo.stock_pro,
                stock_pro_min=producto_modelo.stock_pro_min,
                cod_est_pro=producto_modelo.cod_est_pro,
                precio_pro=producto_modelo.precio_pro,
                estado_producto=producto_modelo.estado_producto,
                impuestos=impuestos_lista
            ))

        return resultado

    async def obtener_productos_activos(self) -> List[ProductoResponseContract]:
        """Obtiene solo los productos activos mapeando a modelos Pydantic"""
        productos_dict = await self.repository.obtener_activos()

        # Mapear a modelo Pydantic usando __parse_all_custom__
        productos_modelos = self.__parse_all_custom__(productos_dict, VwProductoModelo)

        resultado = []
        for producto_modelo in productos_modelos:
            # Obtener impuestos del producto usando el servicio
            impuestos_modelos = await self.producto_impuesto_service.obtener_impuestos_por_producto(
                producto_modelo.cod_pro
            )

            # Mapear impuestos a contratos de respuesta
            impuestos_lista = [
                ImpuestoResponseContract(
                    cod_imp=imp.cod_imp_pro_imp,
                    nombre_imp=imp.nombre_imp,
                    porcentaje=imp.porcentaje_pro_imp
                )
                for imp in impuestos_modelos
            ]

            # Crear el contrato de respuesta del producto
            resultado.append(ProductoResponseContract(
                cod_pro=producto_modelo.cod_pro,
                nombre_pro=producto_modelo.nombre_pro,
                descripcion_pro=producto_modelo.descripcion_pro,
                stock_pro=producto_modelo.stock_pro,
                stock_pro_min=producto_modelo.stock_pro_min,
                cod_est_pro=producto_modelo.cod_est_pro,
                precio_pro=producto_modelo.precio_pro,
                estado_producto=producto_modelo.estado_producto,
                impuestos=impuestos_lista
            ))

        return resultado

    async def obtener_producto_por_id(self, cod_pro: int) -> ProductoResponseContract:
        """Obtiene un producto por su código mapeando a modelo Pydantic"""
        producto_dict = await self.repository.obtener_producto_con_impuestos(cod_pro)

        if not producto_dict:
            raise DomainException(
                f"Producto con código {cod_pro} no encontrado",
                HTTP_404_NOT_FOUND
            )

        # Mapear a modelo Pydantic usando tipado estático
        producto_modelo = self.__parse_custom__(producto_dict, VwProductoModelo)

        # Obtener impuestos del producto usando el servicio
        impuestos_modelos = await self.producto_impuesto_service.obtener_impuestos_por_producto(cod_pro)

        # Mapear impuestos a contratos de respuesta
        impuestos_lista = [
            ImpuestoResponseContract(
                cod_imp=imp.cod_imp_pro_imp,
                nombre_imp=imp.nombre_imp,
                porcentaje=imp.porcentaje_pro_imp
            )
            for imp in impuestos_modelos
        ]

        return ProductoResponseContract(
            cod_pro=producto_modelo.cod_pro,
            nombre_pro=producto_modelo.nombre_pro,
            descripcion_pro=producto_modelo.descripcion_pro,
            stock_pro=producto_modelo.stock_pro,
            stock_pro_min=producto_modelo.stock_pro_min,
            cod_est_pro=producto_modelo.cod_est_pro,
            precio_pro=producto_modelo.precio_pro,
            estado_producto=producto_modelo.estado_producto,
            impuestos=impuestos_lista
        )

    async def crear_producto(self, contract: ProductoCreateContract) -> ProductoResponseContract:
        """Crea un nuevo producto con sus impuestos"""
        # Validar que no exista un producto con el mismo nombre
        existe = await self.repository.existe_producto(contract.nombre_pro)
        if existe:
            raise DomainException(
                f"Ya existe un producto con el nombre '{contract.nombre_pro}'",
                HTTP_400_BAD_REQUEST
            )

        # Validar stock mínimo
        if contract.stock_pro < contract.stock_pro_min:
            raise DomainException(
                "El stock actual no puede ser menor que el stock mínimo",
                HTTP_400_BAD_REQUEST
            )

        # Crear el producto (siempre activo por defecto: cod_est_pro = 1)
        nuevo_producto = ProductoModelo(
            cod_pro=0,
            nombre_pro=contract.nombre_pro,
            descripcion_pro=contract.descripcion_pro,
            stock_pro=contract.stock_pro,
            stock_pro_min=contract.stock_pro_min,
            cod_est_pro=1,  # Activo
            precio_pro=contract.precio_pro
        )

        cod_pro = await self.repository.create(nuevo_producto)
        print(f"Producto creado con código: {cod_pro}")

        # Agregar impuestos si los hay usando el servicio
        if contract.impuestos:
            for impuesto in contract.impuestos:
                producto_impuesto = ProductoImpuestoModelo(
                    cod_pro_imp=0,
                    cod_imp_pro_imp=impuesto.cod_imp,
                    cod_pro_pro_imp=cod_pro,
                    porcentaje_pro_imp=impuesto.porcentaje
                )
                await self.producto_impuesto_service.create(producto_impuesto)

        # Retornar el producto creado
        return await self.obtener_producto_por_id(cod_pro)

    async def actualizar_producto(self, cod_pro: int, contract: ProductoUpdateContract) -> ProductoResponseContract:
        """Actualiza un producto existente mapeando a modelo Pydantic"""
        # Verificar que el producto existe
        producto_actual_dict = await self.repository.obtener_producto_con_impuestos(cod_pro)
        if not producto_actual_dict:
            raise DomainException(
                f"Producto con código {cod_pro} no encontrado",
                HTTP_404_NOT_FOUND
            )

        # Mapear a modelo Pydantic usando tipado estático
        producto_actual_modelo = self.__parse_custom__(producto_actual_dict, VwProductoModelo)

        # Validar nombre único si se está actualizando
        if contract.nombre_pro:
            existe = await self.repository.existe_producto(contract.nombre_pro, cod_pro)
            if existe:
                raise DomainException(
                    f"Ya existe otro producto con el nombre '{contract.nombre_pro}'",
                    HTTP_400_BAD_REQUEST
                )

        # Validar stock mínimo
        stock_actual = contract.stock_pro if contract.stock_pro is not None else producto_actual_modelo.stock_pro
        stock_min = contract.stock_pro_min if contract.stock_pro_min is not None else producto_actual_modelo.stock_pro_min

        if stock_actual < stock_min:
            raise DomainException(
                "El stock actual no puede ser menor que el stock mínimo",
                HTTP_400_BAD_REQUEST
            )

        # Preparar el modelo actualizado
        producto_actualizado = ProductoModelo(
            cod_pro=cod_pro,
            nombre_pro=contract.nombre_pro if contract.nombre_pro else producto_actual_modelo.nombre_pro,
            descripcion_pro=contract.descripcion_pro if contract.descripcion_pro else producto_actual_modelo.descripcion_pro,
            stock_pro=stock_actual,
            stock_pro_min=stock_min,
            cod_est_pro=producto_actual_modelo.cod_est_pro,
            precio_pro=contract.precio_pro if contract.precio_pro is not None else producto_actual_modelo.precio_pro
        )

        await self.repository.update(producto_actualizado)

        # Actualizar impuestos si se proporcionan usando el servicio
        if contract.impuestos is not None:
            # Eliminar impuestos existentes
            await self.producto_impuesto_service.eliminar_impuestos_producto(cod_pro)

            # Agregar nuevos impuestos
            for impuesto in contract.impuestos:
                producto_impuesto = ProductoImpuestoModelo(
                    cod_pro_imp=0,
                    cod_imp_pro_imp=impuesto.cod_imp,
                    cod_pro_pro_imp=cod_pro,
                    porcentaje_pro_imp=impuesto.porcentaje
                )
                await self.producto_impuesto_service.create(producto_impuesto)

        # Retornar el producto actualizado
        return await self.obtener_producto_por_id(cod_pro)

    async def desactivar_producto(self, cod_pro: int) -> dict:
        """Desactiva un producto (soft delete) mapeando a modelo Pydantic"""
        # Verificar que el producto existe
        producto_dict = await self.repository.obtener_producto_con_impuestos(cod_pro)
        if not producto_dict:
            raise DomainException(
                f"Producto con código {cod_pro} no encontrado",
                HTTP_404_NOT_FOUND
            )

        # Mapear a modelo Pydantic usando tipado estático
        producto_modelo = self.__parse_custom__(producto_dict, VwProductoModelo)

        # Verificar que no esté ya desactivado
        if producto_modelo.cod_est_pro == 2:
            raise DomainException(
                "El producto ya está desactivado",
                HTTP_400_BAD_REQUEST
            )

        await self.repository.desactivar_producto(cod_pro)

        return {
            "message": f"Producto {producto_modelo.nombre_pro} desactivado exitosamente",
            "cod_pro": cod_pro
        }

    async def activar_producto(self, cod_pro: int) -> dict:
        """Activa un producto mapeando a modelo Pydantic"""
        # Verificar que el producto existe
        producto_dict = await self.repository.obtener_producto_con_impuestos(cod_pro)
        if not producto_dict:
            raise DomainException(
                f"Producto con código {cod_pro} no encontrado",
                HTTP_404_NOT_FOUND
            )

        # Mapear a modelo Pydantic usando tipado estático
        producto_modelo = self.__parse_custom__(producto_dict, VwProductoModelo)

        # Verificar que no esté ya activo
        if producto_modelo.cod_est_pro == 1:
            raise DomainException(
                "El producto ya está activo",
                HTTP_400_BAD_REQUEST
            )

        await self.repository.activar_producto(cod_pro)

        return {
            "message": f"Producto {producto_modelo.nombre_pro} activado exitosamente",
            "cod_pro": cod_pro
        }
