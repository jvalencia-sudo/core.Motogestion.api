from fastapi import APIRouter, Depends
from starlette.status import HTTP_201_CREATED

from domain.contracts.auth.login_contract import LoginContract
from domain.contracts.auth.user_contract import InviteUsuarioContract
from domain.services.auth.user_service import UserService
from infrastructure.dependencies.current_user import require_admin

router = APIRouter()


@router.post("/login")
async def login(request: LoginContract):
    return await UserService().login(request)


@router.post("/invitar", status_code=HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def invitar_usuario(contract: InviteUsuarioContract):
    """Invita un miembro al taller del usuario autenticado (pre-registrado por correo).

    Solo un Admin del taller puede invitar.
    """
    return await UserService().invitar(contract)
