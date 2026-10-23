"""Genera el PDF de una orden de trabajo a partir de la plantilla HTML
(rediseño con WeasyPrint, reemplaza al generador ReportLab anterior).

Seguridad:
- Jinja2 con autoescape: todo texto del taller o del cliente se escapa.
- WeasyPrint solo puede leer archivos dentro de resources/pdf/orden_trabajo/
  (plantilla, CSS, fuentes) y URIs data:. Cualquier otra URL se rechaza.
- El logo llega como bytes (ya guardados en `taller_logo`) y se incrusta
  como data URI: a WeasyPrint nunca se le pasa una URL externa.
- Los colores se validan como hex #RRGGBB antes de llegar a la plantilla.
"""
from __future__ import annotations

import base64
import re
from decimal import Decimal
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from urllib.request import url2pathname

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
from weasyprint.urls import URLFetcher, URLFetchingError

from domain.contracts.ordenes_trabajo.orden_trabajo_contract import OrdenTrabajoResponseContract
from infrastructure.utils.marca_taller import ConfigMarcaTaller

BASE = Path(__file__).resolve().parent.parent.parent / "resources" / "pdf" / "orden_trabajo"
PLANTILLAS = BASE / "plantillas"
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# F1-05: Pendiente/En Proceso/Completada/Entregada/Anulada/Garantía -- la
# plantilla no tiene estilo propio para Garantía, se reusa el neutro de
# Entregada.
_ESTADO_CLAVE = {1: "pendiente", 2: "en_proceso", 3: "lista", 4: "entregada", 5: "anulada", 6: "entregada"}


# ---------------------------------------------------------------- filtros
def _miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def moneda(valor) -> str:
    """$120.000 — sin decimales: el peso colombiano no los usa en la práctica."""
    v = Decimal(str(valor or 0)).quantize(Decimal("1"))
    return f"${_miles(int(v))}"


def cantidad(valor) -> str:
    """1 → '1' · 1.5 → '1,5' · 0.25 → '0,25'. Nunca '1.000' (se lee como mil)."""
    v = Decimal(str(valor or 0)).normalize()
    entero, _, dec = f"{v:f}".partition(".")
    return _miles(int(entero)) + (f",{dec}" if dec else "")


def km(valor) -> str:
    return f"{_miles(int(valor))} km" if valor not in (None, "") else "—"


def fecha(valor) -> str:
    if not valor:
        return "—"
    from datetime import date
    d = valor if isinstance(valor, date) else date.fromisoformat(str(valor)[:10])
    return f"{d.day} {_MESES[d.month - 1]} {d.year}"


def numero_ot(n) -> str:
    return f"OT-{int(n):04d}"


def telefono(t) -> str:
    d = re.sub(r"\D", "", str(t or ""))
    return f"{d[:3]} {d[3:6]} {d[6:]}" if len(d) == 10 else str(t or "")


def placa(p) -> str:
    p = re.sub(r"[\s-]", "", str(p or "")).upper()
    return f"{p[:3]} {p[3:]}" if len(p) == 6 else p


# ---------------------------------------------------------------- colores
def _hex_a_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _rgb_a_hex(c):
    return "#" + "".join(f"{max(0, min(255, round(x))):02X}" for x in c)


def _luminancia(rgb):
    def canal(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def paleta(color: str) -> dict:
    """Deriva del color del taller un fondo suave y una versión legible para texto."""
    if not _HEX.match(color or ""):
        color = "#1F6FEB"  # color por defecto si la configuración no es válida
    rgb = _hex_a_rgb(color)
    suave = tuple(c + (255 - c) * 0.88 for c in rgb)
    texto = rgb
    while (1.05) / (_luminancia(texto) + 0.05) < 4.5:  # contraste AA sobre blanco
        texto = tuple(c * 0.9 for c in texto)
    return {"color_acento": color, "color_acento_suave": _rgb_a_hex(suave), "color_acento_texto": _rgb_a_hex(texto)}


# ---------------------------------------------------------------- recursos
def data_uri(contenido: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(contenido).decode()}"


class _FetcherSeguro(URLFetcher):
    """Solo permite URIs data: y archivos dentro de esta carpeta (CSS, fuentes)."""

    def __init__(self):
        super().__init__(allowed_protocols={"file", "data"}, timeout=5)

    def fetch(self, url, headers=None):
        if url.startswith("file:"):
            # url2pathname (no un unquote()+Path() a mano): en Windows el path
            # de una file:// URI trae un "/" antes de la letra de unidad
            # ("/C:/Users/..."), que Path() interpreta como ruta relativa a la
            # unidad actual en vez de absoluta -- BASE nunca quedaba en
            # ruta.parents y el fetcher bloqueaba CSS y fuentes siempre,
            # dejando el PDF sin estilos (sin error visible, WeasyPrint solo
            # loguea un warning y sigue sin esa hoja de estilos).
            ruta = Path(url2pathname(urlparse(url).path)).resolve()
            if BASE not in ruta.parents:
                raise URLFetchingError(f"Archivo fuera de la plantilla: {ruta.name}")
        elif not url.startswith("data:"):
            raise URLFetchingError(f"Recurso externo bloqueado: {url[:60]}")
        return super().fetch(url, headers)


_env = Environment(loader=FileSystemLoader(PLANTILLAS), autoescape=select_autoescape(["html", "j2"]))
_env.filters.update(moneda=moneda, cantidad=cantidad, km=km, fecha=fecha,
                     numero_ot=numero_ot, telefono=telefono, placa=placa)


def _renderizar(contexto: dict) -> bytes:
    contexto = {**contexto, "marca": paleta(contexto["taller"].get("color_acento", ""))}
    html = _env.get_template("orden_trabajo.html.j2").render(**contexto)
    return HTML(string=html, base_url=str(PLANTILLAS) + "/", url_fetcher=_FetcherSeguro()).write_pdf()


# ---------------------------------------------------------------- mapeo
def _construir_contexto_orden(orden: OrdenTrabajoResponseContract, marca: ConfigMarcaTaller) -> dict:
    lineas = [
        {
            "codigo": str(d.cod_pro_deto),
            "nombre": d.nombre_pro,
            "detalle": d.descripcion_pro,
            "cantidad": d.cantidad_deto,
            "precio_unitario": d.valor_unitario_deto,
            "total": d.subtotal,
            "sin_costo": not d.cobrar_deto,
            "motivo_sin_costo": d.motivo_no_cobro_deto,
        }
        for d in (orden.detalles or [])
    ]
    # d.subtotal ya es cantidad_deto * valor_unitario_deto sin importar
    # cobrar_deto (así lo calcula vw_detalle_ot_productos) -- es el valor
    # nominal del ítem, lo que necesitamos para "como si todo se cobrara".
    total_sin_costo = sum(d.subtotal for d in (orden.detalles or []) if not d.cobrar_deto)
    total = orden.total_ot or 0.0

    logo_data_uri: Optional[str] = None
    if marca.logo_bytes:
        logo_data_uri = data_uri(marca.logo_bytes, marca.logo_content_type or "image/png")

    return {
        "taller": {
            "nombre": marca.nombre_comercial,
            "nit": marca.nit,
            "direccion": marca.direccion,
            "whatsapp": marca.whatsapp,
            "correo": marca.correo,
            "color_acento": marca.color_principal,
            "logo_data_uri": logo_data_uri,
        },
        "orden": {
            "numero": orden.consecutivo_ot,
            "estado": orden.estado_ot,
            "estado_clave": _ESTADO_CLAVE.get(orden.cod_ot_est_ot, "entregada"),
            "fecha_ingreso": orden.fecha_elaboracion_ot,
            "fecha_entrega": orden.fecha_entrega_ot if orden.cod_ot_est_ot == 4 else None,
            # No existe ETA en el sistema hoy -- fuera de alcance de este trabajo.
            "fecha_estimada": None,
            "mecanico": orden.mecanico,
            "recepcionista": orden.recepcionista,
            "km_ingreso": orden.kilometraje_ingreso_ot,
            "km_salida": orden.kilometraje_salida_ot,
            "motivo_cliente": orden.observacion_cli_ot,
            "diagnostico": orden.observacion_ot,
            "lineas": lineas,
            "subtotal": total + total_sin_costo,
            "total_sin_costo": total_sin_costo,
            "total": total,
            "garantia_hasta": orden.fecha_fin_garantia_ot,
        },
        "cliente": {
            "nombre": orden.nombre_completo_cliente,
            "tipo_documento": orden.tipo_documento_cli,
            "documento": orden.documento_cli,
            "telefono": orden.telefono_cli,
            "direccion": orden.direccion_cli,
            "ciudad": None,
        },
        "moto": {
            "placa": orden.placa_mot,
            # Solo el año: no existe un campo de línea/referencia del
            # fabricante en el sistema hoy (modelo_mot es el año modelo).
            "modelo": str(orden.modelo_mot),
            "ciudad_placa": orden.ciudad_placa_mot or "",
            "marca": orden.marca_moto,
            "color": orden.color_mot,
        },
        "config": {
            "mostrar_precios_unitarios": marca.mostrar_precios_unitarios,
            "mostrar_mecanico": marca.mostrar_mecanico,
            # Mismo campo que antes solo mostraba la firma del cliente --
            # ahora controla el bloque de ambas firmas (cliente + taller).
            "mostrar_firmas": marca.mostrar_firma_cliente,
            "mostrar_marca_motogestion": True,
            "condiciones": marca.texto_condiciones,
            "pie": marca.texto_pie,
        },
        # QR de estado en tiempo real: fuera de alcance (no existe la página
        # pública aún). La plantilla ya hace este bloque opcional.
        "estado_qr_data_uri": None,
    }


def generar_pdf_orden_html(orden: OrdenTrabajoResponseContract, marca: ConfigMarcaTaller) -> bytes:
    """Genera el PDF (carta) de la orden, en memoria -- nunca se escribe a
    disco: consecutivo_ot es único por taller (no global, la llave primaria
    real es cod_taller+consecutivo_ot), así que un nombre de archivo basado
    solo en consecutivo_ot podía colisionar entre dos talleres y filtrar el
    PDF de uno al otro. El RLS no protege esto porque ocurre fuera de la
    base de datos."""
    return _renderizar(_construir_contexto_orden(orden, marca))
