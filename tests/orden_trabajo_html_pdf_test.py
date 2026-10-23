"""Rediseño del PDF de orden de trabajo (WeasyPrint + HTML/CSS/Jinja2,
infrastructure/utils/orden_trabajo_html_pdf.py), reemplaza al generador
ReportLab anterior (pdf_generator_test.py).

F0-07: el PDF no puede decir "factura" en ningún texto visible, y debe
llevar la nota de que no es una factura de venta ni un documento
equivalente -- Jinja2 escapa automáticamente (autoescape=True) cualquier
texto de usuario que entre a la plantilla, así que un "<img src=.../>" o
"<b>" en un nombre de producto/mecánico debe aparecer LITERAL en el PDF,
nunca interpretado."""
import io
from datetime import date
from decimal import Decimal

from pypdf import PdfReader

from domain.contracts.ordenes_trabajo.detalle_orden_trabajo_contract import (
    DetalleOrdenTrabajoResponseContract,
)
from domain.contracts.ordenes_trabajo.orden_trabajo_contract import OrdenTrabajoResponseContract
from infrastructure.utils.marca_taller import ConfigMarcaTaller
from infrastructure.utils.orden_trabajo_html_pdf import (
    _construir_contexto_orden,
    generar_pdf_orden_html,
)
from tests.pdf_test_utils import texto_visible_del_pdf

_NOTA_LEGAL = "factura de venta ni un documento equivalente"


def _detalle(**overrides) -> DetalleOrdenTrabajoResponseContract:
    base = dict(
        consecutivo_ot_deto=1,
        cod_pro_deto=10,
        nombre_pro="Cambio de aceite",
        cantidad_deto=Decimal("1"),
        valor_unitario_deto=50000,
        cobrar_deto=True,
        subtotal=50000,
        usuario_confirmacion="1",
        estado_producto="Confirmado",
    )
    base.update(overrides)
    return DetalleOrdenTrabajoResponseContract(**base)


def _orden_de_prueba(**overrides) -> OrdenTrabajoResponseContract:
    base = dict(
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
        cod_ot_est_ot=4,
        detalles=[_detalle()],
        total_ot=50000,
    )
    base.update(overrides)
    return OrdenTrabajoResponseContract(**base)


def test_texto_visible_del_pdf_no_dice_factura():
    pdf_bytes = generar_pdf_orden_html(_orden_de_prueba(), ConfigMarcaTaller())

    texto = texto_visible_del_pdf(pdf_bytes).lower()
    texto_sin_nota = texto.replace(_NOTA_LEGAL, "")
    assert "factura" not in texto_sin_nota


def test_pdf_incluye_nota_legal():
    pdf_bytes = generar_pdf_orden_html(_orden_de_prueba(), ConfigMarcaTaller())

    texto = texto_visible_del_pdf(pdf_bytes).lower()
    assert _NOTA_LEGAL in texto


def _sin_espacios(texto: str) -> str:
    return texto.replace(" ", "").replace("\n", "")


def test_nombre_producto_con_caracteres_especiales_aparece_literal():
    orden = _orden_de_prueba(detalles=[_detalle(nombre_pro="Aceite <b>10W40</b> & filtro")])

    pdf_bytes = generar_pdf_orden_html(orden, ConfigMarcaTaller())

    texto = _sin_espacios(texto_visible_del_pdf(pdf_bytes))
    # Literal, tal cual lo escribió el usuario -- no en negrita (lo que
    # pasaría si <b> se interpretara como marcado real).
    assert "Aceite<b>10W40</b>&filtro" in texto


def test_descripcion_producto_con_img_malicioso_no_se_interpreta():
    orden = _orden_de_prueba(
        detalles=[_detalle(descripcion_pro='<img src="/etc/hosts"/>')]
    )

    pdf_bytes = generar_pdf_orden_html(orden, ConfigMarcaTaller())

    texto = _sin_espacios(texto_visible_del_pdf(pdf_bytes))
    assert 'imgsrc="/etc/hosts"/' in texto


def test_mecanico_con_marcado_malicioso_no_se_interpreta():
    orden = _orden_de_prueba(mecanico='Carlos <img src="/etc/hosts"/>')

    pdf_bytes = generar_pdf_orden_html(orden, ConfigMarcaTaller())

    texto = _sin_espacios(texto_visible_del_pdf(pdf_bytes))
    assert 'Carlos<imgsrc="/etc/hosts"/>' in texto


def test_observacion_con_caracteres_especiales_aparece_literal():
    orden = _orden_de_prueba(
        observacion_ot='falla a < 3000 rpm, aceite & filtro, <img src="/etc/hosts"/>'
    )

    pdf_bytes = generar_pdf_orden_html(orden, ConfigMarcaTaller())

    texto = texto_visible_del_pdf(pdf_bytes)
    assert 'falla a < 3000 rpm, aceite & filtro, <img src="/etc/hosts"/>' in texto


def test_pdf_incluye_la_tipografia_de_la_plantilla():
    """Si _FetcherSeguro bloquea el CSS o las fuentes (@font-face), WeasyPrint
    no levanta error -- solo loguea un warning y sigue con la fuente por
    defecto, así que el PDF se ve sin ningún diseño (bug real: en Windows la
    reconstrucción de la ruta desde el file:// URI fallaba y el fetcher
    bloqueaba *todo* archivo local, sin que nada lo hiciera visible). Barlow
    solo se declara vía @font-face en orden_trabajo.css -- si el CSS no
    cargó, no aparece embebida."""
    pdf_bytes = generar_pdf_orden_html(_orden_de_prueba(), ConfigMarcaTaller())

    reader = PdfReader(io.BytesIO(pdf_bytes))
    fuentes = reader.pages[0]["/Resources"]["/Font"]
    nombres = [str(f.get_object()["/BaseFont"]) for f in fuentes.values()]
    assert any("Barlow" in n for n in nombres), nombres


def test_pie_de_la_orden_aparece_en_el_pdf():
    """F1-09: el campo "Pie de la orden" (texto_pie_tal) no se estaba
    propagando al contexto de la plantilla -- quedaba guardado en la BD pero
    nunca llegaba al PDF, en ningún taller."""
    marca = ConfigMarcaTaller(texto_pie="Garantía válida presentando esta orden")

    pdf_bytes = generar_pdf_orden_html(_orden_de_prueba(), marca)

    assert "Garantía válida presentando esta orden" in texto_visible_del_pdf(pdf_bytes)


def test_pie_de_la_orden_con_marcado_malicioso_no_se_interpreta():
    marca = ConfigMarcaTaller(texto_pie='<img src="/etc/hosts"/>')

    pdf_bytes = generar_pdf_orden_html(_orden_de_prueba(), marca)

    texto = _sin_espacios(texto_visible_del_pdf(pdf_bytes))
    assert 'imgsrc="/etc/hosts"/' in texto


class TestMapeoDeContexto:
    """_construir_contexto_orden es lo que traduce el contrato de la orden a
    lo que espera la plantilla Jinja2 -- se prueba aparte del render
    completo de WeasyPrint (más rápido, y aísla el cálculo de la
    presentación)."""

    def test_subtotal_reconstruye_el_valor_nominal_de_las_cortesias(self):
        orden = _orden_de_prueba(
            detalles=[
                _detalle(cod_pro_deto=1, cobrar_deto=True, subtotal=50000),
                _detalle(
                    cod_pro_deto=2, cobrar_deto=False, subtotal=10000,
                    motivo_no_cobro_deto="cortesía",
                ),
            ],
            total_ot=50000,  # el cobrable; el de cortesía no suma al total real
        )

        contexto = _construir_contexto_orden(orden, ConfigMarcaTaller())

        assert contexto["orden"]["total"] == 50000
        assert contexto["orden"]["total_sin_costo"] == 10000
        assert contexto["orden"]["subtotal"] == 60000

    def test_estado_clave_mapea_cada_codigo(self):
        esperado = {1: "pendiente", 2: "en_proceso", 3: "lista", 4: "entregada", 5: "anulada", 6: "entregada"}
        for cod, clave in esperado.items():
            orden = _orden_de_prueba(cod_ot_est_ot=cod)
            contexto = _construir_contexto_orden(orden, ConfigMarcaTaller())
            assert contexto["orden"]["estado_clave"] == clave, f"cod {cod}"

    def test_ciudad_placa_ausente_no_rompe_el_contexto(self):
        orden = _orden_de_prueba(ciudad_placa_mot=None)

        contexto = _construir_contexto_orden(orden, ConfigMarcaTaller())

        assert contexto["moto"]["ciudad_placa"] == ""

    def test_ciudad_placa_presente_se_propaga(self):
        orden = _orden_de_prueba(ciudad_placa_mot="Medellín")

        contexto = _construir_contexto_orden(orden, ConfigMarcaTaller())

        assert contexto["moto"]["ciudad_placa"] == "Medellín"

    def test_pie_de_la_orden_se_propaga(self):
        marca = ConfigMarcaTaller(texto_pie="Gracias por su confianza")

        contexto = _construir_contexto_orden(_orden_de_prueba(), marca)

        assert contexto["config"]["pie"] == "Gracias por su confianza"
