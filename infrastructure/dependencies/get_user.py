from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from starlette.status import HTTP_401_UNAUTHORIZED

from domain.models.auth.user_model import UserPermissionsModel
from infrastructure.providers.auth.auth0_provider import Auth0Provider

oauth2_scheme = HTTPBearer()


async def get_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
) -> UserPermissionsModel:
    try:
        return await Auth0Provider().verify(token.credentials)
    except Exception:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
