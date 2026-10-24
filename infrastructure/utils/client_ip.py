from starlette.requests import Request


def ip_cliente(request: Request) -> str:
    """IP real del visitante detrás de Caddy (deploy/Caddyfile hace
    reverse_proxy, que por defecto AGREGA el IP real al final de
    X-Forwarded-For sin importar lo que el cliente ya mandara ahí -- por eso
    se toma el ÚLTIMO valor, no el primero, que sí podría venir falsificado
    por el visitante). Usado como key_func del rate limit de los endpoints
    públicos y para la constancia de aprobación de cotización (F2-03). Sin
    ese encabezado (dev local, tests), cae a request.client.host."""
    adelante = request.headers.get("x-forwarded-for")
    if adelante:
        partes = [p.strip() for p in adelante.split(",") if p.strip()]
        if partes:
            return partes[-1]
    return request.client.host if request.client else "desconocido"
