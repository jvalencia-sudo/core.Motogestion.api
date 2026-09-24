import os

import pytest

from infrastructure.providers.auth.auth0_provider import Auth0Provider

# Estos dos hacen llamadas reales a la Management API de Auth0 (login M2M +
# listar usuarios del tenant real) con las credenciales del .env local. No hay
# secrets de Auth0 en el runner de CI a propósito (no tiene sentido pegarle al
# tenant real en cada push), así que se saltan ahí. Localmente, con un .env
# real, siguen corriendo como test de integración real.
requiere_auth0_real = pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="requiere credenciales reales de Auth0 Management API (no disponibles en CI)",
)


@requiere_auth0_real
class TestAuth0Provider:
    async def test_management_login_must_return_token(self):
        provider = Auth0Provider()

        token = await provider._management_login()
        assert token is not None

    async def test_get_users_must_return_users(self):
        provider = Auth0Provider()

        users = await provider.get_users()
        print(len(users))
        print(users[0])
        assert len(users) > 0
