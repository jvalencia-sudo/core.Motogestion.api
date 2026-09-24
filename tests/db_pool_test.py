"""El RLS (FORCE ROW LEVEL SECURITY) solo aísla datos si el rol de BD no es
superusuario ni tiene BYPASSRLS. _verificar_rol_no_privilegiado() es el chequeo que
evita que un despliegue con el rol equivocado arranque sin que nadie lo note."""
import pytest
from unittest.mock import AsyncMock

from repository.data.db_pool import _verificar_rol_no_privilegiado


def _cursor_con(rolsuper: bool, rolbypassrls: bool) -> AsyncMock:
    cursor = AsyncMock()
    cursor.fetchone.return_value = (rolsuper, rolbypassrls)
    return cursor


async def test_rechaza_rol_superusuario():
    cursor = _cursor_con(rolsuper=True, rolbypassrls=False)

    with pytest.raises(RuntimeError, match="anula el RLS"):
        await _verificar_rol_no_privilegiado(cursor)


async def test_rechaza_rol_con_bypassrls():
    cursor = _cursor_con(rolsuper=False, rolbypassrls=True)

    with pytest.raises(RuntimeError, match="anula el RLS"):
        await _verificar_rol_no_privilegiado(cursor)


async def test_rechaza_rol_con_ambos_privilegios():
    cursor = _cursor_con(rolsuper=True, rolbypassrls=True)

    with pytest.raises(RuntimeError, match="anula el RLS"):
        await _verificar_rol_no_privilegiado(cursor)


async def test_permite_rol_sin_privilegios():
    cursor = _cursor_con(rolsuper=False, rolbypassrls=False)

    await _verificar_rol_no_privilegiado(cursor)

    cursor.execute.assert_awaited_once()
