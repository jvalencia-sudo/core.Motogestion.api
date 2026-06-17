from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditModel(BaseModel):
    audit_id: int = 0
    user_id: Optional[int]
    url: Optional[str]
    creation_date: Optional[datetime] = datetime.now()
    payload: Optional[str]
