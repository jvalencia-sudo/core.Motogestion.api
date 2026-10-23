# Imagen multi-arquitectura (amd64 y arm64): python:3.11-slim y uv publican ambas.
FROM python:3.11-slim

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Librerías nativas de WeasyPrint (rediseño del PDF de orden de trabajo):
# Pango/cairo/gdk-pixbuf. Nombres verificados contra la imagen real
# python:3.11-slim (Debian 13 "trixie") -- libgdk-pixbuf2.0-0 ya no existe
# en trixie, el paquete se renombró a libgdk-pixbuf-2.0-0.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 libcairo2 libffi8 shared-mime-info fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY pyproject.toml uv.lock ./

# Instalar dependencias usando uv (sin grupo dev)
RUN uv sync --frozen --no-cache --no-dev

# Copiar el resto del código
COPY . .

# Usar el venv directamente (sin `uv run`, que re-sincroniza al arrancar)
ENV PATH="/app/.venv/bin:$PATH"

# Exponer el puerto que usa la aplicación
EXPOSE 8000

# Detrás de un proxy inverso (Caddy): confiar en X-Forwarded-* para que los
# redirects y request.url salgan con https. Es seguro porque el contenedor no
# publica puertos: solo el proxy puede alcanzarlo.
# --no-access-log: uvicorn logueaba cada request en texto plano con la ruta
# RESUELTA (incluye documentos/placas reales) -- infrastructure/middleware/
# request_logging.py ya cubre esa misma información, pero con la plantilla de
# ruta en vez del valor real.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log"]
