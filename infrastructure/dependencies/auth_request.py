from typing import List, Optional

from fastapi import Depends, BackgroundTasks, Request
from starlette.status import HTTP_403_FORBIDDEN

from domain.models.auth.user_model import UserPermissionsModel
from domain.services.auth.audit_service import AuditService
from infrastructure.dependencies.get_user import get_user
from infrastructure.exceptions.domain_exception import DomainException


class AuthRequest:
    def __init__(self, permissions: Optional[List[str]] = None):
        self.permissions = permissions if permissions else []

    async def __call__(
        self,
        background_tasks: BackgroundTasks,
        request: Request,
        user: UserPermissionsModel = Depends(get_user),
        service: AuditService = Depends(),
    ):
        if len(self.permissions) > 0:
            allowed_permissions = []
            for p in self.permissions:
                if user.permissions != None and p in [up for up in user.permissions]:
                    allowed_permissions.append(p)

            if len(allowed_permissions) == 0:
                raise DomainException("Access denied", HTTP_403_FORBIDDEN)

        # await audit_request(background_tasks, request, user, service)
