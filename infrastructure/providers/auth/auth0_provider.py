import requests
from auth0.v3.authentication import GetToken
from auth0.v3.management import Users, UsersByEmail
from fastapi import HTTPException
from jose import jwt
from requests_cache import CachedSession, SQLiteCache
from starlette.status import HTTP_401_UNAUTHORIZED

from config import settings
from domain.contracts.auth.user_contract import UserCreationContract
from domain.models.auth.user_model import UserPermissionsModel
from domain.models.providers.auth0_user import Auth0UserModel

session = CachedSession("jwt_cache", backend=SQLiteCache(), expire_after=60)


class Auth0Provider:
    def __init__(self):
        self.config = settings.auth0_config

    async def verify(self, token: str) -> UserPermissionsModel:
        credentials_exception = HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        # TODO: Ad cache again
        json_url = requests.get(f"https://{self.config.domain}/.well-known/jwks.json")
        jwks = json_url.json()

        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=[self.config.algorithms],
                audience=self.config.api_audience,
                issuer=f"https://{self.config.domain}/",
            )
        except Exception:
            raise credentials_exception

        return UserPermissionsModel(
            user_id=payload.get("sub", ""), permissions=payload.get("permissions")
        )

    async def _management_login(self) -> str:
        """
        Private method to login to the Auth0 Management API.

        This method is used to obtain an access token to call the Auth0 Management API.
        The access token is obtained using the client credentials flow.

        Returns:
            str: The access token
        """
        get_token = GetToken(domain=self.config.domain)
        print("{}://{}/oauth/token".format("https", self.config.domain))
        token = get_token.client_credentials(
            self.config.client_id,
            self.config.client_secret,
            self.config.management_audience,
        )
        return token["access_token"]

    async def get_users(self):
        token = await self._management_login()
        auth0 = Users(domain=self.config.domain, token=token)
        users = []
        auth0_users = auth0.list(per_page=100)
        users.extend(auth0_users["users"])
        current_page = 0
        while len(users) < auth0_users["total"]:
            current_page += 1
            auth0_users = auth0.list(per_page=100, page=current_page)
            users.extend(auth0_users["users"])

        return users

    async def assign_customer_role(self, user_id: str):
        token = await self._management_login()
        auth0 = Users(domain=self.config.domain, token=token)
        auth0.add_roles(user_id, [self.config.customer_role])

    async def assign_admin_role(self, user_id: str):
        token = await self._management_login()
        auth0 = Users(domain=self.config.domain, token=token)
        auth0.add_roles(user_id, [self.config.admin_role])

    async def create_user(
        self, contract: UserCreationContract
    ) -> Auth0UserModel | None:
        token = await self._management_login()
        auth0_users = Users(domain=self.config.domain, token=token)
        auth0_users_by_email = UsersByEmail(domain=self.config.domain, token=token)

        # First check if user exists by email
        existing_users = auth0_users_by_email.search_users_by_email(
            email=contract.email
        )
        if existing_users:
            return Auth0UserModel.model_validate(existing_users[0])

        # If user doesn't exist, create new one
        auth0_users.create(
            {
                "email": contract.email,
                "name": contract.name,
                "password": contract.password,
                "connection": self.config.connection_id,
            }
        )

        # Get the newly created user
        auth0_user = auth0_users_by_email.search_users_by_email(email=contract.email)
        if auth0_user:
            return Auth0UserModel.model_validate(auth0_user[0])
        return None

    async def reset_password(self, user_id: str, new_password: str) -> bool:
        """
        Resetea la contraseña de un usuario en Auth0

        Args:
            user_id: El sub_id del usuario (Auth0 user_id)
            new_password: La nueva contraseña

        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            token = await self._management_login()
            auth0_users = Users(domain=self.config.domain, token=token)

            auth0_users.update(
                user_id,
                {
                    "password": new_password
                }
            )
            return True
        except Exception as e:
            print(f"Error resetting password in Auth0: {str(e)}")
            return False

    async def delete_user(self, user_id: str) -> bool:
        """
        Elimina un usuario de Auth0

        Args:
            user_id: El sub_id del usuario (Auth0 user_id)

        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            token = await self._management_login()
            auth0_users = Users(domain=self.config.domain, token=token)
            auth0_users.delete(user_id)
            return True
        except Exception as e:
            print(f"Error deleting user from Auth0: {str(e)}")
            return False

    async def get_user_info(self, user_id: str) -> dict | None:
        """
        Obtiene la información completa de un usuario desde Auth0

        Args:
            user_id: El sub_id del usuario (Auth0 user_id)

        Returns:
            dict: Información del usuario o None si no existe
        """
        try:
            token = await self._management_login()
            auth0_users = Users(domain=self.config.domain, token=token)
            user_info = auth0_users.get(user_id)
            return user_info
        except Exception as e:
            print(f"Error getting user info from Auth0: {str(e)}")
            return None

    async def update_user_email(self, user_id: str, new_email: str) -> bool:
        """
        Actualiza el email de un usuario en Auth0

        Args:
            user_id: El sub_id del usuario (Auth0 user_id)
            new_email: El nuevo email

        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            token = await self._management_login()
            auth0_users = Users(domain=self.config.domain, token=token)

            auth0_users.update(
                user_id,
                {
                    "email": new_email
                }
            )
            return True
        except Exception as e:
            print(f"Error updating email in Auth0: {str(e)}")
            return False
