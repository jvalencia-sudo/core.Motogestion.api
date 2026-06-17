from domain.models.base_model import BaseSchema
from datetime import datetime
from typing import Optional


class Auth0UserModel(BaseSchema):
    picture: str
    email: str
    nickname: str
    created_at: datetime
    updated_at: datetime
    user_id: str
    name: str
    family_name: Optional[str] = None
    given_name: Optional[str] = None
