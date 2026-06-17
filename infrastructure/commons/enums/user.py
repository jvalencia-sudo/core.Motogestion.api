from enum import Enum


class UserTypeEnum(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
