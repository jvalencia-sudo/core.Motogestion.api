from typing import Dict, List
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from domain.contracts.productos.producto_contract import (
    ProductoCreateContract,
    ProductoUpdateContract,
    ProductoResponseContract,
    ImpuestoResponseContract,
    ComponenteResponseContract,
)
from domain.models.productos.producto_modelo import ProductoModelo
from domain.models.productos.producto_impuesto_modelo import ProductoImpuestoModelo
from domain.models.productos.paquete_componente_modelo import PaqueteComponenteModelo
from domain.models.productos.vw_producto_modelo import VwProductoModelo
from domain.services.base_service import BaseService
from domain.services.productos.producto_impuesto_servicio import ProductoImpuestoServicio
from infrastructure.exceptions.domain_exception import DomainException
from repository.productos.producto_repositorio import ProductoRepositorio
from repository.productos.paquete_componente_repositorio import PaqueteComponenteRepositorio


class ProductoServicio(BaseService[ProductoModelo, ProductoRepositorio]):
    def __init__(self):
        super().__init__(ProductoRepositorio())
        self.producto_impuesto_service = ProductoImpuestoServicio()
        self.paquete_repo = PaqueteComponenteRepositorio()

    # ---- Componentes de paquetes (combos) ----

    async def _guardar_componentes(self, cod_pro_paq: int, componentes: list) -> None:
        """Valida y guarda los componentes de un paquete (reemplazo total)."""
        await self.paquete_repo.eliminar_por_paquete(cod_pro_paq)
        for comp in componentes or []:
            if comp.cod_pro_comp == cod_pro_paq:
                raise DomainException("Un paquete no puede incluirse a sí mismo", HTTP_400_BAD_REQUEST)
            comp_dict = await self.repository.get_by_id(comp.cod_pro_comp)
            if not comp_dict:
                raise DomainException(
                    f"El componente con código {comp.cod_pro_comp} no existe", HTTP_400_BAD_REQUEST
                )
            comp_modelo = self.__parse_custom__(comp_dict, ProductoModelo)
            if comp_modelo.tipo_pro == "PAQUETE":
                raise DomainException(
                    "Un paquete no puede contener otro paquete", HTTP_400_BAD_REQUEST
                )
            await self.paquete_repo.create(PaqueteComponenteModelo(
                cod_pro_paq=cod_pro_paq,
                cod_pro_comp=comp.cod_pro_comp,
                cantidad_comp=comp.cantidad_comp,
            ))

    async def _obtener_componentes(self, cod_pro_paq: int) -> list:
        """Devuelve los componentes de un paquete como contratos de respuesta."""
        filas = await self.paquete_repo.listar_por_paquete(cod_pro_paq)
        return [
            ComponenteResponseContract(
                cod_pro_comp=f.get("COD_PRO_COMP"),
                nombre_pro=f.get("NOMBRE_PRO"),
                tipo_pro=f.get("TIPO_PRO"),
                cantidad_comp=f.get("CANTIDAD_COMP"),
            )
            for f in filas
        ]

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

            componentes_lista = (
                await self._obtener_componentes(producto_modelo.cod_pro)
                if producto_modelo.tipo_pro == "PAQUETE" else []
            )

            # Crear el contrato de respuesta del producto
            resultado.append(ProductoResponseContract(
                cod_pro=producto_modelo.cod_pro,
                nombre_pro=producto_modelo.nombre_pro,
                descripcion_pro=producto_modelo.descripcion_pro,
                tipo_pro=producto_modelo.tipo_pro,
                stock_pro=producto_modelo.stock_pro,
                stock_pro_min=producto_modelo.stock_pro_min,
                cod_est_pro=producto_modelo.cod_est_pro,
                precio_pro=producto_modelo.precio_pro,
                estado_producto=producto_modelo.estado_producto,
                impuestos=impuestos_lista,
                componentes=componentes_lista
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

            componentes_lista = (
                await self._obtener_componentes(producto_modelo.cod_pro)
                if producto_modelo.tipo_pro == "PAQUETE" else []
            )

            # Crear el contrato de respuesta del producto
            resultado.append(ProductoResponseContract(
                cod_pro=producto_modelo.cod_pro,
                nombre_pro=producto_modelo.nombre_pro,
                descripcion_pro=producto_modelo.descripcion_pro,
                tipo_pro=producto_modelo.tipo_pro,
                stock_pro=producto_modelo.stock_pro,
                stock_pro_min=producto_modelo.stock_pro_min,
                cod_est_pro=producto_modelo.cod_est_pro,
                precio_pro=producto_modelo.precio_pro,
                estado_producto=producto_modelo.estado_producto,
                impuestos=impuestos_lista,
                componentes=componentes_lista
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

        componentes_lista = (
            await self._obtener_componentes(cod_pro)
            if producto_modelo.tipo_pro == "PAQUETE" else []
        )

        return ProductoResponseContract(
            cod_pro=producto_modelo.cod_pro,
            nombre_pro=producto_modelo.nombre_pro,
            descripcion_pro=producto_modelo.descripcion_pro,
            tipo_pro=producto_modelo.tipo_pro,
            stock_pro=producto_modelo.stock_pro,
            stock_pro_min=producto_modelo.stock_pro_min,
            cod_est_pro=producto_modelo.cod_est_pro,
            precio_pro=producto_modelo.precio_pro,
            estado_producto=producto_modelo.estado_producto,
            impuestos=impuestos_lista,
            componentes=componentes_lista
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

        # El stock solo aplica a los BIEN. SERVICIO (mano de obra) no maneja stock.
        es_bien = contract.tipo_pro == "BIEN"
        if es_bien:
            stock_pro = contract.stock_pro if contract.stock_pro is not None else 0
            stock_pro_min = contract.stock_pro_min if contract.stock_pro_min is not None else 0
            if stock_pro < stock_pro_min:
                raise DomainException(
                    "El stock actual no puede ser menor que el stock mínimo",
                    HTTP_400_BAD_REQUEST
                )
        else:
            stock_pro = None
            stock_pro_min = None

        # Crear el producto (siempre activo por defecto: cod_est_pro = 1)
        nuevo_producto = ProductoModelo(
            cod_pro=0,
            nombre_pro=contract.nombre_pro,
            descripcion_pro=contract.descripcion_pro,
            stock_pro=stock_pro,
            stock_pro_min=stock_pro_min,
            cod_est_pro=1,  # Activo
            precio_pro=contract.precio_pro,
            tipo_pro=contract.tipo_pro
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

        # Si es un PAQUETE, guardar su receta de componentes
        if contract.tipo_pro == "PAQUETE" and contract.componentes:
            await self._guardar_componentes(cod_pro, contract.componentes)

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

        # Tipo efectivo tras la actualización (puede venir en el contrato o mantenerse)
        tipo_pro = contract.tipo_pro if contract.tipo_pro is not None else producto_actual_modelo.tipo_pro

        # El stock solo aplica a los BIEN. Si el producto es/queda SERVICIO → NULL.
        if tipo_pro == "BIEN":
            stock_actual = contract.stock_pro if contract.stock_pro is not None else producto_actual_modelo.stock_pro
            stock_min = contract.stock_pro_min if contract.stock_pro_min is not None else producto_actual_modelo.stock_pro_min
            stock_actual = stock_actual if stock_actual is not None else 0
            stock_min = stock_min if stock_min is not None else 0
            if stock_actual < stock_min:
                raise DomainException(
                    "El stock actual no puede ser menor que el stock mínimo",
                    HTTP_400_BAD_REQUEST
                )
        else:
            stock_actual = None
            stock_min = None

        # Preparar el modelo actualizado
        producto_actualizado = ProductoModelo(
            cod_pro=cod_pro,
            nombre_pro=contract.nombre_pro if contract.nombre_pro else producto_actual_modelo.nombre_pro,
            descripcion_pro=contract.descripcion_pro if contract.descripcion_pro else producto_actual_modelo.descripcion_pro,
            stock_pro=stock_actual,
            stock_pro_min=stock_min,
            cod_est_pro=producto_actual_modelo.cod_est_pro,
            precio_pro=contract.precio_pro if contract.precio_pro is not None else producto_actual_modelo.precio_pro,
            tipo_pro=tipo_pro
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

        # Reemplazar componentes del paquete si se proporcionan
        if contract.componentes is not None:
            await self._guardar_componentes(cod_pro, contract.componentes)

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
