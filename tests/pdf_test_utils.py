"""Helpers compartidos por los tests de generación de PDF (no es un módulo de
tests: pytest no lo recolecta porque no termina en "_test.py")."""
import base64
import re
import zlib


_GRUPO_PARENTESIS = re.compile(rb"\(((?:[^()\\]|\\.)*)\)")


def _desescapar(cadena: bytes) -> bytes:
    """Deshace el escape mínimo de PDF dentro de un literal string: \\( \\) \\\\."""
    return cadena.replace(rb"\(", b"(").replace(rb"\)", b")").replace(rb"\\", b"\\")


def texto_visible_del_pdf(pdf_bytes: bytes) -> str:
    """Decodifica los content streams del PDF (reportlab los deja en
    ASCII85+FlateDecode por defecto) y extrae solo el texto que de verdad se
    dibuja en la página (los literales entre paréntesis de los operadores
    Tj/TJ), no los operadores de PDF alrededor -- así una frase partida en
    varias líneas de dibujo se puede buscar como un solo texto continuo."""
    palabras = []
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
        palabras.extend(_desescapar(g) for g in _GRUPO_PARENTESIS.findall(bloque))
    return b" ".join(palabras).decode("latin-1")
