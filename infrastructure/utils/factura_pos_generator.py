"""
Generador de PDF para Facturas POS (Ticket de 80mm)
"""
from datetime import datetime
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

from domain.contracts.ordenes_trabajo.orden_trabajo_contract import OrdenTrabajoResponseContract


class FacturaPOSPDFGenerator:
    """Genera facturas en formato POS (ticket de 80mm)"""

    def __init__(self):
        # Configuración de ticket POS (80mm de ancho)
        self.ancho_ticket = 80 * mm
        self.alto_ticket = 297 * mm  # Altura inicial
        self.margen = 5 * mm
        self.ancho_util = self.ancho_ticket - (2 * self.margen)

    def generar_factura(self, orden: OrdenTrabajoResponseContract, ruta_salida: str):
        """
        Genera una factura en formato POS

        Args:
            orden: Contrato con los datos de la orden de trabajo
            ruta_salida: Ruta donde se guardará el PDF
        """
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)

        # Crear el canvas
        c = canvas.Canvas(ruta_salida, pagesize=(self.ancho_ticket, self.alto_ticket))

        # Posición inicial
        y = self.alto_ticket - 10 * mm

        # Generar contenido
        y = self._crear_encabezado(c, orden, y)
        y = self._crear_datos_cliente(c, orden, y)
        y = self._crear_datos_vehiculo(c, orden, y)
        y = self._crear_productos(c, orden, y)
        y = self._crear_totales(c, orden, y)
        y = self._crear_pie(c, orden, y)

        # Finalizar PDF
        c.save()

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

    def _crear_encabezado(self, c: canvas.Canvas, orden: OrdenTrabajoResponseContract, y: float) -> float:
        """Crea el encabezado del ticket"""
        y = self._texto_centrado(c, "MOTOGESTION", y, 14, "Courier-Bold")
        y = self._texto_centrado(c, "Taller de Motos", y - 2*mm, 9, "Courier")
        y = self._texto_centrado(c, "Medellin, Colombia", y, 8, "Courier")
        y = self._texto_centrado(c, "Tel: (604) 123-4567", y, 8, "Courier")

        y -= 3 * mm
        y = self._linea_separadora(c, y)
        y -= 2 * mm

        y = self._texto_centrado(c, "FACTURA DE VENTA", y, 12, "Courier-Bold")
        consecutivo = orden.consecutivo_ot or 'N/A'
        y = self._texto_centrado(c, f"No. {consecutivo}", y, 10, "Courier-Bold")

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

        # Filtrar solo productos facturables (cantidad > 0)
        productos_facturables = [d for d in orden.detalles if d.cantidad_deto > 0]

        if not productos_facturables:
            c.setFont("Courier", 8)
            y = self._texto_centrado(c, "Sin productos facturables", y, 8, "Courier")
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
        productos_facturables = [d for d in orden.detalles if d.cantidad_deto > 0]

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

    def _crear_pie(self, c: canvas.Canvas, orden: OrdenTrabajoResponseContract, y: float) -> float:
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

        # Fecha de impresión
        c.setFont("Courier", 6)
        fecha_impresion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        y = self._texto_centrado(c, f"Impreso: {fecha_impresion}", y, 6, "Courier")

        return y
