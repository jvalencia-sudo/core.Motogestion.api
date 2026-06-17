from infrastructure.providers.auth.auth0_provider import Auth0Provider


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
