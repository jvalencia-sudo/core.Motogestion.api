from decimal import Decimal
from domain.models.base_model import BaseSchema


class PaqueteComponenteModelo(BaseSchema):
    """Un componente de la 'receta' de un paquete (producto tipo PAQUETE)."""
    cod_paq_comp: int = 0
    cod_pro_paq: int          # el paquete
    cod_pro_comp: int         # el producto incluido
    cantidad_comp: Decimal
