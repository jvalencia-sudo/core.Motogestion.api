"""actualizar() arma el UPDATE interpolando los nombres de columna directo en el
SQL (no son parámetros). Hoy 'campos' siempre sale de un Pydantic model fijo, así
que las claves están controladas — pero si eso cambia algún día, este test debe
notarlo: congela el contrato de qué SQL se genera y con qué parámetros."""
from unittest.mock import AsyncMock

from repository.talleres.taller_repositorio import TallerRepositorio


async def test_actualizar_arma_update_solo_con_los_campos_provistos():
    repo = TallerRepositorio()
    repo.db = AsyncMock()

    await repo.actualizar(7, {"nombre_tal": "Taller Nuevo", "correo_tal": "a@b.com"})

    repo.db.execute_non_query.assert_awaited_once_with(
        "UPDATE talleres SET nombre_tal = :1, correo_tal = :2 WHERE cod_taller = :3",
        ("Taller Nuevo", "a@b.com", 7),
    )


async def test_actualizar_con_un_solo_campo():
    repo = TallerRepositorio()
    repo.db = AsyncMock()

    await repo.actualizar(3, {"estado_tal": "activo"})

    repo.db.execute_non_query.assert_awaited_once_with(
        "UPDATE talleres SET estado_tal = :1 WHERE cod_taller = :2",
        ("activo", 3),
    )


async def test_actualizar_sin_campos_no_toca_la_base_de_datos():
    """Evita un UPDATE ... SET WHERE ... inválido (o un no-op costoso) si algún
    caller llega con un dict vacío."""
    repo = TallerRepositorio()
    repo.db = AsyncMock()

    await repo.actualizar(7, {})

    repo.db.execute_non_query.assert_not_called()
