"""
Generador de PDF para Comprobantes de Servicio (Ticket de 80mm)
"""
from datetime import datetime
import io
import textwrap
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from domain.contracts.ordenes_trabajo.orden_trabajo_contract import OrdenTrabajoResponseContract


class ComprobanteServicioPDFGenerator:
    """Genera comprobantes de servicio en formato POS (ticket de 80mm)"""

    def __init__(self):
        # Configuración de ticket POS (80mm de ancho)
        self.ancho_ticket = 80 * mm
        self.alto_ticket = 297 * mm  # Altura inicial
        self.margen = 5 * mm
        self.ancho_util = self.ancho_ticket - (2 * self.margen)

    def generar_comprobante(
        self,
        orden: OrdenTrabajoResponseContract,
        texto_pie_comprobante: str = None,
        nombre_tal: str = None,
        direccion_tal: str = None,
        telefono_tal: str = None,
    ) -> bytes:
        """
        Genera un comprobante de servicio en formato POS, en memoria (ver nota
        de seguridad en OrdenTrabajoPDFGenerator.generar_pdf: consecutivo_ot
        no es único globalmente, solo por taller).

        Args:
            orden: Contrato con los datos de la orden de trabajo
            texto_pie_comprobante: línea libre configurable por el taller
                ("Mi taller"), se imprime al final del ticket. Puede ser None.
            nombre_tal, direccion_tal, telefono_tal: datos reales del taller
                ("Mi taller") para el encabezado. nombre_tal siempre debería
                venir (NOT NULL en BD); dirección/teléfono pueden ser None si
                el taller no los configuró -- en ese caso esa línea se omite
                (no se inventa un valor).

        Returns:
            bytes: Contenido del PDF generado
        """
        buffer = io.BytesIO()

        # Crear el canvas
        c = canvas.Canvas(buffer, pagesize=(self.ancho_ticket, self.alto_ticket))
        # Sin esto, reportlab deja el default "(anonymous)" como título/autor
        # del PDF, visible en la pestaña del navegador al abrirlo.
        c.setTitle(f"Comprobante de servicio #{orden.consecutivo_ot}")
        c.setAuthor("Motogestion")

        # Posición inicial
        y = self.alto_ticket - 10 * mm

        # Generar contenido
        y = self._crear_encabezado(c, orden, y, nombre_tal, direccion_tal, telefono_tal)
        y = self._crear_datos_cliente(c, orden, y)
        y = self._crear_datos_vehiculo(c, orden, y)
        y = self._crear_productos(c, orden, y)
        y = self._crear_totales(c, orden, y)
        y = self._crear_pie(c, orden, y, texto_pie_comprobante)

        # Finalizar PDF
        c.save()

        return buffer.getvalue()

    def _texto_centrado(self, c: canvas.Canvas, texto: str, y: float, tamano: int = 10, fuente: str = "Courier-Bold") -> float:
        """
        Dibuja texto centrado y retorna la nueva posición Y
        """
        c.setFont(fuente, tamano)
        ancho_texto = c.stringWidth(texto, fuente, tamano)
        x = (self.ancho_ticket - ancho_texto) / 2
        c.drawString(x, y, texto)
        return y - (tamano + 2)

    def _linea_separadora(self, c: canvas.Canvas, y: float) -> float:
        """
        Dibuja una línea separadora y retorna nueva posición Y
        """
        c.line(self.margen, y, self.ancho_ticket - self.margen, y)
        return y - 3 * mm

    def _crear_encabezado(
        self, c: canvas.Canvas, orden: OrdenTrabajoResponseContract, y: float,
        nombre_tal: str = None, direccion_tal: str = None, telefono_tal: str = None,
    ) -> float:
        """Crea el encabezado del ticket con los datos reales del taller
        ("Mi taller") -- antes decía siempre "MOTOGESTION" / "Medellin,
        Colombia" / un teléfono inventado, sin importar de qué taller fuera
        la orden: el cliente de cualquier taller recibía un número que no
        existe. dirección/teléfono se omiten si el taller no los configuró,
        en vez de inventar un valor."""
        y = self._texto_centrado(c, (nombre_tal or "COMPROBANTE DE SERVICIO").upper(), y, 14, "Courier-Bold")
        if direccion_tal:
            y = self._texto_centrado(c, direccion_tal, y - 2 * mm, 9, "Courier")
        if telefono_tal:
            y = self._texto_centrado(c, f"Tel: {telefono_tal}", y - 2 * mm, 8, "Courier")

        y -= 3 * mm
        y = self._linea_separadora(c, y)
        y -= 2 * mm

        y = self._texto_centrado(c, "COMPROBANTE DE SERVICIO", y, 11, "Courier-Bold")
        consecutivo = orden.consecutivo_ot or 'N/A'
        y = self._texto_centrado(c, f"No. {consecutivo}", y, 10, "Courier-Bold")

        y -= 2 * mm
        y = self._texto_centrado(c, "Este documento no es una", y, 7, "Courier")
        y = self._texto_centrado(c, "factura de venta ni un", y, 7, "Courier")
        y = self._texto_centrado(c, "documento equivalente", y, 7, "Courier")

        y -= 3 * mm
        return y

    def _crear_datos_cliente(self, c: canvas.Canvas, orden: OrdenTrabajoResponseContract, y: float) -> float:
        """Crea la sección de datos del cliente"""
        c.setFont("Courier", 8)

        fecha = orden.fecha_elaboracion_ot or 'N/A'
        c.drawString(self.margen, y, f"Fecha: {fecha}")
        y -= 10

        cliente = orden.nombre_completo_cliente or 'N/A'
        # Limitar el nombre si es muy largo
        if len(cliente) > 30:
            cliente = cliente[:27] + "..."
        c.drawString(self.margen, y, f"Cliente: {cliente}")
        y -= 10

        documento = orden.documento_cli or 'N/A'
        c.drawString(self.margen, y, f"Doc: {documento}")
        y -= 10

        telefono = orden.telefono_cli or 'N/A'
        c.drawString(self.margen, y, f"Tel: {telefono}")
        y -= 15

        return y

    def _crear_datos_vehiculo(self, c: canvas.Canvas, orden: OrdenTrabajoResponseContract, y: float) -> float:
        """Crea la sección de datos del vehículo"""
        y = self._linea_separadora(c, y)

        c.setFont("Courier-Bold", 9)
        c.drawString(self.margen, y, "VEHICULO")
        y -= 10

        c.setFont("Courier", 8)

        placa = orden.placa_mot or 'N/A'
        c.drawString(self.margen, y, f"Placa: {placa}")
        y -= 10

        marca = orden.marca_moto or 'N/A'
        c.drawString(self.margen, y, f"Marca: {marca}")
        y -= 10

        modelo = orden.modelo_mot or 'N/A'
        c.drawString(self.margen, y, f"Modelo: {modelo}")
        y -= 10

        km = orden.kilometraje_ingreso_ot or 'N/A'
        c.drawString(self.margen, y, f"Km: {km}")
        y -= 15

        return y

    def _crear_productos(self, c: canvas.Canvas, orden: OrdenTrabajoResponseContract, y: float) -> float:
        """Crea la sección de productos (SOLO facturables)"""
        y = self._linea_separadora(c, y)

        c.setFont("Courier-Bold", 9)
        y = self._texto_centrado(c, "PRODUCTOS Y SERVICIOS", y, 9, "Courier-Bold")
        y -= 10

        y = self._linea_separadora(c, y)
        y -= 5

        # Filtrar solo productos facturables (cobrar_deto=True)
        productos_facturables = [d for d in orden.detalles if d.cobrar_deto]

        if not productos_facturables:
            c.setFont("Courier", 8)
            y = self._texto_centrado(c, "Sin productos cobrados", y, 8, "Courier")
            y -= 10
            return y

        c.setFont("Courier", 8)
        for producto in productos_facturables:
            # Nombre del producto (limitar caracteres)
            nombre = producto.nombre_pro or 'N/A'
            if len(nombre) > 35:
                nombre = nombre[:32] + "..."
            c.drawString(self.margen, y, nombre)
            y -= 10

            # Cantidad x Precio = Subtotal
            cantidad = producto.cantidad_deto
            precio = producto.valor_unitario_deto
            subtotal = cantidad * precio

            # Línea de detalle
            linea_detalle = f"  {cantidad} x ${precio:,.0f}"
            c.drawString(self.margen, y, linea_detalle)

            # Subtotal alineado a la derecha
            subtotal_str = f"${subtotal:,.0f}"
            ancho_subtotal = c.stringWidth(subtotal_str, "Courier", 8)
            c.drawString(self.ancho_ticket - self.margen - ancho_subtotal, y, subtotal_str)
            y -= 10

            # Línea separadora fina
            c.line(self.margen, y, self.ancho_ticket - self.margen, y)
            y -= 8

        y -= 5
        return y

    def _crear_totales(self, c: canvas.Canvas, orden: OrdenTrabajoResponseContract, y: float) -> float:
        """Crea la sección de totales (SOLO productos facturables)"""
        y = self._linea_separadora(c, y)

        c.setFont("Courier-Bold", 10)
        y = self._texto_centrado(c, "RESUMEN", y, 10, "Courier-Bold")
        y -= 10

        y = self._linea_separadora(c, y)
        y -= 5

        # Calcular totales SOLO de productos facturables
        productos_facturables = [d for d in orden.detalles if d.cobrar_deto]

        subtotal = sum(
            d.cantidad_deto * d.valor_unitario_deto
            for d in productos_facturables
        )

        c.setFont("Courier", 9)

        # Subtotal
        c.drawString(self.margen, y, "Subtotal:")
        subtotal_str = f"${subtotal:,.0f}"
        ancho_subtotal = c.stringWidth(subtotal_str, "Courier", 9)
        c.drawString(self.ancho_ticket - self.margen - ancho_subtotal, y, subtotal_str)
        y -= 10

        # IVA (incluido)
        c.drawString(self.margen, y, "IVA (incluido):")
        c.drawString(self.ancho_ticket - self.margen - c.stringWidth("$0", "Courier", 9), y, "$0")
        y -= 10

        # Línea antes del total
        c.line(self.margen, y, self.ancho_ticket - self.margen, y)
        y -= 10

        # Total
        c.setFont("Courier-Bold", 12)
        c.drawString(self.margen, y, "TOTAL:")
        total_str = f"${subtotal:,.0f}"
        ancho_total = c.stringWidth(total_str, "Courier-Bold", 12)
        c.drawString(self.ancho_ticket - self.margen - ancho_total, y, total_str)
        y -= 15

        # Línea doble
        c.line(self.margen, y, self.ancho_ticket - self.margen, y)
        y -= 2
        c.line(self.margen, y, self.ancho_ticket - self.margen, y)
        y -= 15

        return y

    def _crear_pie(
        self, c: canvas.Canvas, orden: OrdenTrabajoResponseContract, y: float,
        texto_pie_comprobante: str = None,
    ) -> float:
        """Crea el pie del ticket"""
        c.setFont("Courier", 8)

        # Observaciones
        observacion = orden.observacion_ot
        if observacion:
            c.drawString(self.margen, y, "Observaciones:")
            y -= 10
            # Limitar observación a 40 caracteres por línea, máximo 2 líneas
            obs_corta = observacion[:80]
            if len(obs_corta) > 40:
                c.drawString(self.margen, y, obs_corta[:40])
                y -= 10
                if len(obs_corta) > 40:
                    c.drawString(self.margen, y, obs_corta[40:80])
                    y -= 10
            else:
                c.drawString(self.margen, y, obs_corta)
                y -= 10
            y -= 5

        # Mecánico y Recepcionista
        c.setFont("Courier", 7)
        mecanico = orden.mecanico or 'N/A'
        c.drawString(self.margen, y, f"Mecanico: {mecanico[:25]}")
        y -= 10

        recepcionista = orden.recepcionista or 'N/A'
        c.drawString(self.margen, y, f"Recibido: {recepcionista[:25]}")
        y -= 10

        # Fecha de entrega
        fecha_entrega = orden.fecha_entrega_ot
        if fecha_entrega:
            # Convertir a string si es objeto date
            if hasattr(fecha_entrega, 'strftime'):
                fecha_entrega_str = fecha_entrega.strftime('%Y-%m-%d')
            else:
                fecha_entrega_str = str(fecha_entrega)
            c.drawString(self.margen, y, f"F. Entrega: {fecha_entrega_str}")
            y -= 10

        # Garantía
        fecha_garantia = orden.fecha_fin_garantia_ot
        if fecha_garantia:
            # Convertir a string si es objeto date
            if hasattr(fecha_garantia, 'strftime'):
                fecha_garantia_str = fecha_garantia.strftime('%Y-%m-%d')
            else:
                fecha_garantia_str = str(fecha_garantia)
            c.drawString(self.margen, y, f"Garantia hasta: {fecha_garantia_str}")
            y -= 15
        else:
            y -= 10

        # Mensaje final
        y -= 5
        c.line(self.margen, y, self.ancho_ticket - self.margen, y)
        y -= 10

        c.setFont("Courier-Bold", 10)
        y = self._texto_centrado(c, "GRACIAS POR SU COMPRA!", y, 10, "Courier-Bold")
        y -= 10

        c.line(self.margen, y, self.ancho_ticket - self.margen, y)
        y -= 10

        # Texto de pie configurable por el taller ("Mi taller"): límite visual
        # de 3 líneas / ~38 caracteres cada una (recorte por longitud, igual
        # que el resto de este generador -- no usa reportlab.platypus.Paragraph,
        # así que no aplica texto_seguro aquí).
        if texto_pie_comprobante:
            lineas_pie = textwrap.wrap(texto_pie_comprobante.strip(), width=38)[:3]
            c.setFont("Courier", 7)
            for linea in lineas_pie:
                y = self._texto_centrado(c, linea, y, 7, "Courier")
            y -= 5
            c.line(self.margen, y, self.ancho_ticket - self.margen, y)
            y -= 10

        # Fecha de impresión
        c.setFont("Courier", 6)
        fecha_impresion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        y = self._texto_centrado(c, f"Impreso: {fecha_impresion}", y, 6, "Courier")

        return y
