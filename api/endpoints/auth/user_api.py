from typing import List

from fastapi import APIRouter, Depends, Response
from starlette.status import HTTP_204_NO_CONTENT, HTTP_201_CREATED

from domain.contracts.auth.login_contract import LoginContract
from domain.contracts.auth.user_contract import (
    UserCreationContract,
    UserUpdateContract,
    InviteUsuarioContract,
)
from domain.models.auth.user_model import UserModel
from domain.models.providers.auth0_user import Auth0UserModel
from domain.services.auth.user_service import UserService
from infrastructure.dependencies.current_user import require_admin

router = APIRouter()


@router.get("", response_model=List[UserModel])
async def get():
    return await UserService().get_all()


@router.post("/login")
async def login(request: LoginContract):
    return await UserService().login(request)


@router.post("/invitar", status_code=HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def invitar_usuario(contract: InviteUsuarioContract):
    """Invita un miembro al taller del usuario autenticado (pre-registrado por correo).

    Solo un Admin del taller puede invitar.
    """
    return await UserService().invitar(contract)


@router.get("/auth_users", response_model=List[Auth0UserModel])
async def get_all_users_from_auth_provider():
    return await UserService().get_all_users_from_auth_provider()


@router.post("", status_code=HTTP_204_NO_CONTENT, response_class=Response)
async def create(user: UserCreationContract):
    await UserService().create_or_add_user(user, login=False)


@router.post("", status_code=HTTP_204_NO_CONTENT, response_class=Response)
async def create_user(user:UserCreationContract):
    await UserService().create_or_add_user(user)



@router.put("/{user_id}")
async def update_user(user_id: str, user: UserUpdateContract):
    return await UserService().update_user(user_id=user_id, user=user)
