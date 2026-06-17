from datetime import datetime
from typing import List, Optional

from domain.contracts.base_contract import BaseContractSchema


class InternationalOfferDetailContract(BaseContractSchema):
    offer_id: Optional[int] = None
    incoterm_id: int
    currency_id: int
    currency_name: str
    offer_code: Optional[str] = None
    valid_until: datetime
    transit_time: int
    transshipment: bool
    free_days: int
    tariff: float
    free_loading: Optional[bool] = None
    observation: Optional[str] = None
    transporter: str
    min: Optional[float] = None
    amount: float
    wm: Optional[float] = None
    imo: float
    container_size_20: Optional[float] = None
    container_size_40: Optional[float] = None
    freight_percentage: float
    document_bl: float
    preparation_fee_bl: float
    mounting_dismounting: float
    food_grade: float
    positioning: float
    thc_origin: float
    special_handling: float
    vgm: float
    custom_ams: float
    consolidation_lcl: float
    destination_bl: float
    destination_cont: float
    free_days_destination: int


class InternationalOfferItemContract(BaseContractSchema):
    location_id: int
    location_name: str
    address: str
    quotations: List[InternationalOfferDetailContract]


class InternationalOfferContract(BaseContractSchema):
    locations: List[InternationalOfferItemContract]
