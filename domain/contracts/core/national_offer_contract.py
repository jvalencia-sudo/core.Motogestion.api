from datetime import datetime
from typing import Optional, List

from domain.contracts.base_contract import BaseContractSchema


class NationalOfferLocationContract(BaseContractSchema):
    location_id: int
    location_name: str
    address: str
    tariff: float


class NationalOfferDetailContract(BaseContractSchema):
    offer_code: Optional[str] = None
    offer_id: Optional[int] = None
    valid_until: datetime
    free_loading: bool
    availability_requested_date: bool
    load_date: Optional[datetime] = None
    locations: List[NationalOfferLocationContract]
    total_tariff: float
    currency_id: int
    currency_name: str
    observation: str | None = None


class NationalOfferContract(BaseContractSchema):
    quotations: List[NationalOfferDetailContract]
