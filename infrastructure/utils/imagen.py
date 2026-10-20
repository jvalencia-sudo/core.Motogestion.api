import io

from PIL import Image

# F1-09: formatos de logo aceptados. SVG queda excluido a propósito (es XML,
# no un raster -- Image.open tampoco lo decodifica, pero el content-type se
# valida primero para no gastar tiempo decodificando algo ya rechazado).
TIPOS_LOGO_PERMITIDOS = {"image/png", "image/jpeg", "image/webp"}
LOGO_MAX_BYTES = 2 * 1024 * 1024  # 2MB
LOGO_LADO_MAX_PX = 400  # suficiente para un logo de encabezado, tope de tamaño guardado


def redimensionar_logo(contenido: bytes) -> bytes:
    """Valida que `contenido` sea una imagen rasterizada real (no solo que el
    content-type lo diga -- un archivo puede venir mal etiquetado) y la
    redimensiona a un máximo de LOGO_LADO_MAX_PX por lado, preservando la
    relación de aspecto. Siempre devuelve PNG (re-codificar también descarta
    cualquier payload no-imagen que viniera incrustado en el archivo original).

    Raises:
        ValueError: si `contenido` no es una imagen decodificable.
    """
    try:
        imagen = Image.open(io.BytesIO(contenido))
        imagen.load()
    except OSError as exc:
        raise ValueError("El archivo no es una imagen válida") from exc

    if imagen.mode not in ("RGB", "RGBA"):
        imagen = imagen.convert("RGBA")

    imagen.thumbnail((LOGO_LADO_MAX_PX, LOGO_LADO_MAX_PX), Image.LANCZOS)

    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
