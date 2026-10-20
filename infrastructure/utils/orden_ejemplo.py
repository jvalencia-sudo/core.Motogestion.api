from datetime import date

from domain.contracts.ordenes_trabajo.detalle_orden_trabajo_contract import (
    DetalleOrdenTrabajoResponseContract,
)
from domain.contracts.ordenes_trabajo.orden_trabajo_contract import OrdenTrabajoResponseContract


def orden_de_ejemplo() -> OrdenTrabajoResponseContract:
    """Orden ficticia para la vista previa del PDF en 'Mi taller' (F1-09):
    no toca la base de datos, es solo para que el usuario vea cómo se ve su
    personalización antes de guardarla."""
    detalles = [
        DetalleOrdenTrabajoResponseContract(
            consecutivo_ot_deto=1,
            cod_pro_deto=1,
            nombre_pro="Cambio de aceite 20W-50",
            descripcion_pro="Full sintético",
            cantidad_deto=1,
            valor_unitario_deto=45000,
            cobrar_deto=True,
            subtotal=45000,
            usuario_confirmacion="Mecánico de ejemplo",
            estado_producto="Confirmado",
        ),
        DetalleOrdenTrabajoResponseContract(
            consecutivo_ot_deto=1,
            cod_pro_deto=2,
            nombre_pro="Mano de obra",
            descripcion_pro="Revisión general",
            cantidad_deto=1,
            valor_unitario_deto=20000,
            cobrar_deto=True,
            subtotal=20000,
            usuario_confirmacion="Mecánico de ejemplo",
            estado_producto="Confirmado",
        ),
    ]
    return OrdenTrabajoResponseContract(
        consecutivo_ot=1,
        fecha_elaboracion_ot=date.today(),
        kilometraje_ingreso_ot=12345,
        observacion_cli_ot="Hace ruido al frenar",
        observacion_ot="Se ajustaron pastillas y se cambió aceite",
        placa_mot="ABC123",
        modelo_mot=2022,
        color_mot="Rojo",
        cilindraje_mot=150,
        marca_moto="Yamaha",
        documento_cli="1000000000",
        nombre_completo_cliente="Cliente de ejemplo",
        telefono_cli="3000000000",
        correo_cli="cliente@ejemplo.com",
        documento_recepcionista="1000000001",
        recepcionista="Recepcionista de ejemplo",
        documento_mecanico="1000000002",
        mecanico="Mecánico de ejemplo",
        estado_ot="En Proceso",
        cod_ot_est_ot=2,
        detalles=detalles,
        total_items=2,
        subtotal_productos=65000,
        total_ot=65000,
        total_pagado=0,
        saldo_ot=65000,
    )
