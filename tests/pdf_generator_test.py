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


# --- F0-10: texto de usuario sin escapar en los Paragraph de reportlab ---
#
# Paragraph interpreta un mini-lenguaje tipo XML. Antes del fix, un "<"/"&"
# suelto rompía el documento (SAXParseException) y una etiqueta <img
# src="..."/> hacía que reportlab intentara abrir ese archivo/URL como
# imagen -- lectura de archivos locales o SSRF, según el valor. Las
# comparaciones quitan los espacios: reportlab divide el texto en varios
# runs con kerning alrededor de "<"/">" y texto_visible_del_pdf los une con
# un espacio por cada uno, así que el texto EXTRAÍDO no queda pegado letra a
# letra aunque el PDF sí lo muestre así.

def _sin_espacios(texto: str) -> str:
    return texto.replace(" ", "")


def test_nombre_producto_con_caracteres_especiales_aparece_literal():
    orden = _orden_de_prueba()
    orden.detalles[0].nombre_pro = "Aceite <b>10W40</b> & filtro"

    pdf_bytes = OrdenTrabajoPDFGenerator().generar_pdf(orden)

    texto = _sin_espacios(texto_visible_del_pdf(pdf_bytes))
    # Literal, tal cual lo escribió el usuario -- no en negrita (lo que
    # pasaría si <b> se interpretara como marcado real).
    assert "Aceite<b>10W40</b>&filtro" in texto


def test_descripcion_producto_con_img_malicioso_no_genera_lectura_de_archivo():
    orden = _orden_de_prueba()
    orden.detalles[0].descripcion_pro = '<img src="/etc/hosts"/>'

    # Antes del fix esto lanzaba OSError: reportlab intentaba abrir
    # /etc/hosts como si fuera una imagen referenciada en el PDF.
    pdf_bytes = OrdenTrabajoPDFGenerator().generar_pdf(orden)

    texto = _sin_espacios(texto_visible_del_pdf(pdf_bytes))
    assert '<imgsrc="/etc/hosts"/>' in texto


def test_mecanico_con_marcado_malicioso_no_rompe_ni_se_interpreta():
    orden = _orden_de_prueba()
    orden.mecanico = 'Carlos <img src="/etc/hosts"/>'

    pdf_bytes = OrdenTrabajoPDFGenerator().generar_pdf(orden)

    texto = _sin_espacios(texto_visible_del_pdf(pdf_bytes))
    assert 'Carlos<imgsrc="/etc/hosts"/>' in texto


def test_observacion_con_caracteres_especiales_aparece_literal():
    """Las observaciones van en celdas de Table, no en Paragraph (Table no
    interpreta el marcado), así que ya eran seguras antes de este ticket --
    se deja el test para que quede probado, no solo asumido."""
    orden = _orden_de_prueba()
    orden.observacion_ot = 'falla a < 3000 rpm, aceite & filtro, <img src="/etc/hosts"/>'

    pdf_bytes = OrdenTrabajoPDFGenerator().generar_pdf(orden)

    texto = texto_visible_del_pdf(pdf_bytes)
    assert 'falla a < 3000 rpm, aceite & filtro, <img src="/etc/hosts"/>' in texto
