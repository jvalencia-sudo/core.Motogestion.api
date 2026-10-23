"""Helpers compartidos por los tests de generación de PDF (no es un módulo de
tests: pytest no lo recolecta porque no termina en "_test.py")."""
import io
import re

from pypdf import PdfReader


def texto_visible_del_pdf(pdf_bytes: bytes) -> str:
    """Extrae el texto que de verdad se dibuja en la página. Sirve tanto
    para los PDF de ReportLab (texto en literales simples) como para los de
    WeasyPrint (fuentes embebidas tipo CID, cadenas hexadecimales) -- pypdf
    entiende ambas codificaciones, a diferencia de un parseo manual del
    content stream.

    pypdf conserva los saltos de línea visuales del texto envuelto, así que
    una frase que se parte en dos líneas en el PDF queda con un "\\n" en
    medio -- se colapsa todo el espacio en blanco a un solo espacio para que
    comparar contra un texto esperado de una sola línea siga funcionando."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    texto = " ".join(page.extract_text() for page in reader.pages)
    return re.sub(r"\s+", " ", texto)
