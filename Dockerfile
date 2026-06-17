# Usar imagen base oficial de Python
FROM python:3.11-slim

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY pyproject.toml uv.lock ./

# Instalar dependencias usando uv
RUN uv sync --frozen --no-cache

# Copiar el resto del código
COPY . .

# Exponer el puerto que usa la aplicación
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

