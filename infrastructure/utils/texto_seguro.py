from xml.sax.saxutils import escape


def texto_seguro(valor) -> str:
    """Escapa un valor para que se pueda interpolar sin riesgo dentro del
    marcado de un reportlab.platypus.Paragraph.

    Paragraph interpreta un mini-lenguaje tipo XML (<b>, <font>, <img>, ...).
    Un dato de usuario sin escapar puede romper ese parseo (p.ej. un "<" o
    "&" sueltos) o, peor, ser interpretado como una etiqueta real: <img
    src="..."/> hace que reportlab intente abrir ese archivo/URL como
    imagen -- una ruta local legible por el proceso o una URL externa.
    """
    return escape(str(valor or ""))
