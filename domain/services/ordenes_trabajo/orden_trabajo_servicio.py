from typing import Dict, List, Optional
from datetime import date, timedelta
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from domain.models.ordenes_trabajo.orden_trabajo_modelo import (
    OrdenTrabajoModelo,
    VwOrdenesTrabajoCompleta,
    VwResumenFinancieroOt,
    OrdenAnteriorModelo
)
from domain.models.ordenes_trabajo.detalle_orden_trabajo_modelo import VwDetalleOtProductos, DetalleOrdenTrabajoModelo
from domain.models.ordenes_trabajo.ot_estado_modelo import OtEstadoModelo
from domain.models.productos.producto_modelo import ProductoModelo
from domain.contracts.ordenes_trabajo.orden_trabajo_contract import (
    OrdenTrabajoCreateContract,
    OrdenTrabajoUpdateContract,
    OrdenTrabajoResponseContract,
    CambiarEstadoContract,
    EntregarOrdenContract,
    OrdenTrabajoResumenContract,
    OtEstadoResponseContract
)
from domain.contracts.ordenes_trabajo.detalle_orden_trabajo_contract import (
    DetalleOrdenTrabajoContract,
    DetalleOrdenTrabajoResponseContract
)
from domain.services.base_service import BaseService
from repository.ordenes_trabajo.orden_trabajo_repositorio import OrdenTrabajoRepositorio
from repository.ordenes_trabajo.detalle_orden_trabajo_repositorio import DetalleOrdenTrabajoRepositorio
from repository.ordenes_trabajo.ot_estado_repositorio import OtEstadoRepositorio
from repository.motos.moto_repositorio import MotoRepositorio
from repository.productos.producto_repositorio import ProductoRepositorio
from infrastructure.exceptions.domain_exception import DomainException


class OrdenTrabajoServicio(BaseService[OrdenTrabajoModelo, OrdenTrabajoRepositorio]):
    def __init__(self):
        super().__init__(OrdenTrabajoRepositorio())
        self.detalle_repository = DetalleOrdenTrabajoRepositorio()
        self.estado_repository = OtEstadoRepositorio()
        self.moto_repository = MotoRepositorio()
        self.producto_repository = ProductoRepositorio()

    def __parse__(self, record: Dict) -> OrdenTrabajoModelo:
        return OrdenTrabajoModelo.model_validate(record)

    async def obtener_todas_ordenes(self) -> List[OrdenTrabajoResumenContract]:
        """Obtiene todas las ordenes de trabajo con informacion resumida"""
        ordenes_dict = await self.repository.obtener_ordenes_completas()
        ordenes_modelos = self.__parse_all_custom__(ordenes_dict, VwOrdenesTrabajoCompleta)

        resultado = []
        for orden in ordenes_modelos:
            # Obtener resumen financiero si existe
            resumen_dict = await self.repository.obtener_resumen_financiero(orden.consecutivo_ot)
            total_ot = 0.0
            if resumen_dict:
                resumen_modelo = self.__parse_custom__(resumen_dict, VwResumenFinancieroOt)
                total_ot = float(resumen_modelo.total_ot or 0.0)

            resultado.append(OrdenTrabajoResumenContract(
                consecutivo_ot=orden.consecutivo_ot,
                fecha_elaboracion_ot=orden.fecha_elaboracion_ot,
                fecha_entrega_ot=orden.fecha_entrega_ot,
                placa_mot=orden.placa_mot,
                nombre_completo_cliente=orden.nombre_completo_cliente,
                telefono_cli=orden.telefono_cli,
                estado_ot=orden.estado_ot,
                mecanico=orden.mecanico,
                total_ot=total_ot
            ))

        return resultado

    async def obtener_estados(self) -> List[OtEstadoResponseContract]:
        """Obtiene todos los estados de ordenes de trabajo"""
        estados_dict = await self.estado_repository.obtener_todos_estados()
        estados_modelos = self.__parse_all_custom__(estados_dict, OtEstadoModelo)

        return [
            OtEstadoResponseContract(
                cod_ot_est=estado.cod_ot_est,
                nombre_ot_est=estado.nombre_ot_est
            )
            for estado in estados_modelos
        ]

    async def obtener_orden_por_id(self, consecutivo_ot: int) -> OrdenTrabajoResponseContract:
        """Obtiene una orden de trabajo completa con todos sus detalles"""
        # Obtener orden usando vista
        orden_dict = await self.repository.obtener_orden_por_id(consecutivo_ot)

        if not orden_dict:
            raise DomainException(
                f"Orden de trabajo con consecutivo {consecutivo_ot} no encontrada",
                HTTP_404_NOT_FOUND
            )

        # Mapear a modelo Pydantic usando tipado estatico
        orden_modelo = self.__parse_custom__(orden_dict, VwOrdenesTrabajoCompleta)

        # Obtener detalles de la orden
        detalles_dict = await self.detalle_repository.obtener_detalles_por_orden(consecutivo_ot)
        detalles_modelos = self.__parse_all_custom__(detalles_dict, VwDetalleOtProductos)

        # Mapear detalles a contratos de respuesta
        detalles_lista = [
            DetalleOrdenTrabajoResponseContract(
                consecutivo_ot_deto=det.consecutivo_ot_deto,
                cod_pro_deto=det.cod_pro_deto,
                nombre_pro=det.nombre_pro,
                descripcion_pro=det.descripcion_pro,
                cantidad_deto=det.cantidad_deto,
                valor_unitario_deto=det.valor_unitario_deto,
                subtotal=float(det.subtotal),
                fecha_confirmacion_deto=det.fecha_confirmacion_deto,
                usuario_confirmacion=det.usuario_confirmacion,
                estado_producto=det.estado_producto
            )
            for det in detalles_modelos
        ]

        # Obtener resumen financiero
        resumen_dict = await self.repository.obtener_resumen_financiero(consecutivo_ot)
        total_items = 0
        subtotal_productos = 0.0
        total_impuestos = 0.0
        total_ot = 0.0

        if resumen_dict:
            resumen_modelo = self.__parse_custom__(resumen_dict, VwResumenFinancieroOt)
            total_items = int(resumen_modelo.total_items or 0)
            subtotal_productos = float(resumen_modelo.subtotal_productos or 0.0)
            total_impuestos = float(resumen_modelo.total_impuestos or 0.0)
            total_ot = float(resumen_modelo.total_ot or 0.0)

        return OrdenTrabajoResponseContract(
            consecutivo_ot=orden_modelo.consecutivo_ot,
            fecha_elaboracion_ot=orden_modelo.fecha_elaboracion_ot,
            fecha_entrega_ot=orden_modelo.fecha_entrega_ot,
            kilometraje_ingreso_ot=orden_modelo.kilometraje_ingreso_ot,
            observacion_cli_ot=orden_modelo.observacion_cli_ot,
            observacion_ot=orden_modelo.observacion_ot,
            fecha_fin_garantia_ot=orden_modelo.fecha_fin_garantia_ot,
            placa_mot=orden_modelo.placa_mot,
            modelo_mot=orden_modelo.modelo_mot,
            color_mot=orden_modelo.color_mot,
            cilindraje_mot=orden_modelo.cilindraje_mot,
            marca_moto=orden_modelo.marca_moto,
            documento_cli=orden_modelo.documento_cli,
            nombre_completo_cliente=orden_modelo.nombre_completo_cliente,
            telefono_cli=orden_modelo.telefono_cli,
            correo_cli=orden_modelo.correo_cli,
            direccion_cli=orden_modelo.direccion_cli,
            documento_recepcionista=orden_modelo.documento_recepcionista,
            recepcionista=orden_modelo.recepcionista,
            documento_mecanico=orden_modelo.documento_mecanico,
            mecanico=orden_modelo.mecanico,
            estado_ot=orden_modelo.estado_ot,
            cod_ot_est_ot=orden_modelo.cod_ot_est_ot,
            detalles=detalles_lista,
            total_items=total_items,
            subtotal_productos=subtotal_productos,
            total_impuestos=total_impuestos,
            total_ot=total_ot
        )

    async def crear_orden_trabajo(
        self,
        contract: OrdenTrabajoCreateContract,
        documento_usu_creador: str
    ) -> OrdenTrabajoResponseContract:
        """Crea una nueva orden de trabajo con sus detalles"""
        # Validar que la moto existe
        moto_dict = await self.moto_repository.get_by_id(contract.placa_mot_ot)
        if not moto_dict:
            raise DomainException(
                f"Moto con placa {contract.placa_mot_ot} no encontrada",
                HTTP_404_NOT_FOUND
            )

        # Validar garantía si se intenta crear directamente en estado 6 (Garantía)
        estado_inicial = contract.cod_ot_est_ot if contract.cod_ot_est_ot else 1
        if estado_inicial == 6:
            orden_anterior_dict = await self.repository.obtener_orden_anterior(
                contract.placa_mot_ot,
                0  # 0 porque la orden aún no existe
            )

            if not orden_anterior_dict:
                raise DomainException(
                    f"No se puede crear una orden con estado Garantía. Esta moto no tiene órdenes anteriores entregadas",
                    HTTP_400_BAD_REQUEST
                )

            # Convertir a modelo Pydantic
            orden_anterior = self.__parse_custom__(orden_anterior_dict, OrdenAnteriorModelo)

            if orden_anterior.fecha_fin_garantia_ot:
                if orden_anterior.fecha_fin_garantia_ot < date.today():
                    raise DomainException(
                        f"No se puede crear orden con estado Garantía. La garantía de la orden anterior venció el {orden_anterior.fecha_fin_garantia_ot.strftime('%d/%m/%Y')}",
                        HTTP_400_BAD_REQUEST
                    )

        # Validar que los productos existen y tienen stock
        for detalle in contract.detalles:
            producto_dict = await self.producto_repository.get_by_id(detalle.cod_pro_deto)
            if not producto_dict:
                raise DomainException(
                    f"Producto con codigo {detalle.cod_pro_deto} no encontrado",
                    HTTP_404_NOT_FOUND
                )

            # Parsear a modelo Pydantic para tipado estático
            producto = self.__parse_custom__(producto_dict, ProductoModelo)

            # Validar stock disponible SOLO si la cantidad es positiva (se factura)
            if detalle.cantidad_deto > 0:
                if producto.stock_pro < detalle.cantidad_deto:
                    raise DomainException(
                        f"Stock insuficiente para el producto {producto.nombre_pro}. Disponible: {producto.stock_pro}, Solicitado: {detalle.cantidad_deto}",
                        HTTP_400_BAD_REQUEST
                    )

        # Crear el modelo de orden de trabajo
        orden_modelo = OrdenTrabajoModelo(
            fecha_elaboracion_ot=date.today(),
            fecha_entrega_ot=contract.fecha_entrega_ot,
            placa_mot_ot=contract.placa_mot_ot,
            kilometraje_ingreso_ot=contract.kilometraje_ingreso_ot,
            documento_usu_rp_ot=contract.documento_usu_rp_ot,
            documento_usu_mc_ot=contract.documento_usu_mc_ot,
            observacion_cli_ot=contract.observacion_cli_ot,
            observacion_ot=contract.observacion_ot,
            fecha_fin_garantia_ot=contract.fecha_fin_garantia_ot,
            cod_ot_est_ot=estado_inicial
        )

        # Crear la orden de trabajo
        consecutivo_ot = await self.repository.create(orden_modelo)

        # Crear los detalles y actualizar stock
        for detalle in contract.detalles:
            producto_dict = await self.producto_repository.get_by_id(detalle.cod_pro_deto)
            producto = self.__parse_custom__(producto_dict, ProductoModelo)

            # Usar valor unitario del producto si no se proporciona
            valor_unitario = detalle.valor_unitario_deto
            if not valor_unitario:
                valor_unitario = producto.precio_pro

            # Crear detalle
            await self.detalle_repository.crear_detalle(
                consecutivo_ot=consecutivo_ot,
                cod_pro=detalle.cod_pro_deto,
                cantidad=detalle.cantidad_deto,
                valor_unitario=valor_unitario,
                documento_usu=documento_usu_creador
            )

            # Actualizar stock del producto según el signo de la cantidad
            # IMPORTANTE: Productos NO facturables (cantidad negativa) NO afectan el stock
            if detalle.cantidad_deto > 0:
                # Producto SE FACTURA: restar del stock
                nuevo_stock = producto.stock_pro - detalle.cantidad_deto
                await self.producto_repository.actualizar_stock(detalle.cod_pro_deto, nuevo_stock)
            # Si cantidad < 0 (NO se factura): NO hacer nada con el stock

        # Retornar la orden creada completa
        return await self.obtener_orden_por_id(consecutivo_ot)

    async def actualizar_orden(
        self,
        consecutivo_ot: int,
        contract: OrdenTrabajoUpdateContract
    ) -> OrdenTrabajoResponseContract:
        """Actualiza una orden de trabajo existente"""
        # Verificar que la orden existe
        orden_actual_dict = await self.repository.obtener_orden_por_id(consecutivo_ot)
        if not orden_actual_dict:
            raise DomainException(
                f"Orden de trabajo con consecutivo {consecutivo_ot} no encontrada",
                HTTP_404_NOT_FOUND
            )

        orden_actual = self.__parse_custom__(orden_actual_dict, VwOrdenesTrabajoCompleta)

        # Validar garantía si se intenta cambiar a estado 6 (Garantía)
        if contract.cod_ot_est_ot is not None and contract.cod_ot_est_ot == 6:
            orden_anterior_dict = await self.repository.obtener_orden_anterior(
                orden_actual.placa_mot,
                consecutivo_ot
            )

            if not orden_anterior_dict:
                raise DomainException(
                    f"No se puede cambiar a estado Garantía. Esta moto no tiene órdenes anteriores entregadas",
                    HTTP_400_BAD_REQUEST
                )

            # Convertir a modelo Pydantic
            orden_anterior = self.__parse_custom__(orden_anterior_dict, OrdenAnteriorModelo)

            if orden_anterior.fecha_fin_garantia_ot:
                if orden_anterior.fecha_fin_garantia_ot < date.today():
                    raise DomainException(
                        f"No se puede cambiar a estado Garantía. La garantía de la orden anterior venció el {orden_anterior.fecha_fin_garantia_ot.strftime('%d/%m/%Y')}",
                        HTTP_400_BAD_REQUEST
                    )

        # Crear modelo para actualizar solo con los campos proporcionados
        datos_actualizacion = {}
        if contract.fecha_entrega_ot is not None:
            datos_actualizacion['FECHA_ENTREGA_OT'] = contract.fecha_entrega_ot
        if contract.observacion_ot is not None:
            datos_actualizacion['OBSERVACION_OT'] = contract.observacion_ot
        if contract.cod_ot_est_ot is not None:
            datos_actualizacion['COD_OT_EST_OT'] = contract.cod_ot_est_ot
        if contract.fecha_fin_garantia_ot is not None:
            datos_actualizacion['FECHA_FIN_GARANTIA_OT'] = contract.fecha_fin_garantia_ot
        if contract.documento_usu_rp_ot is not None:
            datos_actualizacion['DOCUMENTO_USU_RP_OT'] = contract.documento_usu_rp_ot
        if contract.documento_usu_mc_ot is not None:
            datos_actualizacion['DOCUMENTO_USU_MC_OT'] = contract.documento_usu_mc_ot

        if datos_actualizacion:
            await self.repository.actualizar_campos(consecutivo_ot, datos_actualizacion)

        return await self.obtener_orden_por_id(consecutivo_ot)

    async def cambiar_estado(
        self,
        consecutivo_ot: int,
        contract: CambiarEstadoContract
    ) -> OrdenTrabajoResponseContract:
        """Cambia el estado de una orden de trabajo"""
        # Verificar que la orden existe
        orden_actual_dict = await self.repository.obtener_orden_por_id(consecutivo_ot)
        if not orden_actual_dict:
            raise DomainException(
                f"Orden de trabajo con consecutivo {consecutivo_ot} no encontrada",
                HTTP_404_NOT_FOUND
            )

        orden_actual = self.__parse_custom__(orden_actual_dict, VwOrdenesTrabajoCompleta)

        # Validar garantía si se intenta cambiar a estado 6 (Garantía)
        if contract.cod_ot_est_ot == 6:
            orden_anterior_dict = await self.repository.obtener_orden_anterior(
                orden_actual.placa_mot,
                consecutivo_ot
            )

            if not orden_anterior_dict:
                raise DomainException(
                    f"No se puede cambiar a estado Garantía. Esta moto no tiene órdenes anteriores entregadas",
                    HTTP_400_BAD_REQUEST
                )

            # Convertir a modelo Pydantic
            orden_anterior = self.__parse_custom__(orden_anterior_dict, OrdenAnteriorModelo)

            if orden_anterior.fecha_fin_garantia_ot:
                if orden_anterior.fecha_fin_garantia_ot < date.today():
                    raise DomainException(
                        f"No se puede cambiar a estado Garantía. La garantía de la orden anterior venció el {orden_anterior.fecha_fin_garantia_ot.strftime('%d/%m/%Y')}",
                        HTTP_400_BAD_REQUEST
                    )

        # Actualizar estado
        await self.repository.actualizar_estado(consecutivo_ot, contract.cod_ot_est_ot)

        return await self.obtener_orden_por_id(consecutivo_ot)

    async def entregar_orden(
        self,
        consecutivo_ot: int,
        contract: EntregarOrdenContract
    ) -> OrdenTrabajoResponseContract:
        """Marca una orden como entregada"""
        # Verificar que la orden existe
        orden_dict = await self.repository.obtener_orden_por_id(consecutivo_ot)
        if not orden_dict:
            raise DomainException(
                f"Orden de trabajo con consecutivo {consecutivo_ot} no encontrada",
                HTTP_404_NOT_FOUND
            )

        orden_modelo = self.__parse_custom__(orden_dict, VwOrdenesTrabajoCompleta)

        # Validar que el estado sea "Finalizada" (3)
        if orden_modelo.cod_ot_est_ot != 3:
            raise DomainException(
                f"La orden debe estar en estado 'Finalizada' para poder entregarla. Estado actual: {orden_modelo.estado_ot}",
                HTTP_400_BAD_REQUEST
            )

        # Calcular fecha fin de garantia (30 dias despues de la entrega)
        fecha_entrega = date.today()
        fecha_fin_garantia = fecha_entrega + timedelta(days=30)

        # Registrar entrega
        await self.repository.registrar_entrega(
            consecutivo_ot=consecutivo_ot,
            fecha_entrega=fecha_entrega,
            km_salida=contract.kilometreje_salida_ot,
            fecha_fin_garantia=fecha_fin_garantia
        )

        return await self.obtener_orden_por_id(consecutivo_ot)

    async def agregar_producto(
        self,
        consecutivo_ot: int,
        detalle_contract: DetalleOrdenTrabajoContract,
        documento_usu: str
    ) -> OrdenTrabajoResponseContract:
        """Agrega un producto a una orden de trabajo existente"""
        # Verificar que la orden existe
        if not await self.repository.existe_orden(consecutivo_ot):
            raise DomainException(
                f"Orden de trabajo con consecutivo {consecutivo_ot} no encontrada",
                HTTP_404_NOT_FOUND
            )

        # Verificar que el producto existe
        producto_dict = await self.producto_repository.get_by_id(detalle_contract.cod_pro_deto)
        if not producto_dict:
            raise DomainException(
                f"Producto con codigo {detalle_contract.cod_pro_deto} no encontrado",
                HTTP_404_NOT_FOUND
            )

        # Parsear a modelo Pydantic para tipado estático
        producto = self.__parse_custom__(producto_dict, ProductoModelo)

        # Validar stock disponible SOLO si la cantidad es positiva (se factura)
        if detalle_contract.cantidad_deto > 0:
            if producto.stock_pro < detalle_contract.cantidad_deto:
                raise DomainException(
                    f"Stock insuficiente. Disponible: {producto.stock_pro}, Solicitado: {detalle_contract.cantidad_deto}",
                    HTTP_400_BAD_REQUEST
                )

        # Verificar si el producto ya existe en la orden
        if await self.detalle_repository.existe_detalle(consecutivo_ot, detalle_contract.cod_pro_deto):
            raise DomainException(
                f"El producto {producto.nombre_pro} ya existe en esta orden",
                HTTP_400_BAD_REQUEST
            )

        # Usar valor unitario del producto si no se proporciona
        valor_unitario = detalle_contract.valor_unitario_deto
        if not valor_unitario:
            valor_unitario = producto.precio_pro

        # Crear detalle
        await self.detalle_repository.crear_detalle(
            consecutivo_ot=consecutivo_ot,
            cod_pro=detalle_contract.cod_pro_deto,
            cantidad=detalle_contract.cantidad_deto,
            valor_unitario=valor_unitario,
            documento_usu=documento_usu
        )

        # Actualizar stock según el signo de la cantidad
        # IMPORTANTE: Productos NO facturables (cantidad negativa) NO afectan el stock
        if detalle_contract.cantidad_deto > 0:
            # Producto SE FACTURA: restar del stock
            nuevo_stock = producto.stock_pro - detalle_contract.cantidad_deto
            await self.producto_repository.actualizar_stock(detalle_contract.cod_pro_deto, nuevo_stock)
        # Si cantidad < 0 (NO se factura): NO hacer nada con el stock

        return await self.obtener_orden_por_id(consecutivo_ot)

    async def actualizar_cantidad_producto(
        self,
        consecutivo_ot: int,
        cod_pro: int,
        detalle_contract
    ) -> OrdenTrabajoResponseContract:
        """Actualiza la cantidad de un producto en una orden de trabajo"""
        # Verificar que la orden existe
        orden = await self.repository.obtener_orden_por_id(consecutivo_ot)
        if not orden:
            raise DomainException(
                f"Orden de trabajo {consecutivo_ot} no encontrada",
                HTTP_404_NOT_FOUND
            )

        # Verificar que el producto existe en la orden
        detalle_actual_dict = await self.detalle_repository.obtener_detalle(consecutivo_ot, cod_pro)
        if not detalle_actual_dict:
            raise DomainException(
                f"Producto {cod_pro} no encontrado en la orden {consecutivo_ot}",
                HTTP_404_NOT_FOUND
            )

        # Parsear a modelo Pydantic para tipado estático
        detalle_actual = self.__parse_custom__(detalle_actual_dict, DetalleOrdenTrabajoModelo)

        # Obtener información del producto
        producto_dict = await self.producto_repository.get_by_id(cod_pro)
        if not producto_dict:
            raise DomainException(
                f"Producto {cod_pro} no encontrado",
                HTTP_404_NOT_FOUND
            )

        # Parsear a modelo Pydantic para tipado estático
        producto = self.__parse_custom__(producto_dict, ProductoModelo)

        # Obtener cantidad anterior y nueva
        cantidad_anterior = detalle_actual.cantidad_deto
        cantidad_nueva = detalle_contract.cantidad_deto

        # IMPORTANTE: Productos NO facturables (cantidad negativa) NO afectan el stock
        # Solo calculamos el delta (cambio neto) considerando esto

        # Calcular efecto de la cantidad anterior en el stock
        if cantidad_anterior > 0:
            efecto_anterior = -cantidad_anterior  # Se restó del stock
        else:
            efecto_anterior = 0  # NO afectó el stock

        # Calcular efecto de la cantidad nueva en el stock
        if cantidad_nueva > 0:
            efecto_nuevo = -cantidad_nueva  # Se restará del stock
        else:
            efecto_nuevo = 0  # NO afectará el stock

        # Calcular el cambio neto en el stock
        delta_stock = efecto_nuevo - efecto_anterior

        # Validar stock disponible si es necesario
        if delta_stock < 0:  # Si vamos a restar stock
            stock_resultante = producto.stock_pro + delta_stock
            if stock_resultante < 0:
                raise DomainException(
                    f"Stock insuficiente. Disponible: {producto.stock_pro}, Requerido: {abs(delta_stock)}",
                    HTTP_400_BAD_REQUEST
                )

        # Actualizar cantidad en el detalle
        await self.detalle_repository.actualizar_cantidad_detalle(
            consecutivo_ot,
            cod_pro,
            cantidad_nueva
        )

        # Actualizar stock del producto solo si hay cambio neto
        if delta_stock != 0:
            nuevo_stock = producto.stock_pro + delta_stock
            await self.producto_repository.actualizar_stock(cod_pro, nuevo_stock)

        return await self.obtener_orden_por_id(consecutivo_ot)

    async def eliminar_producto(
        self,
        consecutivo_ot: int,
        cod_pro: int
    ) -> OrdenTrabajoResponseContract:
        """Elimina un producto de una orden de trabajo"""
        # Verificar que el detalle existe
        detalle_dict = await self.detalle_repository.obtener_detalle(consecutivo_ot, cod_pro)
        if not detalle_dict:
            raise DomainException(
                f"El producto no existe en esta orden",
                HTTP_404_NOT_FOUND
            )

        # Parsear a modelo Pydantic para tipado estático
        detalle = self.__parse_custom__(detalle_dict, DetalleOrdenTrabajoModelo)

        # Obtener cantidad para revertir el efecto en el stock
        cantidad = detalle.cantidad_deto

        # Eliminar detalle
        await self.detalle_repository.eliminar_detalle(consecutivo_ot, cod_pro)

        # Revertir el efecto en el stock
        # IMPORTANTE: Solo revertir si la cantidad era positiva (se facturaba)
        if cantidad > 0:
            producto_dict = await self.producto_repository.get_by_id(cod_pro)
            if producto_dict:
                producto = self.__parse_custom__(producto_dict, ProductoModelo)
                # Se había restado del stock, devolverlo
                nuevo_stock = producto.stock_pro + cantidad
                await self.producto_repository.actualizar_stock(cod_pro, nuevo_stock)
        # Si cantidad < 0 (NO se facturaba): NO hacer nada con el stock

        return await self.obtener_orden_por_id(consecutivo_ot)

    async def obtener_ordenes_pendientes(self) -> List[dict]:
        """Obtiene todas las ordenes pendientes de entrega"""
        ordenes_dict = await self.repository.obtener_ordenes_pendientes()
        return ordenes_dict

    async def obtener_ordenes_por_cliente(self, documento_cli: str) -> List[OrdenTrabajoResumenContract]:
        """Obtiene todas las ordenes de un cliente"""
        ordenes_dict = await self.repository.obtener_ordenes_por_cliente(documento_cli)
        ordenes_modelos = self.__parse_all_custom__(ordenes_dict, VwOrdenesTrabajoCompleta)

        resultado = []
        for orden in ordenes_modelos:
            resumen_dict = await self.repository.obtener_resumen_financiero(orden.consecutivo_ot)
            total_ot = 0.0
            if resumen_dict:
                resumen_modelo = self.__parse_custom__(resumen_dict, VwResumenFinancieroOt)
                total_ot = float(resumen_modelo.total_ot or 0.0)

            resultado.append(OrdenTrabajoResumenContract(
                consecutivo_ot=orden.consecutivo_ot,
                fecha_elaboracion_ot=orden.fecha_elaboracion_ot,
                fecha_entrega_ot=orden.fecha_entrega_ot,
                placa_mot=orden.placa_mot,
                nombre_completo_cliente=orden.nombre_completo_cliente,
                telefono_cli=orden.telefono_cli,
                estado_ot=orden.estado_ot,
                mecanico=orden.mecanico,
                total_ot=total_ot
            ))

        return resultado

    async def obtener_estados(self) -> List[OtEstadoResponseContract]:
        """Obtiene todos los estados de ordenes de trabajo"""
        estados_dict = await self.estado_repository.obtener_todos_estados()
        estados_modelos = self.__parse_all_custom__(estados_dict, OtEstadoModelo)

        return [
            OtEstadoResponseContract(
                cod_ot_est=estado.cod_ot_est,
                nombre_ot_est=estado.nombre_ot_est
            )
            for estado in estados_modelos
        ]

    async def obtener_ordenes_por_moto(self, placa_mot: str) -> List[OrdenTrabajoResumenContract]:
        """Obtiene todas las ordenes de una moto"""
        ordenes_dict = await self.repository.obtener_ordenes_por_moto(placa_mot)
        ordenes_modelos = self.__parse_all_custom__(ordenes_dict, VwOrdenesTrabajoCompleta)

        resultado = []
        for orden in ordenes_modelos:
            resumen_dict = await self.repository.obtener_resumen_financiero(orden.consecutivo_ot)
            total_ot = 0.0
            if resumen_dict:
                resumen_modelo = self.__parse_custom__(resumen_dict, VwResumenFinancieroOt)
                total_ot = float(resumen_modelo.total_ot or 0.0)

            resultado.append(OrdenTrabajoResumenContract(
                consecutivo_ot=orden.consecutivo_ot,
                fecha_elaboracion_ot=orden.fecha_elaboracion_ot,
                fecha_entrega_ot=orden.fecha_entrega_ot,
                placa_mot=orden.placa_mot,
                nombre_completo_cliente=orden.nombre_completo_cliente,
                telefono_cli=orden.telefono_cli,
                estado_ot=orden.estado_ot,
                mecanico=orden.mecanico,
                total_ot=total_ot
            ))

        return resultado

    async def obtener_estados(self) -> List[OtEstadoResponseContract]:
        """Obtiene todos los estados de ordenes de trabajo"""
        estados_dict = await self.estado_repository.obtener_todos_estados()
        estados_modelos = self.__parse_all_custom__(estados_dict, OtEstadoModelo)

        return [
            OtEstadoResponseContract(
                cod_ot_est=estado.cod_ot_est,
                nombre_ot_est=estado.nombre_ot_est
            )
            for estado in estados_modelos
        ]

    async def generar_factura_pos(self, consecutivo_ot: int) -> str:
        """
        Genera una factura en formato POS (ticket 80mm) para una orden entregada.
        Retorna la ruta del archivo PDF generado.

        Args:
            consecutivo_ot: Consecutivo de la orden de trabajo

        Returns:
            str: Ruta del archivo PDF generado

        Raises:
            DomainException: Si la orden no existe, no está entregada o no tiene productos facturables
        """
        import os
        from infrastructure.utils.factura_pos_generator import FacturaPOSPDFGenerator

        # Obtener la orden de trabajo
        orden = await self.obtener_orden_por_id(consecutivo_ot)

        # Validar que el estado sea "Entregada"
        if orden.estado_ot != "Entregada":
            raise DomainException(
                f"Solo se pueden generar facturas para órdenes con estado 'Entregada'. Estado actual: {orden.estado_ot}",
                HTTP_400_BAD_REQUEST
            )

        # Actualizar fechas si están vacías
        hoy = date.today()
        update_dict = {}

        # Si fecha_entrega_ot está vacía, usar hoy
        if not orden.fecha_entrega_ot:
            update_dict['fecha_entrega_ot'] = hoy

        # Si fecha_fin_garantia_ot está vacía, calcular como hoy + 30 días
        if not orden.fecha_fin_garantia_ot:
            update_dict['fecha_fin_garantia_ot'] = hoy + timedelta(days=30)

        # Actualizar la orden si es necesario
        if update_dict:
            from domain.contracts.ordenes_trabajo.orden_trabajo_contract import OrdenTrabajoUpdateContract
            update_data = OrdenTrabajoUpdateContract(**update_dict)
            orden = await self.actualizar_orden(consecutivo_ot, update_data)

        # Validar que haya productos facturables (cantidad > 0)
        productos_facturables = [d for d in orden.detalles if d.cantidad_deto > 0]
        if not productos_facturables:
            raise DomainException(
                "No hay productos facturables en esta orden (todos tienen cantidad negativa)",
                HTTP_400_BAD_REQUEST
            )

        # Generar el PDF en formato POS
        pdf_generator = FacturaPOSPDFGenerator()
        nombre_archivo = f"factura_{consecutivo_ot}.pdf"
        ruta_pdf = os.path.join("pdfs", "facturas", nombre_archivo)

        pdf_generator.generar_factura(orden, ruta_pdf)

        return ruta_pdf
