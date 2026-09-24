"""resolve_tenant/_apply_tenant son el aislamiento entre talleres: si esto falla,
un taller puede terminar viendo datos de otro (el RLS de Postgres confía en que
app.tenant_id quede bien puesto)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from infrastructure.dependencies.tenant_request import resolve_tenant
from infrastructure.utils.tenant_context import get_tenant, set_tenant
from repository.data.database import _apply_tenant


def _request_con_header(valor_authorization=""):
    return SimpleNamespace(headers={"authorization": valor_authorization} if valor_authorization else {})


async def test_sin_authorization_header_deja_tenant_en_none():
    set_tenant(999)  # contamina el contexto a propósito para probar que se limpia
    await resolve_tenant(_request_con_header())
    assert get_tenant() is None


async def test_header_sin_bearer_deja_tenant_en_none():
    await resolve_tenant(_request_con_header("Basic algo"))
    assert get_tenant() is None


async def test_token_valido_con_taller_fija_el_tenant_correcto():
    auth_user = SimpleNamespace(user_id="auth0|abc123")
    with patch(
        "infrastructure.dependencies.tenant_request.Auth0Provider.verify",
        new=AsyncMock(return_value=auth_user),
    ), patch(
        "infrastructure.dependencies.tenant_request.IdentidadRepositorio.get_taller_by_sub",
        new=AsyncMock(return_value=7),
    ):
        await resolve_tenant(_request_con_header("Bearer un-token-valido"))

    assert get_tenant() == 7


async def test_token_valido_pero_usuario_sin_taller_deja_tenant_en_none():
    auth_user = SimpleNamespace(user_id="auth0|sin-taller")
    with patch(
        "infrastructure.dependencies.tenant_request.Auth0Provider.verify",
        new=AsyncMock(return_value=auth_user),
    ), patch(
        "infrastructure.dependencies.tenant_request.IdentidadRepositorio.get_taller_by_sub",
        new=AsyncMock(return_value=None),
    ):
        await resolve_tenant(_request_con_header("Bearer un-token-valido"))

    assert get_tenant() is None


async def test_token_invalido_no_deja_el_tenant_anterior_puesto():
    """Caso crítico: si verify() lanza (token vencido/manipulado), el tenant NO
    debe quedar con el valor de una petición anterior en el mismo worker."""
    set_tenant(5)  # simula el tenant que dejó una petición anterior
    with patch(
        "infrastructure.dependencies.tenant_request.Auth0Provider.verify",
        new=AsyncMock(side_effect=Exception("token inválido")),
    ):
        await resolve_tenant(_request_con_header("Bearer token-vencido"))

    assert get_tenant() is None


async def test_apply_tenant_sin_tenant_en_contexto_usa_taller_inexistente():
    """Sin tenant resuelto, debe fijar un taller que no existe (-1) para que el
    RLS no devuelva filas, en vez de fallar o -peor- no filtrar nada."""
    set_tenant(None)
    cursor = AsyncMock()
    await _apply_tenant(cursor)
    cursor.execute.assert_awaited_once_with(
        "SELECT set_config('app.tenant_id', %s, true)", ("-1",)
    )


async def test_apply_tenant_con_tenant_resuelto_lo_pasa_como_string():
    set_tenant(42)
    cursor = AsyncMock()
    await _apply_tenant(cursor)
    cursor.execute.assert_awaited_once_with(
        "SELECT set_config('app.tenant_id', %s, true)", ("42",)
    )
    set_tenant(None)
