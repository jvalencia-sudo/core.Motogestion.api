import oracledb
from config import settings


class DbFactory:
    def __init__(self):
        self.config = settings.db_config
        # Configurar el modo thin de Oracle (recomendado)
        oracledb.init_oracle_client()

    async def connect(self):
        # Crear DSN (Data Source Name) para Oracle
        dsn = oracledb.makedsn(
            host=self.config.host,
            port=self.config.port,
            service_name=self.config.service_name
        )

        # Si prefieres usar SID en lugar de service_name:
        # dsn = oracledb.makedsn(
        #     host=self.config.host,
        #     port=self.config.port,
        #     sid=self.config.sid
        # )

        return await oracledb.connect_async(
            user=self.config.user,
            password=self.config.password,
            dsn=dsn
        )
