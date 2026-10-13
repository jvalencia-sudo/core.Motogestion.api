"""F0-07: el sistema no emite facturación electrónica DIAN, así que el ticket
POS no puede llamarse "factura" en ningún texto visible (título del PDF,
encabezado) y debe incluir la nota de que no es una factura electrónica."""
import base64
import re
import zlib
from datetime import date

from domain.contracts.ordenes_trabajo.orden_trabajo_contract import OrdenTrabajoResponseContract
from infrastructure.utils.comprobante_servicio_generator import ComprobanteServicioPDFGenerator


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


def _texto_visible_del_pdf(pdf_bytes: bytes) -> str:
    """Decodifica los content streams del PDF (reportlab los deja en
    ASCII85+FlateDecode por defecto) y concatena su texto, para poder buscar
    literales sin depender de que el PDF esté sin comprimir."""
    partes = []
    for bloque in re.findall(rb"stream\r?\n(.*?)endstream", pdf_bytes, re.DOTALL):
        bloque = bloque.rstrip(b"\r\n")
        try:
            bloque = base64.a85decode(bloque, adobe=True)
        except ValueError:
            pass
        try:
            bloque = zlib.decompress(bloque)
        except zlib.error:
            pass
        partes.append(bloque)
    return b"\n".join(partes).decode("latin-1")


def test_titulo_del_pdf_no_dice_factura():
    pdf_bytes = ComprobanteServicioPDFGenerator().generar_comprobante(_orden_de_prueba())

    assert b"/Title (Comprobante de servicio #123)" in pdf_bytes
    assert b"Factura" not in pdf_bytes


def test_pdf_incluye_nota_de_que_no_es_factura_electronica():
    pdf_bytes = ComprobanteServicioPDFGenerator().generar_comprobante(_orden_de_prueba())

    texto = _texto_visible_del_pdf(pdf_bytes)
    assert "Este documento no es una" in texto
    assert "factura electronica" in texto
    assert "COMPROBANTE DE SERVICIO" in texto
