from enum import Enum


class WarrantyStatusEnum(str, Enum):
    VIGENTE = "VIGENTE"
    VENCIDA = "VENCIDA"
    SIN_INFORMACION = "SIN INFORMACIÓN"
