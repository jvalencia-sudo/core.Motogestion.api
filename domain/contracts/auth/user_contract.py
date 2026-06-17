from enum import Enum
from typing import List, Optional

from pydantic import EmailStr
from domain.models.base_model import BaseSchema
import secrets
from infrastructure.commons.enums.user import UserTypeEnum


class UserCreationContract(BaseSchema):
    name: str
    email: EmailStr
    sub_id_usu: str
    is_creation: bool = False
    password: Optional[str] = secrets.token_urlsafe(16)
    user_type: UserTypeEnum = UserTypeEnum.CUSTOMER
    documento_usu: str
    nombre_usu: str
    apellido_1_usu: str
    apellido_2_usu: Optional[str] = None
    cod_prf_usu:int
    cod_rol_prf_usu:int

    def split_name(self) -> tuple[str, str, str]:
        """Divide el name en nombre, apellido_1 y apellido_2"""
        parts = self.name.strip().split()
        if len(parts) == 1:
            return parts[0], "Sin Apellido", ""
        elif len(parts) == 2:
            return parts[0], parts[1], ""
        elif len(parts) >= 3:
            nombre = parts[0]
            apellido_1 = parts[1]
            apellido_2 = " ".join(parts[2:])
            return nombre, apellido_1, apellido_2
        else:
            return "Usuario", "Sin Apellido", ""


class UserUpdateContract(BaseSchema):
    name: str
    email: str
    user_type: UserTypeEnum
    customer_id: Optional[int]
    business_ids: Optional[List[int]]
    user_id: Optional[int] = None
    sub_id_usu: Optional[str] = None

    # Campos adicionales para la BD Oracle
    documento_usu: Optional[str] = None
    nombre_usu: Optional[str] = None
    apellido_1_usu: Optional[str] = None
    apellido_2_usu: Optional[str] = None
