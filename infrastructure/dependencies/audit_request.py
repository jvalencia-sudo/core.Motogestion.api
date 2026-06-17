import json

from fastapi import BackgroundTasks
from fastapi import Request

from domain.models.auth.audit_model import AuditModel
from domain.models.auth.user_model import UserModel
from domain.services.auth.audit_service import AuditService


async def save_audit(service: AuditService, model: AuditModel):
    await service.create(model)


async def audit_request(
    background_tasks: BackgroundTasks,
    request: Request,
    user: UserModel,
    service: AuditService,
):
    if request.method is not None and request.method.lower() in [
        "post",
        "delete",
        "put",
    ]:
        background_tasks.add_task(
            save_audit,
            service,
            AuditModel(
                user_id=user.user_id,
                payload=json.dumps(
                    await request.json()
                    if request.method.lower() in ["post", "put"]
                    else {"id": request.url.query}
                ),
                url=request.url.path,
            ),
        )
