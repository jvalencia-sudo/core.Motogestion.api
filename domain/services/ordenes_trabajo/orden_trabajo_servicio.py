import logging
from typing import Dict, List
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
from infrastructure.utils.placa import normalizar_placa
from repository.ordenes_trabajo.orden_trabajo_repositorio import OrdenTrabajoRepositorio
from repository.ordenes_trabajo.detalle_orden_trabajo_repositorio import DetalleOrdenTrabajoRepositorio
from repository.ordenes_trabajo.ot_estado_repositorio import OtEstadoRepositorio
from repository.motos.moto_repositorio import MotoRepositorio
from repository.productos.producto_repositorio import ProductoRepositorio
from repository.productos.paquete_componente_repositorio import PaqueteComponenteRepositorio
from repository.inventario.inventario_repositorio import InventarioRepositorio
from repository.talleres.taller_repositorio import TallerRepositorio
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.fecha_bogota import hoy_bogota
from infrastructure.utils.marca_taller import ConfigMarcaTaller
from infrastructure.utils.tenant_context import get_tenant
from domain.services.ordenes_trabajo.validaciones_entrega import validar_saldo_para_entrega

logger = logging.getLogger(__name__)


class OrdenTrabajoServicio(BaseService[OrdenTrabajoModelo, OrdenTrabajoRepositorio]):
    def __init__(self):
        super().__init__(OrdenTrabajoRepositorio())
        self.detalle_repository = DetalleOrdenTrabajoRepositorio()
        self.estado_repository = OtEstadoRepositorio()
        self.moto_repository = MotoRepositorio()
        self.producto_repository = ProductoRepositorio()
        self.paquete_repository = PaqueteComponenteRepositorio()
        self.inventario_repository = InventarioRepositorio()
        self.taller_repository = TallerRepositorio()

    async def _config_comprobante_taller(self) -> dict:
        """nombre/dirección/teléfono y texto_pie_comprobante del taller actual
        (tabla talleres no tiene RLS -- el tenant se toma del contexto de la
        petición)."""
        cod_taller = get_tenant()
        config = await self.taller_repository.obtener_config_comprobante(cod_taller) if cod_taller else None
        return config or {}

    async def _config_marca_taller(self) -> ConfigMarcaTaller:
        """F1-09: personalización visual de la orden (logo, color,
        condiciones, pie, interruptores) del taller actual."""
        from domain.services.talleres.taller_servicio import TallerServicio

        cod_taller = get_tenant()
        if not cod_taller:
            return ConfigMarcaTaller()
        return await TallerServicio().config_marca(cod_taller)

    async def generar_pdf_orden(self, consecutivo_ot: int) -> bytes:
        """Genera el PDF (carta) de la orden, con la personalización visual
        del taller (F1-09). La validación de negocio (existencia, estado
        válido, tiene ítems) vive en obtener_orden_para_documento."""
        from infrastructure.utils.orden_trabajo_html_pdf import generar_pdf_orden_html

        orden = await self.obtener_orden_para_documento(consecutivo_ot)
        marca = await self._config_marca_taller()
        return generar_pdf_orden_html(orden, marca)

    def __parse__(self, record: Dict) -> OrdenTrabajoModelo:
        return OrdenTrabajoModelo.model_validate(record)

    ESTADOS_QUE_REQUIEREN_ITEMS = (3, 4)  # Completada, Entregada

    async def _validar_items_para_estado(self, consecutivo_ot: int, nuevo_estado: int) -> None:
        """F1-01: una orden no puede pasar a Completada ni Entregada sin al
        menos un ítem. Se valida en todos los caminos que pueden fijar el
        estado (crear, actualizar, cambiar-estado), no solo en entregar_orden."""
        if nuevo_estado not in self.ESTADOS_QUE_REQUIEREN_ITEMS:
            return
        detalles = await self.detalle_repository.obtener_detalles_por_orden(consecutivo_ot)
        if not detalles:
            raise DomainException(
                "La orden debe tener al menos un producto o servicio para "
                "marcarla como Completada o Entregada",
                HTTP_400_BAD_REQUEST
            )

    async def _validar_stock(self, producto: ProductoModelo, cantidad) -> None:
        """Valida stock disponible antes de insertar cualquier detalle de tipo BIEN,
        se cobre o no (F1-06: una cortesía descuenta stock igual que una venta, así
        que también debe validarse contra el disponible).
        - BIEN: valida su propio stock.
        - PAQUETE: valida el stock de cada componente BIEN (cantidad_comp * cantidad).
        - SERVICIO: no valida (no maneja stock).
        El descuento real lo hace el trigger de la BD.
        """
        if producto.tipo_pro == "BIEN":
            if (producto.stock_pro or 0) < cantidad:
                raise DomainException(
                    f"Stock insuficiente para el producto {producto.nombre_pro}. "
                    f"Disponible: {producto.stock_pro}, Solicitado: {cantidad}",
                    HTTP_400_BAD_REQUEST
                )
        elif producto.tipo_pro == "PAQUETE":
            componentes = await self.paquete_repository.listar_por_paquete(producto.cod_pro)
            for c in componentes:
                if c.get("TIPO_PRO") == "BIEN":
                    requerido = c.get("CANTIDAD_COMP") * cantidad
                    disponible = c.get("STOCK_PRO") or 0
                    if disponible < requerido:
                        raise DomainException(
                            f"Stock insuficiente para el componente {c.get('NOMBRE_PRO')} "
                            f"del paquete {producto.nombre_pro}. Disponible: {disponible}, "
                            f"Requerido: {requerido}",
                            HTTP_400_BAD_REQUEST
                        )

    async def _validar_orden_editable(self, consecutivo_ot: int) -> None:
        """F1-05: una orden Entregada o Anulada no admite más cambios de
        ítems -- en ambas el stock ya quedó resuelto (entregado o devuelto)."""
        orden_dict = await self.repository.obtener_orden_por_id(consecutivo_ot)
        if not orden_dict:
            raise DomainException(
                f"Orden de trabajo con consecutivo {consecutivo_ot} no encontrada",
                HTTP_404_NOT_FOUND
            )
        if orden_dict.get("COD_OT_EST_OT") in (4, 5):
            raise DomainException(
                "No se pueden modificar los productos de una orden Entregada o Anulada",
                HTTP_400_BAD_REQUEST
            )

    async def anular_orden(
        self, consecutivo_ot: int, motivo: str, documento_usu: str
    ) -> OrdenTrabajoResponseContract:
        """F1-05: anula una orden completa (motivo obligatorio). Devuelve al
        inventario los bienes de la orden con movimientos ENTRADA -- sin
        borrar ningún detalle, que queda como historial -- y en la misma
        transacción deja la orden en estado Anulada con quién/cuándo/por
        qué. SERVICIO no maneja stock; PAQUETE se expande en sus
        componentes BIEN, igual que el trigger de descuento al crear."""
        orden_dict = await self.repository.obtener_orden_por_id(consecutivo_ot)
        if not orden_dict:
            raise DomainException(
                f"Orden de trabajo con consecutivo {consecutivo_ot} no encontrada",
                HTTP_404_NOT_FOUND
            )
        if orden_dict.get("COD_OT_EST_OT") == 5:
            raise DomainException("La orden ya está anulada", HTTP_400_BAD_REQUEST)

        detalles_dict = await self.detalle_repository.obtener_detalles_por_orden(consecutivo_ot)

        # cod_pro -> cantidad total de BIEN a devolver. Se acumula primero
        # (en vez de leer/escribir stock por línea) para que un mismo BIEN
        # que aparezca directo en una línea y como componente de un PAQUETE
        # en otra reciba un único movimiento consistente.
        a_devolver: Dict[int, object] = {}
        for det in detalles_dict:
            cod_pro = det.get("COD_PRO_DETO")
            cantidad = det.get("CANTIDAD_DETO")
            producto_dict = await self.producto_repository.get_by_id(cod_pro)
            if not producto_dict:
                continue
            tipo_pro = producto_dict.get("TIPO_PRO")
            if tipo_pro == "BIEN":
                a_devolver[cod_pro] = a_devolver.get(cod_pro, 0) + cantidad
            elif tipo_pro == "PAQUETE":
                componentes = await self.paquete_repository.listar_por_paquete(cod_pro)
                for c in componentes:
                    if c.get("TIPO_PRO") == "BIEN":
                        cod_comp = c.get("COD_PRO_COMP")
                        requerido = c.get("CANTIDAD_COMP") * cantidad
                        a_devolver[cod_comp] = a_devolver.get(cod_comp, 0) + requerido
            # SERVICIO: no maneja stock.

        motivo_mov = f"Anulación OT #{consecutivo_ot}"
        statements: List = []
        for cod_pro, cantidad in a_devolver.items():
            stock_ant = await self.producto_repository.obtener_stock(cod_pro) or 0
            stock_nue = stock_ant + cantidad
            statements.append(self.producto_repository.statement_actualizar_stock(cod_pro, stock_nue))
            statements.append(self.inventario_repository.statement_insertar_movimiento(
                cod_pro, "ENTRADA", cantidad, stock_ant, stock_nue, motivo_mov, documento_usu
            ))

        statements.append(self.repository.statement_anular(consecutivo_ot, motivo, documento_usu))

        await self.repository.execute_transaction(statements)

        return await self.obtener_orden_por_id(consecutivo_ot)

    async def obtener_todas_ordenes(self) -> List[OrdenTrabajoResumenContract]:
        """Obtiene todas las ordenes de trabajo con informacion resumida"""
        ordenes_dict = await self.repository.obtener_ordenes_completas()
        ordenes_modelos = self.__parse_all_custom__(ordenes_dict, VwOrdenesTrabajoCompleta)

        resultado = []
        for orden in ordenes_modelos:
            # Obtener resumen financiero si existe
            resumen_dict = await self.repository.obtener_resumen_financiero(orden.consecutivo_ot)
            total_ot = 0.0
            saldo_ot = 0.0
            if resumen_dict:
                resumen_modelo = self.__parse_custom__(resumen_dict, VwResumenFinancieroOt)
                total_ot = float(resumen_modelo.total_ot or 0.0)
                saldo_ot = float(resumen_modelo.saldo_ot or 0.0)

            resultado.append(OrdenTrabajoResumenContract(
                consecutivo_ot=orden.consecutivo_ot,
                fecha_elaboracion_ot=orden.fecha_elaboracion_ot,
                fecha_entrega_ot=orden.fecha_entrega_ot,
                placa_mot=orden.placa_mot,
                nombre_completo_cliente=orden.nombre_completo_cliente,
                telefono_cli=orden.telefono_cli,
                estado_ot=orden.estado_ot,
                cod_ot_est_ot=orden.cod_ot_est_ot,
                mecanico=orden.mecanico,
                kilometraje_ingreso_ot=orden.kilometraje_ingreso_ot,
                trabajos=orden.trabajos,
                total_ot=total_ot,
                saldo_ot=saldo_ot
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
                cobrar_deto=det.cobrar_deto,
                motivo_no_cobro_deto=det.motivo_no_cobro_deto,
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
        total_pagado = 0.0
        saldo_ot = 0.0

        if resumen_dict:
            resumen_modelo = self.__parse_custom__(resumen_dict, VwResumenFinancieroOt)
            total_items = int(resumen_modelo.total_items or 0)
            subtotal_productos = float(resumen_modelo.subtotal_productos or 0.0)
            total_impuestos = float(resumen_modelo.total_impuestos or 0.0)
            total_ot = float(resumen_modelo.total_ot or 0.0)
            total_pagado = float(resumen_modelo.total_pagado or 0.0)
            saldo_ot = float(resumen_modelo.saldo_ot or 0.0)

        return OrdenTrabajoResponseContract(
            consecutivo_ot=orden_modelo.consecutivo_ot,
            fecha_elaboracion_ot=orden_modelo.fecha_elaboracion_ot,
            fecha_entrega_ot=orden_modelo.fecha_entrega_ot,
            kilometraje_ingreso_ot=orden_modelo.kilometraje_ingreso_ot,
            kilometraje_salida_ot=orden_modelo.kilometraje_salida_ot,
            observacion_cli_ot=orden_modelo.observacion_cli_ot,
            observacion_ot=orden_modelo.observacion_ot,
            fecha_fin_garantia_ot=orden_modelo.fecha_fin_garantia_ot,
            motivo_anulacion_ot=orden_modelo.motivo_anulacion_ot,
            fecha_anulacion_ot=orden_modelo.fecha_anulacion_ot,
            documento_usu_anulacion_ot=orden_modelo.documento_usu_anulacion_ot,
            placa_mot=orden_modelo.placa_mot,
            modelo_mot=orden_modelo.modelo_mot,
            color_mot=orden_modelo.color_mot,
            cilindraje_mot=orden_modelo.cilindraje_mot,
            marca_moto=orden_modelo.marca_moto,
            ciudad_placa_mot=orden_modelo.ciudad_placa_mot,
            documento_cli=orden_modelo.documento_cli,
            tipo_documento_cli=orden_modelo.tipo_documento_cli,
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
            total_ot=total_ot,
            total_pagado=total_pagado,
            saldo_ot=saldo_ot
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
                    "No se puede crear una orden con estado Garantía. Esta moto no tiene órdenes anteriores entregadas",
                    HTTP_400_BAD_REQUEST
                )

            # Convertir a modelo Pydantic
            orden_anterior = self.__parse_custom__(orden_anterior_dict, OrdenAnteriorModelo)

            if orden_anterior.fecha_fin_garantia_ot:
                if orden_anterior.fecha_fin_garantia_ot < hoy_bogota():
                    raise DomainException(
                        f"No se puede crear orden con estado Garantía. La garantía de la orden anterior venció el {orden_anterior.fecha_fin_garantia_ot.strftime('%d/%m/%Y')}",
                        HTTP_400_BAD_REQUEST
                    )

        # F1-01: no se puede crear directo en Completada/Entregada sin ítems.
        if estado_inicial in self.ESTADOS_QUE_REQUIEREN_ITEMS and not contract.detalles:
            raise DomainException(
                "La orden debe tener al menos un producto o servicio para "
                "crearla como Completada o Entregada",
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

            # Validar stock (type-aware): BIEN valida su stock, PAQUETE el de sus
            # componentes BIEN, SERVICIO no valida. El descuento lo hace el trigger.
            await self._validar_stock(producto, detalle.cantidad_deto)

        # Crear el modelo de orden de trabajo. El recepcionista usa el valor ya
        # resuelto por el endpoint (contrato o, por defecto, el usuario
        # autenticado) -- contract.documento_usu_rp_ot puede venir en None.
        orden_modelo = OrdenTrabajoModelo(
            fecha_elaboracion_ot=hoy_bogota(),
            fecha_entrega_ot=contract.fecha_entrega_ot,
            placa_mot_ot=contract.placa_mot_ot,
            kilometraje_ingreso_ot=contract.kilometraje_ingreso_ot,
            documento_usu_rp_ot=documento_usu_creador,
            documento_usu_mc_ot=contract.documento_usu_mc_ot,
            observacion_cli_ot=contract.observacion_cli_ot,
            observacion_ot=contract.observacion_ot,
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

            # Crear detalle. El stock lo maneja el trigger de la BD (tg_actualizar_stock),
            # que descuenta según el tipo de producto (BIEN descuenta, SERVICIO no, PAQUETE
            # explota componentes) y deja el movimiento en el kardex. Aquí NO tocamos stock.
            await self.detalle_repository.crear_detalle(
                consecutivo_ot=consecutivo_ot,
                cod_pro=detalle.cod_pro_deto,
                cantidad=detalle.cantidad_deto,
                valor_unitario=valor_unitario,
                documento_usu=documento_usu_creador,
                cobrar=detalle.cobrar_deto,
                motivo_no_cobro=detalle.motivo_no_cobro_deto
            )

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
                    "No se puede cambiar a estado Garantía. Esta moto no tiene órdenes anteriores entregadas",
                    HTTP_400_BAD_REQUEST
                )

            # Convertir a modelo Pydantic
            orden_anterior = self.__parse_custom__(orden_anterior_dict, OrdenAnteriorModelo)

            if orden_anterior.fecha_fin_garantia_ot:
                if orden_anterior.fecha_fin_garantia_ot < hoy_bogota():
                    raise DomainException(
                        f"No se puede cambiar a estado Garantía. La garantía de la orden anterior venció el {orden_anterior.fecha_fin_garantia_ot.strftime('%d/%m/%Y')}",
                        HTTP_400_BAD_REQUEST
                    )

        # F1-01: no se puede pasar a Completada/Entregada sin ítems.
        if contract.cod_ot_est_ot is not None:
            await self._validar_items_para_estado(consecutivo_ot, contract.cod_ot_est_ot)

        # Crear modelo para actualizar solo con los campos proporcionados
        datos_actualizacion = {}
        if contract.fecha_entrega_ot is not None:
            datos_actualizacion['FECHA_ENTREGA_OT'] = contract.fecha_entrega_ot
        if contract.observacion_ot is not None:
            datos_actualizacion['OBSERVACION_OT'] = contract.observacion_ot
        if contract.cod_ot_est_ot is not None:
            datos_actualizacion['COD_OT_EST_OT'] = contract.cod_ot_est_ot
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
                    "No se puede cambiar a estado Garantía. Esta moto no tiene órdenes anteriores entregadas",
                    HTTP_400_BAD_REQUEST
                )

            # Convertir a modelo Pydantic
            orden_anterior = self.__parse_custom__(orden_anterior_dict, OrdenAnteriorModelo)

            if orden_anterior.fecha_fin_garantia_ot:
                if orden_anterior.fecha_fin_garantia_ot < hoy_bogota():
                    raise DomainException(
                        f"No se puede cambiar a estado Garantía. La garantía de la orden anterior venció el {orden_anterior.fecha_fin_garantia_ot.strftime('%d/%m/%Y')}",
                        HTTP_400_BAD_REQUEST
                    )

        # F1-01: no se puede pasar a Completada/Entregada sin ítems.
        await self._validar_items_para_estado(consecutivo_ot, contract.cod_ot_est_ot)

        # F1-07: si la orden queda con saldo pendiente, exige confirmar
        # "entregar a crédito" -- ver validaciones_entrega.py (compartida con
        # TableroServicio.cambiar_estado, que es hoy el único camino que la UI
        # real usa para mover una orden a Entregada).
        if contract.cod_ot_est_ot == 4:
            await validar_saldo_para_entrega(consecutivo_ot, contract.confirmar_credito)

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

        # F1-11: el kilometraje de salida no puede ser menor al de ingreso.
        if (
            contract.kilometraje_salida_ot is not None
            and contract.kilometraje_salida_ot < orden_modelo.kilometraje_ingreso_ot
        ):
            raise DomainException(
                f"El kilometraje de salida ({contract.kilometraje_salida_ot}) no puede ser "
                f"menor al de ingreso ({orden_modelo.kilometraje_ingreso_ot})",
                HTTP_400_BAD_REQUEST
            )

        await validar_saldo_para_entrega(consecutivo_ot, contract.confirmar_credito)

        # F1-04: fecha_fin_garantia_ot ya no se calcula acá -- el trigger
        # fn_calc_fecha_garantia la fija con el MAX(dias_garantia_pro) de los
        # ítems de la orden en cuanto este UPDATE deja cod_ot_est_ot = 4.
        fecha_entrega = hoy_bogota()

        # Registrar entrega
        await self.repository.registrar_entrega(
            consecutivo_ot=consecutivo_ot,
            fecha_entrega=fecha_entrega,
            km_salida=contract.kilometraje_salida_ot,
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

        # F1-05: no se pueden agregar productos a una orden Entregada o Anulada.
        await self._validar_orden_editable(consecutivo_ot)

        # Verificar que el producto existe
        producto_dict = await self.producto_repository.get_by_id(detalle_contract.cod_pro_deto)
        if not producto_dict:
            raise DomainException(
                f"Producto con codigo {detalle_contract.cod_pro_deto} no encontrado",
                HTTP_404_NOT_FOUND
            )

        # Parsear a modelo Pydantic para tipado estático
        producto = self.__parse_custom__(producto_dict, ProductoModelo)

        # Validar stock (type-aware: BIEN, PAQUETE→componentes, SERVICIO no aplica).
        await self._validar_stock(producto, detalle_contract.cantidad_deto)

        # Verificar duplicados solo para BIEN. La mano de obra (SERVICIO) y los
        # paquetes (PAQUETE) pueden agregarse en varias líneas dentro de la misma orden.
        if producto.tipo_pro == "BIEN" and await self.detalle_repository.existe_detalle(consecutivo_ot, detalle_contract.cod_pro_deto):
            raise DomainException(
                f"El producto {producto.nombre_pro} ya existe en esta orden",
                HTTP_400_BAD_REQUEST
            )

        # Usar valor unitario del producto si no se proporciona
        valor_unitario = detalle_contract.valor_unitario_deto
        if not valor_unitario:
            valor_unitario = producto.precio_pro

        # Crear detalle. El stock lo maneja el trigger de la BD (type-aware). No lo tocamos aquí.
        await self.detalle_repository.crear_detalle(
            consecutivo_ot=consecutivo_ot,
            cod_pro=detalle_contract.cod_pro_deto,
            cantidad=detalle_contract.cantidad_deto,
            valor_unitario=valor_unitario,
            documento_usu=documento_usu,
            cobrar=detalle_contract.cobrar_deto,
            motivo_no_cobro=detalle_contract.motivo_no_cobro_deto
        )

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

        # F1-05: no se puede editar la cantidad en una orden Entregada o Anulada.
        if orden.get("COD_OT_EST_OT") in (4, 5):
            raise DomainException(
                "No se pueden modificar los productos de una orden Entregada o Anulada",
                HTTP_400_BAD_REQUEST
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

        # Validación de stock solo para BIEN: comprobar que el aumento de consumo no
        # deje el stock negativo. El ajuste real de stock + kardex lo hace el trigger
        # de UPDATE (tg_ajustar_stock). F1-06: toda cantidad cuenta, se cobre o no.
        if producto.tipo_pro == "BIEN":
            delta_consumo = cantidad_nueva - cantidad_anterior  # > 0: consume más stock
            if delta_consumo > 0 and (producto.stock_pro or 0) < delta_consumo:
                raise DomainException(
                    f"Stock insuficiente. Disponible: {producto.stock_pro}, Requerido: {delta_consumo}",
                    HTTP_400_BAD_REQUEST
                )

        # Actualizar cantidad (y estado de cobro) en el detalle (el trigger ajusta stock + kardex).
        await self.detalle_repository.actualizar_cantidad_detalle(
            consecutivo_ot,
            cod_pro,
            cantidad_nueva,
            cobrar=detalle_contract.cobrar_deto,
            motivo_no_cobro=detalle_contract.motivo_no_cobro_deto
        )

        return await self.obtener_orden_por_id(consecutivo_ot)

    async def eliminar_producto(
        self,
        consecutivo_ot: int,
        cod_pro: int
    ) -> OrdenTrabajoResponseContract:
        """Elimina un producto de una orden de trabajo"""
        # F1-05: no se pueden quitar productos de una orden Entregada o Anulada.
        await self._validar_orden_editable(consecutivo_ot)

        # Verificar que el detalle existe
        detalle_dict = await self.detalle_repository.obtener_detalle(consecutivo_ot, cod_pro)
        if not detalle_dict:
            raise DomainException(
                "El producto no existe en esta orden",
                HTTP_404_NOT_FOUND
            )

        # Eliminar detalle. El trigger de DELETE (tg_revertir_stock) devuelve el stock
        # y deja el movimiento de reversa en el kardex (solo para BIEN facturable).
        await self.detalle_repository.eliminar_detalle(consecutivo_ot, cod_pro)

        return await self.obtener_orden_por_id(consecutivo_ot)

    async def obtener_orden_para_documento(self, consecutivo_ot: int):
        """Obtiene una OT validando que sea apta para generar su documento/PDF.
        Reglas de negocio (viven en el servicio, no en el controlador):
        estado válido y al menos un ítem."""
        orden = await self.obtener_orden_por_id(consecutivo_ot)  # lanza 404 si no existe
        estados_validos = ["En Proceso", "Completada", "Entregada"]
        if orden.estado_ot not in estados_validos:
            raise DomainException(
                f"Solo se puede generar el documento para órdenes en estado "
                f"'En Proceso', 'Completada' o 'Entregada'. Estado actual: {orden.estado_ot}",
                HTTP_400_BAD_REQUEST,
            )
        if not orden.detalles or len(orden.detalles) == 0:
            raise DomainException(
                "La orden debe tener al menos un producto para generar el documento",
                HTTP_400_BAD_REQUEST,
            )
        return orden

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
            saldo_ot = 0.0
            if resumen_dict:
                resumen_modelo = self.__parse_custom__(resumen_dict, VwResumenFinancieroOt)
                total_ot = float(resumen_modelo.total_ot or 0.0)
                saldo_ot = float(resumen_modelo.saldo_ot or 0.0)

            resultado.append(OrdenTrabajoResumenContract(
                consecutivo_ot=orden.consecutivo_ot,
                fecha_elaboracion_ot=orden.fecha_elaboracion_ot,
                fecha_entrega_ot=orden.fecha_entrega_ot,
                placa_mot=orden.placa_mot,
                nombre_completo_cliente=orden.nombre_completo_cliente,
                telefono_cli=orden.telefono_cli,
                estado_ot=orden.estado_ot,
                cod_ot_est_ot=orden.cod_ot_est_ot,
                mecanico=orden.mecanico,
                kilometraje_ingreso_ot=orden.kilometraje_ingreso_ot,
                trabajos=orden.trabajos,
                total_ot=total_ot,
                saldo_ot=saldo_ot
            ))

        return resultado

    async def obtener_ordenes_por_moto(self, placa_mot: str) -> List[OrdenTrabajoResumenContract]:
        """Obtiene todas las ordenes de una moto"""
        placa_mot = normalizar_placa(placa_mot)
        ordenes_dict = await self.repository.obtener_ordenes_por_moto(placa_mot)
        ordenes_modelos = self.__parse_all_custom__(ordenes_dict, VwOrdenesTrabajoCompleta)

        resultado = []
        for orden in ordenes_modelos:
            resumen_dict = await self.repository.obtener_resumen_financiero(orden.consecutivo_ot)
            total_ot = 0.0
            saldo_ot = 0.0
            if resumen_dict:
                resumen_modelo = self.__parse_custom__(resumen_dict, VwResumenFinancieroOt)
                total_ot = float(resumen_modelo.total_ot or 0.0)
                saldo_ot = float(resumen_modelo.saldo_ot or 0.0)

            resultado.append(OrdenTrabajoResumenContract(
                consecutivo_ot=orden.consecutivo_ot,
                fecha_elaboracion_ot=orden.fecha_elaboracion_ot,
                fecha_entrega_ot=orden.fecha_entrega_ot,
                placa_mot=orden.placa_mot,
                nombre_completo_cliente=orden.nombre_completo_cliente,
                telefono_cli=orden.telefono_cli,
                estado_ot=orden.estado_ot,
                cod_ot_est_ot=orden.cod_ot_est_ot,
                mecanico=orden.mecanico,
                kilometraje_ingreso_ot=orden.kilometraje_ingreso_ot,
                trabajos=orden.trabajos,
                total_ot=total_ot,
                saldo_ot=saldo_ot
            ))

        return resultado

    async def generar_comprobante_servicio_pos(self, consecutivo_ot: int) -> bytes:
        """
        Genera un comprobante de servicio en formato POS (ticket 80mm) para una orden entregada.

        Args:
            consecutivo_ot: Consecutivo de la orden de trabajo

        Returns:
            bytes: Contenido del PDF generado

        Raises:
            DomainException: Si la orden no existe, no está entregada o no tiene productos facturables
        """
        from infrastructure.utils.comprobante_servicio_generator import ComprobanteServicioPDFGenerator

        # Obtener la orden de trabajo
        orden = await self.obtener_orden_por_id(consecutivo_ot)

        # Validar que el estado sea "Entregada"
        if orden.estado_ot != "Entregada":
            raise DomainException(
                f"Solo se pueden generar comprobantes para órdenes con estado 'Entregada'. Estado actual: {orden.estado_ot}",
                HTTP_400_BAD_REQUEST
            )

        # Actualizar fecha de entrega si está vacía (fecha_fin_garantia_ot ya
        # no se backfillea acá -- F1-04: NULL es una respuesta válida y final,
        # no un dato que falte, cuando ningún ítem de la orden da garantía).
        config_taller = await self._config_comprobante_taller()
        marca = await self._config_marca_taller()
        hoy = hoy_bogota()
        update_dict = {}

        if not orden.fecha_entrega_ot:
            update_dict['fecha_entrega_ot'] = hoy

        # Actualizar la orden si es necesario
        if update_dict:
            from domain.contracts.ordenes_trabajo.orden_trabajo_contract import OrdenTrabajoUpdateContract
            update_data = OrdenTrabajoUpdateContract(**update_dict)
            orden = await self.actualizar_orden(consecutivo_ot, update_data)

        # Validar que haya productos facturables (cobrar_deto=True)
        productos_facturables = [d for d in orden.detalles if d.cobrar_deto]
        if not productos_facturables:
            if not orden.detalles:
                raise DomainException(
                    "No se puede generar el comprobante porque la orden no tiene "
                    "productos ni servicios. Agrégalos editando la orden.",
                    HTTP_400_BAD_REQUEST
                )
            logger.info(
                "Comprobante rechazado: orden %s sin productos cobrables (%s ítems sin costo)",
                consecutivo_ot, len(orden.detalles)
            )
            raise DomainException(
                "No se puede generar el comprobante porque todos los productos de "
                "esta orden están marcados como sin costo. Si alguno se debe cobrar, "
                "edita la orden y actívalo en \"¿Se cobra?\".",
                HTTP_400_BAD_REQUEST
            )

        # Generar el PDF en formato POS, con los datos reales del taller en el
        # encabezado (antes decía siempre "MOTOGESTION" / un teléfono inventado,
        # sin importar de qué taller fuera la orden).
        pdf_generator = ComprobanteServicioPDFGenerator()
        return pdf_generator.generar_comprobante(
            orden,
            texto_pie_comprobante=config_taller.get("TEXTO_PIE_COMPROBANTE"),
            # F1-09: nombre_comercial_tal ya cae a nombre_tal por COALESCE en
            # obtener_config_marca si el taller no lo definió -- la tirilla
            # debe mostrar el mismo nombre que la carta, no el legal siempre.
            nombre_tal=marca.nombre_comercial or config_taller.get("NOMBRE_TAL"),
            direccion_tal=config_taller.get("DIRECCION_TAL"),
            telefono_tal=config_taller.get("TELEFONO_TAL"),
            logo_bytes=marca.logo_bytes,
            color_principal=marca.color_principal,
        )
