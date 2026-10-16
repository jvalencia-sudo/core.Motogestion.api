"""Fecha de HOY en América/Bogotá, sin depender de la zona horaria del
proceso/contenedor que corre el backend.

`date.today()` resuelve contra el reloj del SISTEMA -- en producción, el
contenedor del backend corre en UTC (a diferencia de Postgres, que sí tiene
`-c timezone=America/Bogota` fijado explícitamente, ver docker-compose*.y*ml).
Entre las 7pm y la medianoche en Bogotá (UTC-5), UTC ya muestra el día
siguiente: cualquier lógica de negocio sensible a la fecha (días restantes de
suscripción, vencimiento de pruebas, etc.) que use `date.today()` a secas
puede "creer" que ya es un día que en Bogotá todavía no llegó.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

ZONA_BOGOTA = ZoneInfo("America/Bogota")


def hoy_bogota() -> date:
    return datetime.now(ZONA_BOGOTA).date()
