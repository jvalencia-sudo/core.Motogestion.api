# Imagen multi-arquitectura (amd64 y arm64): python:3.11-slim y uv publican ambas.
FROM python:3.11-slim

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

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
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
