"""F0-07: el sistema no emite facturación electrónica DIAN, así que el ticket
POS no puede llamarse "factura" en ningún texto visible (título del PDF,
encabezado, mensajes de estado vacío) y debe incluir la nota de que no es
una factura de venta ni un documento equivalente."""
from datetime import date

from domain.contracts.ordenes_trabajo.orden_trabajo_contract import OrdenTrabajoResponseContract
from infrastructure.utils.comprobante_servicio_generator import ComprobanteServicioPDFGenerator
from tests.pdf_test_utils import texto_visible_del_pdf

# Frase de la nota legal del pie: la contiene a propósito la palabra "factura",
# así que se descuenta del texto antes de buscar cualquier otra mención.
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
        documento_recepcionista="1",
        recepcionista="Recepcionista",
        documento_mecanico="2",
        mecanico="Mecanico",
        estado_ot="Entregada",
        cod_ot_est_ot=1,
        detalles=[],
    )


def test_titulo_del_pdf_no_dice_factura():
    pdf_bytes = ComprobanteServicioPDFGenerator().generar_comprobante(_orden_de_prueba())

    assert b"/Title (Comprobante de servicio #123)" in pdf_bytes


def test_texto_visible_del_pdf_no_dice_factura():
    """A diferencia del test anterior, este sí mira el contenido real de las
    páginas (decodificado de ASCII85+Flate), no solo los metadatos del PDF:
    detecta por ejemplo "Sin productos facturables" o un futuro "FACTURA DE
    VENTA" que se cuele en el encabezado."""
    pdf_bytes = ComprobanteServicioPDFGenerator().generar_comprobante(_orden_de_prueba())

    texto = texto_visible_del_pdf(pdf_bytes).lower()
    texto_sin_nota = texto.replace(_NOTA_LEGAL, "")
    assert "factura" not in texto_sin_nota


def test_pdf_incluye_nota_legal_y_encabezado_correcto():
    pdf_bytes = ComprobanteServicioPDFGenerator().generar_comprobante(_orden_de_prueba())

    texto = texto_visible_del_pdf(pdf_bytes)
    assert "Este documento no es una" in texto
    assert _NOTA_LEGAL in texto.lower()
    assert "COMPROBANTE DE SERVICIO" in texto


def test_orden_sin_productos_cobrados_no_dice_facturables():
    pdf_bytes = ComprobanteServicioPDFGenerator().generar_comprobante(_orden_de_prueba())

    texto = texto_visible_del_pdf(pdf_bytes)
    assert "Sin productos cobrados" in texto


def test_texto_pie_comprobante_configurado_se_imprime():
    """F0-13 (cierre): el texto de pie configurado en 'Mi taller' aparece en el
    ticket cuando el taller lo definió."""
    pdf_bytes = ComprobanteServicioPDFGenerator().generar_comprobante(
        _orden_de_prueba(), texto_pie_comprobante="Garantia valida solo con este ticket"
    )

    texto = texto_visible_del_pdf(pdf_bytes)
    assert "Garantia valida solo con este ticket" in texto


def test_sin_texto_pie_comprobante_no_rompe_el_pdf():
    """None es el valor por defecto (taller sin texto de pie configurado) --
    no debe lanzar ni dejar un hueco raro en el ticket."""
    pdf_bytes = ComprobanteServicioPDFGenerator().generar_comprobante(_orden_de_prueba())

    assert b"%PDF" in pdf_bytes[:10]
