from domain.models.base_model import BaseSchema


class MotoModelo(BaseSchema):
    placa_mot: str  # Primary key
    modelo_mot: int
    color_mot: str
    cilindraje_mot: int
    documento_cli_mot: str  # Foreign key to clientes
    cod_marca_mot: int  # Foreign key to marcas
