from fastapi import APIRouter, Depends
from starlette.status import HTTP_201_CREATED

from domain.contracts.auth.login_contract import LoginContract
from domain.contracts.auth.user_contract import InviteUsuarioContract
from domain.contracts.shared.respuesta_contract import InvitacionResponseContract
from domain.models.auth.user_model import UserWithPermissionsModel
from domain.services.auth.user_service import UserService
from infrastructure.dependencies.current_user import require_admin

router = APIRouter()


@router.post("/login", response_model=UserWithPermissionsModel)
async def login(request: LoginContract):
    return await UserService().login(request)


@router.post(
    "/invitar",
    status_code=HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    response_model=InvitacionResponseContract,
)
async def invitar_usuario(contract: InviteUsuarioContract):
    """Invita un miembro al taller del usuario autenticado (pre-registrado por correo).

    Solo un Admin del taller puede invitar.
    """
    return await UserService().invitar(contract)
