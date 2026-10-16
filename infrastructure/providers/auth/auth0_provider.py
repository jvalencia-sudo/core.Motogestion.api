import asyncio
import logging
import time
from typing import Dict, Tuple

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

# El JWKS de Auth0 casi nunca rota (solo si rotas las llaves de firma del
# tenant), así que 1h de caché es seguro y evita pegarle a Auth0 en cada
# request autenticado.
session = CachedSession("jwt_cache", backend=SQLiteCache(), expire_after=3600)

logger = logging.getLogger(__name__)

# Token M2M de la Management API: a nivel de módulo (no de instancia, que se
# crea nueva en cada llamada -- Auth0Provider() -- y perdería el caché al
# toque) porque desde que el login verifica email_verified en la Management
# API (bloqueante de seguridad), _management_login se llama en CADA login, no
# solo en acciones puntuales de administración. Sin caché, cada login pide un
# token M2M nuevo -- si se agota la cuota de tokens M2M del plan de Auth0,
# nadie puede iniciar sesión. 60s de margen para renovar antes de que venza,
# no justo al filo.
_M2M_TOKEN_CACHE: Dict[str, Tuple[str, float]] = {}
_M2M_TOKEN_MARGEN_SEGUNDOS = 60


class Auth0Provider:
    def __init__(self):
        self.config = settings.auth0_config

    async def verify(self, token: str) -> UserPermissionsModel:
        credentials_exception = HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        # session cachea la respuesta (ver expire_after arriba) y to_thread
        # evita bloquear el event loop mientras espera la respuesta HTTP.
        json_url = await asyncio.to_thread(
            session.get, f"https://{self.config.domain}/.well-known/jwks.json"
        )
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
        Obtiene (o reusa del caché de módulo) el token M2M de la Management API.

        Se cachea hasta que esté por vencer -- ver _M2M_TOKEN_CACHE arriba: sin
        esto, cada login pediría un token M2M nuevo a Auth0. client_credentials
        es una llamada HTTP síncrona (bloquea el event loop sin to_thread).

        Returns:
            str: El access token
        """
        cached = _M2M_TOKEN_CACHE.get(self.config.domain)
        if cached:
            token, vence_en = cached
            if time.monotonic() < vence_en:
                return token

        get_token = GetToken(domain=self.config.domain)
        respuesta = await asyncio.to_thread(
            get_token.client_credentials,
            self.config.client_id,
            self.config.client_secret,
            self.config.management_audience,
        )
        access_token = respuesta["access_token"]
        expira_en_segundos = respuesta.get("expires_in", 86400)
        _M2M_TOKEN_CACHE[self.config.domain] = (
            access_token,
            time.monotonic() + expira_en_segundos - _M2M_TOKEN_MARGEN_SEGUNDOS,
        )
        return access_token

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
        Obtiene la información completa de un usuario desde Auth0. Se llama en
        CADA login (no solo en acciones de administración) -- auth0_users.get
        es una llamada HTTP síncrona, así que va en to_thread para no bloquear
        el event loop mientras Auth0 responde.

        Args:
            user_id: El sub_id del usuario (Auth0 user_id)

        Returns:
            dict: Información del usuario, o None si no existe o la Management
            API no respondió (el caller debe distinguir este caso -- no es lo
            mismo que "el correo no está verificado").
        """
        try:
            token = await self._management_login()
            auth0_users = Users(domain=self.config.domain, token=token)
            return await asyncio.to_thread(auth0_users.get, user_id)
        except Exception as e:
            logger.warning("Error obteniendo info de usuario desde Auth0: %s", e)
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
