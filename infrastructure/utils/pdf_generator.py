from datetime import datetime
from typing import List
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.graphics.shapes import Drawing, Circle, Line, Rect
from reportlab.graphics import renderPDF
import os

from domain.contracts.ordenes_trabajo.orden_trabajo_contract import OrdenTrabajoResponseContract


class OrdenTrabajoPDFGenerator:
    """Generador de PDFs para órdenes de trabajo con formato profesional"""

    def __init__(self):
        self.width, self.height = letter
        self.styles = getSampleStyleSheet()
        self._crear_estilos_personalizados()

    def _crear_estilos_personalizados(self):
        """Crea estilos personalizados para el documento"""
        # Estilo para encabezados de sección
        self.styles.add(ParagraphStyle(
            name='EncabezadoSeccion',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            spaceAfter=2,
            spaceBefore=2
        ))

        # Estilo para datos
        self.styles.add(ParagraphStyle(
            name='Datos',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.black,
            fontName='Helvetica',
            spaceAfter=2
        ))

        # Estilo para el título principal
        self.styles.add(ParagraphStyle(
            name='TituloOrden',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT
        ))

    def _crear_logo_moto(self) -> Drawing:
        """Crea un icono simple de moto usando formas geométricas"""
        d = Drawing(80, 60)

        # Rueda trasera
        d.add(Circle(20, 15, 12, fillColor=colors.HexColor('#00D084'), strokeColor=colors.HexColor('#00B06E'), strokeWidth=2))
        d.add(Circle(20, 15, 6, fillColor=colors.white, strokeColor=colors.HexColor('#00B06E'), strokeWidth=1))

        # Rueda delantera
        d.add(Circle(60, 15, 12, fillColor=colors.HexColor('#00D084'), strokeColor=colors.HexColor('#00B06E'), strokeWidth=2))
        d.add(Circle(60, 15, 6, fillColor=colors.white, strokeColor=colors.HexColor('#00B06E'), strokeWidth=1))

        # Chasis (líneas que conectan)
        d.add(Line(20, 20, 40, 35, strokeColor=colors.HexColor('#00B06E'), strokeWidth=3))
        d.add(Line(40, 35, 60, 20, strokeColor=colors.HexColor('#00B06E'), strokeWidth=3))
        d.add(Line(30, 25, 50, 25, strokeColor=colors.HexColor('#00B06E'), strokeWidth=2))

        # Asiento
        d.add(Rect(35, 35, 20, 8, fillColor=colors.HexColor('#00D084'), strokeColor=colors.HexColor('#00B06E'), strokeWidth=1))

        return d

    def _formatear_moneda(self, valor: float) -> str:
        """Formatea un valor como moneda colombiana"""
        return f"${valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    def _formatear_fecha(self, fecha) -> str:
        """Formatea una fecha al formato DD-Mes-YYYY"""
        if isinstance(fecha, str):
            try:
                fecha = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
            except:
                return fecha
        if isinstance(fecha, datetime):
            meses = {
                1: 'ene', 2: 'feb', 3: 'mar', 4: 'abr', 5: 'may', 6: 'jun',
                7: 'jul', 8: 'ago', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dic'
            }
            return f"{fecha.day:02d}-{meses[fecha.month]}-{fecha.year}"
        return str(fecha) if fecha else 'N/A'

    def _crear_encabezado(self, orden: OrdenTrabajoResponseContract) -> List:
        """Crea el encabezado del documento con logo y título"""
        elementos = []

        # Cargar el logo real desde resources/images
        logo_path = os.path.join("resources", "images", "logo.png")

        # Si el logo no existe, usar el generado
        if os.path.exists(logo_path):
            logo = RLImage(logo_path, width=80, height=60)
        else:
            logo = self._crear_logo_moto()

        titulo_data = [
            [Paragraph(f"<b>ORDEN DE TRABAJO No. {orden.consecutivo_ot or 'N/A'}</b>", self.styles['TituloOrden'])],
            [Paragraph(f"<b>{orden.estado_ot or 'N/A'}</b>", self.styles['TituloOrden'])],
            [Paragraph(f"Fecha de Elaboración: {self._formatear_fecha(orden.fecha_elaboracion_ot)}",
                      ParagraphStyle('FechaElaboracion', parent=self.styles['Normal'], fontSize=8, alignment=TA_RIGHT))],
            [Paragraph(f"Mecánico: {orden.mecanico or 'N/A'}",
                      ParagraphStyle('Mecanico', parent=self.styles['Normal'], fontSize=8, alignment=TA_RIGHT))]
        ]

        titulo_tabla = Table(titulo_data, colWidths=[2.5*inch])
        titulo_tabla.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        encabezado_data = [[logo, titulo_tabla]]
        encabezado_tabla = Table(encabezado_data, colWidths=[1*inch, 5.5*inch])
        encabezado_tabla.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))

        elementos.append(encabezado_tabla)
        elementos.append(Spacer(1, 0.15*inch))

        return elementos

    def _crear_info_cliente_moto(self, orden: OrdenTrabajoResponseContract) -> List:
        """Crea tabla con información del cliente y moto"""
        elementos = []

        # Formatear cliente con documento
        cliente_con_doc = f"{orden.nombre_completo_cliente or 'N/A'} - CC {orden.documento_cli or 'N/A'}"

        data = [
            ['Cliente:', cliente_con_doc, 'Teléfono:', orden.telefono_cli or 'N/A'],
            ['Dirección:', orden.direccion_cli or 'N/A', 'Ciudad:', 'MEDELLIN'],
            ['Placas:', orden.placa_mot or 'N/A', 'Marca/Modelo:', f"{orden.marca_moto or 'N/A'} {orden.modelo_mot or ''}"],
            ['Color:', orden.color_mot or 'N/A', 'Responsable:', orden.recepcionista or 'N/A'],
            ['Km:', f"{orden.kilometraje_ingreso_ot or 0:,}".replace(',', '.'), 'F. Entrega:', self._formatear_fecha(orden.fecha_entrega_ot or '')],
        ]

        tabla = Table(data, colWidths=[1*inch, 2.5*inch, 1*inch, 2.5*inch])
        tabla.setStyle(TableStyle([
            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LINEWIDTH', (0, 0), (-1, -1), 0.5),

            # Fuentes
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),

            # Negrita para etiquetas (columnas 0 y 2)
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),

            # Alineación
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elementos.append(tabla)
        elementos.append(Spacer(1, 0.1*inch))

        return elementos

    def _crear_tabla_productos(self, orden: OrdenTrabajoResponseContract) -> List:
        """Crea la tabla de productos y servicios"""
        elementos = []

        detalles = orden.detalles

        # Encabezados
        data = [[
            'Item',
            'Código',
            'Referencia',
            'Cantidad',
            'Vlr. Unit.',
            'Factur.',
            'Total'
        ]]

        # Agregar productos y calcular totales
        subtotal_total = 0  # Suma de TODOS los productos
        total_facturable = 0  # Suma solo de productos facturables

        for idx, detalle in enumerate(detalles, 1):
            nombre = detalle.nombre_pro or 'N/A'
            descripcion = detalle.descripcion_pro or ''

            # Combinar nombre y descripción con formato más pequeño para descripción
            estilo_ref = ParagraphStyle('Referencia', parent=self.styles['Normal'], fontSize=7, leading=9)

            if descripcion:
                referencia = Paragraph(
                    f"<b>{nombre}</b><br/><font size='6'>{descripcion}</font>",
                    estilo_ref
                )
            else:
                referencia = Paragraph(f"<b>{nombre}</b>", estilo_ref)

            codigo = detalle.cod_pro_deto
            cantidad_deto = detalle.cantidad_deto
            valor_unitario = detalle.valor_unitario_deto

            # Determinar si se factura según el signo de la cantidad
            se_factura = 'Si' if cantidad_deto > 0 else 'No'

            # Mostrar la cantidad sin signo (valor absoluto)
            cantidad_mostrar = abs(cantidad_deto)

            # Calcular subtotal usando valor absoluto de la cantidad
            subtotal = abs(cantidad_deto) * valor_unitario

            # Acumular al subtotal total (todos los productos)
            subtotal_total += subtotal

            # Acumular al total facturable solo si se factura
            if cantidad_deto > 0:
                total_facturable += subtotal

            data.append([
                str(idx),
                str(codigo),
                referencia,
                str(cantidad_mostrar),
                self._formatear_moneda(valor_unitario),
                se_factura,
                self._formatear_moneda(subtotal)
            ])

        # Agregar filas de totales
        data.append(['', '', '', '', '', 'SUBTOTAL:', self._formatear_moneda(subtotal_total)])
        data.append(['', '', '', '', '', 'FACTURABLE:', self._formatear_moneda(total_facturable)])

        # Crear tabla
        tabla = Table(data, colWidths=[0.4*inch, 0.7*inch, 2.8*inch, 0.7*inch, 0.9*inch, 0.8*inch, 0.9*inch])

        tabla.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0E0E0')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

            # Contenido
            ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -3), 7),
            ('ALIGN', (0, 1), (0, -3), 'CENTER'),  # Item
            ('ALIGN', (1, 1), (1, -3), 'CENTER'),  # Código
            ('ALIGN', (3, 1), (3, -3), 'CENTER'),  # Cantidad
            ('ALIGN', (4, 1), (-1, -3), 'RIGHT'),  # Valores
            ('VALIGN', (0, 1), (-1, -3), 'TOP'),

            # Filas de totales
            ('FONTNAME', (5, -2), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (5, -2), (-1, -1), 8),
            ('ALIGN', (5, -2), (-1, -1), 'RIGHT'),

            # Bordes
            ('GRID', (0, 0), (-1, -3), 0.5, colors.black),
            ('LINEABOVE', (5, -2), (-1, -2), 1, colors.black),
            ('LINEABOVE', (5, -1), (-1, -1), 1, colors.black),

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        elementos.append(tabla)
        elementos.append(Spacer(1, 0.1*inch))

        return elementos

    def _crear_observaciones(self, orden: OrdenTrabajoResponseContract) -> List:
        """Crea la sección de observaciones"""
        elementos = []

        obs_data = []

        if orden.observacion_cli_ot:
            obs_data.append(['Observaciones:', orden.observacion_cli_ot])

        if orden.observacion_ot:
            if obs_data:
                obs_data.append(['Concepto Técnico:', orden.observacion_ot])
            else:
                obs_data.append(['Concepto Técnico:', orden.observacion_ot])

        if obs_data:
            tabla = Table(obs_data, colWidths=[1.2*inch, 5.8*inch])
            tabla.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elementos.append(tabla)

        return elementos

    def generar_pdf(self, orden: OrdenTrabajoResponseContract, ruta_salida: str) -> str:
        """
        Genera un PDF con la información de la orden de trabajo

        Args:
            orden: Contrato con toda la información de la orden
            ruta_salida: Ruta completa donde se guardará el PDF

        Returns:
            str: Ruta del archivo PDF generado
        """
        # Crear directorio si no existe
        directorio = os.path.dirname(ruta_salida)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio)

        # Crear el documento con márgenes más pequeños
        doc = SimpleDocTemplate(
            ruta_salida,
            pagesize=letter,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )

        # Construir el contenido
        elementos = []

        # Agregar todas las secciones
        elementos.extend(self._crear_encabezado(orden))
        elementos.extend(self._crear_info_cliente_moto(orden))
        elementos.extend(self._crear_tabla_productos(orden))
        elementos.extend(self._crear_observaciones(orden))

        # Generar el PDF
        doc.build(elementos)

        return ruta_salida
