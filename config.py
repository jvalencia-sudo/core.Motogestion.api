from typing import Optional
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseSettingModel(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class DbConfig(BaseSettingModel):
    host: str = Field(..., alias="DB_HOST")
    port: int = Field(5432, alias="DB_PORT")  # Puerto por defecto de PostgreSQL
    user: str = Field(..., alias="DB_USER")
    password: str = Field(..., alias="DB_PASSWORD")
    dbname: str = Field(..., alias="DB_NAME")


class Auth0Config(BaseSettingModel):
    domain: str = Field(..., alias="AUTH0_DOMAIN")
    algorithms: str = Field(..., alias="AUTH0_ALGORITHMS")
    api_audience: str = Field(..., alias="AUTH0_API_AUDIENCE")
    client_id: str = Field(..., alias="AUTH0_MANAGEMENT_CLIENT_ID")
    client_secret: str = Field(..., alias="AUTH0_MANAGEMENT_CLIENT_SECRET")
    management_audience: str = Field(..., alias="AUTH0_MANAGEMENT_AUDIENCE")
    connection_id: str = Field(..., alias="AUTH0_CONNECTION_ID")
    customer_role: str = Field(..., alias="AUTH0_CUSTOMER_ROLE")
    admin_role: str = Field(..., alias="AUTH0_ADMIN_ROLE")


class AwsConfig(BaseSettingModel):
    bucket_name: str = Field(..., alias="S3_BUCKET")


class QuotationConfig(BaseSettingModel):
    national_url: str = Field(..., alias="NATIONAL_QUOTATION_URL")
    international_url: str = Field(..., alias="INTERNATIONAL_QUOTATION_URL")


class SapConfig(BaseSettingModel):
    pending_orders_url: str = Field(..., alias="SAP_PENDING_ORDERS_URL")
    username: str = Field(..., alias="SAP_USERNAME")
    password: str = Field(..., alias="SAP_PASSWORD")
    base_dev_url: str = Field(..., alias="SAP_BASE_DEV_URL")
    base_prd_url: str = Field(..., alias="SAP_BASE_PRD_URL")


class WompiConfig(BaseSettingModel):
    # Opcionales: si no hay llaves, la app arranca igual y el checkout responde
    # "pagos no configurados" en vez de romper el arranque.
    public_key: str = Field("", alias="WOMPI_PUBLIC_KEY")
    private_key: str = Field("", alias="WOMPI_PRIVATE_KEY")
    events_secret: str = Field("", alias="WOMPI_EVENTS_SECRET")
    integrity_secret: str = Field("", alias="WOMPI_INTEGRITY_SECRET")
    checkout_url: str = Field("https://checkout.wompi.co/p/", alias="WOMPI_CHECKOUT_URL")
    base_url: str = Field("https://sandbox.wompi.co/v1", alias="WOMPI_BASE_URL")

    @property
    def configurado(self) -> bool:
        return bool(self.public_key and self.integrity_secret and self.events_secret)


class Settings(BaseSettingModel):
    environment: str
    project_name: str
    api_url: str = "/api"
    docs_url: Optional[str] = "/docs"
    db_config: DbConfig = DbConfig()
    auth0_config: Auth0Config = Auth0Config()
    wompi_config: WompiConfig = WompiConfig()
    #aws_config: AwsConfig = AwsConfig()
    #quotation_config: QuotationConfig = QuotationConfig()
    #sap_config: SapConfig = SapConfig()
    # Orígenes permitidos por CORS. `cors_origins` es una lista separada por comas
    # (env CORS_ORIGINS); `allowed_origin` se mantiene por compatibilidad.
    cors_origins: str = ""
    allowed_origin: str = ""
    frontend_url: str

    @property
    def cors_allowed_origins(self) -> list[str]:
        """Une CORS_ORIGINS y allowed_origin sin vacíos, sin '/' final y sin duplicados."""
        raw = [*self.cors_origins.split(","), self.allowed_origin]
        origins = [o.strip().rstrip("/") for o in raw]
        return list(dict.fromkeys(o for o in origins if o))

    @field_validator("docs_url")
    def none_docs_url(cls, v, info: ValidationInfo):
        if info.data.get("environment") != "dev":
            return None
        return v


settings = Settings()
