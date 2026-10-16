"""F0-14 corrección 6: hoy_bogota() no debe depender de la zona horaria del
proceso -- entre las 7pm y la medianoche en Bogotá (UTC-5), UTC ya muestra el
día siguiente."""
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from infrastructure.utils.fecha_bogota import ZONA_BOGOTA, hoy_bogota


def test_hoy_bogota_a_las_9pm_no_es_el_dia_siguiente_de_utc():
    # 2026-03-11 02:00 UTC == 2026-03-10 21:00 en Bogotá (UTC-5): en Bogotá
    # todavía es 10 de marzo, aunque en UTC el reloj ya marque 11.
    instante_utc = datetime(2026, 3, 11, 2, 0, tzinfo=ZoneInfo("UTC"))
    with patch("infrastructure.utils.fecha_bogota.datetime") as mock_dt:
        mock_dt.now.side_effect = lambda tz: instante_utc.astimezone(tz)
        resultado = hoy_bogota()
    mock_dt.now.assert_called_once_with(ZONA_BOGOTA)
    assert resultado == date(2026, 3, 10)
