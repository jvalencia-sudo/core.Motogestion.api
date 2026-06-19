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


class Settings(BaseSettingModel):
    environment: str
    project_name: str
    api_url: str = "/api"
    docs_url: Optional[str] = "/docs"
    db_config: DbConfig = DbConfig()
    auth0_config: Auth0Config = Auth0Config()
    #aws_config: AwsConfig = AwsConfig()
    #quotation_config: QuotationConfig = QuotationConfig()
    #sap_config: SapConfig = SapConfig()
    allowed_origin: str
    frontend_url: str

    @field_validator("docs_url")
    def none_docs_url(cls, v, info: ValidationInfo):
        if info.data.get("environment") != "dev":
            return None
        return v


settings = Settings()
