"""F0-07: el PDF de la orden de trabajo (no solo el comprobante POS) tampoco
puede decir "factura" en ningún texto visible, y también debe llevar la nota
de que no es una factura de venta ni un documento equivalente."""
from datetime import date

from domain.contracts.ordenes_trabajo.detalle_orden_trabajo_contract import (
    DetalleOrdenTrabajoResponseContract,
)
from domain.contracts.ordenes_trabajo.orden_trabajo_contract import OrdenTrabajoResponseContract
from infrastructure.utils.pdf_generator import OrdenTrabajoPDFGenerator
from tests.pdf_test_utils import texto_visible_del_pdf

_NOTA_LEGAL = "factura de venta ni un documento equivalente"


def _orden_de_prueba() -> OrdenTrabajoResponseContract:
    return OrdenTrabajoResponseContract(
        consecutivo_ot=123,
        fecha_elaboracion_ot=date.today(),
        kilometraje_ingreso_ot=1000,
        placa_mot="ABC123",
        modelo_mot=2020,
        color_mot="Rojo",
        cilindraje_mot=150,
        marca_moto="Yamaha",
        documento_cli="1122334455",
        nombre_completo_cliente="Cliente de Prueba",
        telefono_cli="3001234567",
        correo_cli="cliente@example.com",
        direccion_cli="Calle 1 # 2-3",
        documento_recepcionista="1",
        recepcionista="Recepcionista",
        documento_mecanico="2",
        mecanico="Mecanico",
        estado_ot="Entregada",
        cod_ot_est_ot=1,
        detalles=[
            DetalleOrdenTrabajoResponseContract(
                consecutivo_ot_deto=1,
                cod_pro_deto=10,
                nombre_pro="Cambio de aceite",
                cantidad_deto=1,
                valor_unitario_deto=50000,
                subtotal=50000,
                usuario_confirmacion="1",
                estado_producto="Confirmado",
            )
        ],
    )


def test_texto_visible_del_pdf_no_dice_factura():
    pdf_bytes = OrdenTrabajoPDFGenerator().generar_pdf(_orden_de_prueba())

    texto = texto_visible_del_pdf(pdf_bytes).lower()
    texto_sin_nota = texto.replace(_NOTA_LEGAL, "")
    assert "factura" not in texto_sin_nota


def test_pdf_incluye_nota_legal():
    pdf_bytes = OrdenTrabajoPDFGenerator().generar_pdf(_orden_de_prueba())

    texto = texto_visible_del_pdf(pdf_bytes).lower()
    assert _NOTA_LEGAL in texto
