from typing import Dict

from domain.models.auth.audit_model import AuditModel
from domain.services.base_service import BaseService
from repository.base_repository import BaseRepository


class AuditService(BaseService[AuditModel, None]):
    def __init__(self):
        super().__init__(BaseRepository("auth", "audit", "audit_id"))

    def __parse__(self, record: Dict) -> AuditModel:
        return AuditModel.model_validate(record)
