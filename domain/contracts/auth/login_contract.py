from pydantic.main import BaseModel


class LoginContract(BaseModel):
    email: str
    token: str
    name: str


class LoginByPassContract(BaseModel):
    email: str
    password: str

class RegisterContract(BaseModel):
    email: str
    password: str

