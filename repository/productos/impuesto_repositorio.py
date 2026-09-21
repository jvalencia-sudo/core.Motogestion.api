from repository.base_repository import BaseRepository


class ImpuestoRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="impuestos",
            primary_key="cod_imp",
            omit_key=True,
            sequence_name="seq_impuestos"
        )

    async def crear(self, nombre_imp: str, porcentaje_imp: float) -> None:
        """Crea un impuesto en el taller actual (cod_taller por DEFAULT app.tenant_id)."""
        await self.execute_non_query(
            "INSERT INTO impuestos (nombre_imp, porcentaje_imp) VALUES (:1, :2)",
            (nombre_imp, porcentaje_imp),
        )

    async def listar(self):
        """Todos los impuestos del taller actual (RLS)."""
        return await self.execute(
            "SELECT cod_imp, nombre_imp, porcentaje_imp FROM impuestos ORDER BY nombre_imp",
            None,
        )
