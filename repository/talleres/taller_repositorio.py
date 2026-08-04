from repository.base_repository import BaseRepository


class TallerRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="talleres",
            primary_key="cod_taller",
            omit_key=True,
            sequence_name="seq_talleres",
        )

    async def crear_taller(self, nombre_tal: str, correo_tal: str, nit_tal: str = None) -> int:
        """Crea el taller (tenant) y devuelve su cod_taller. talleres no tiene RLS."""
        res = await self.db.insert(
            "INSERT INTO talleres (nombre_tal, correo_tal, nit_tal, estado_tal) "
            "VALUES (:1, :2, :3, 'prueba')",
            (nombre_tal, correo_tal, nit_tal),
            primary_key="cod_taller",
        )
        return res["cod_taller"]

    async def get_nombre(self, cod_taller: int) -> str:
        """Nombre del taller (talleres no tiene RLS: se consulta directo)."""
        row = await self.db.get_first(
            "SELECT nombre_tal FROM talleres WHERE cod_taller = :1", (cod_taller,)
        )
        return row.get("NOMBRE_TAL") if row else None

    async def actualizar(self, cod_taller: int, campos: dict) -> None:
        """Actualiza solo los campos provistos (UPDATE dinámico)."""
        if not campos:
            return
        sets = ", ".join(f"{col} = :{i + 1}" for i, col in enumerate(campos))
        params = tuple(campos.values()) + (cod_taller,)
        query = f"UPDATE talleres SET {sets} WHERE cod_taller = :{len(campos) + 1}"
        await self.db.execute_non_query(query, params)
