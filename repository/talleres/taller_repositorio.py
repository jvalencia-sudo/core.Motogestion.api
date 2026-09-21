from typing import Dict, Optional

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

    async def crear_taller(
        self, nombre_tal: str, correo_tal: str, nit_tal: str = None, fecha_fin_susc=None
    ) -> int:
        """Crea el taller (tenant) en modo 'prueba' con su ventana de trial ya fijada
        (fecha_fin_susc) y devuelve su cod_taller. talleres no tiene RLS."""
        res = await self.db.insert(
            "INSERT INTO talleres (nombre_tal, correo_tal, nit_tal, estado_tal, fecha_fin_susc_tal) "
            "VALUES (:1, :2, :3, 'prueba', :4)",
            (nombre_tal, correo_tal, nit_tal, fecha_fin_susc),
            primary_key="cod_taller",
        )
        return res["cod_taller"]

    async def existe_por_correo(self, correo_tal: str) -> bool:
        """¿Ya hay un taller con ese correo? (anti-abuso del trial). talleres no tiene RLS."""
        row = await self.db.get_first(
            "SELECT 1 FROM talleres WHERE lower(correo_tal) = lower(:1) LIMIT 1",
            (correo_tal,),
        )
        return row is not None

    async def get_nombre(self, cod_taller: int) -> str:
        """Nombre del taller (talleres no tiene RLS: se consulta directo)."""
        row = await self.db.get_first(
            "SELECT nombre_tal FROM talleres WHERE cod_taller = :1", (cod_taller,)
        )
        return row.get("NOMBRE_TAL") if row else None

    async def get_suscripcion(self, cod_taller: int) -> Optional[Dict]:
        """Estado de suscripción del taller (para el gating). talleres no tiene RLS."""
        return await self.db.get_first(
            "SELECT estado_tal, plan_tal, fecha_fin_susc_tal FROM talleres WHERE cod_taller = :1",
            (cod_taller,),
        )

    async def activar_suscripcion(self, cod_taller: int, nombre_plan: str, dias: int = 30) -> None:
        """Activa/renueva la suscripción tras un pago aprobado: estado='activo',
        fija el plan y extiende la vigencia `dias` desde hoy (o desde la fecha fin
        vigente si aún no venció). talleres no tiene RLS."""
        await self.db.execute_non_query(
            "UPDATE talleres SET estado_tal = 'activo', plan_tal = :1, "
            "  fecha_fin_susc_tal = (GREATEST(COALESCE(fecha_fin_susc_tal, CURRENT_DATE), CURRENT_DATE) "
            "                        + make_interval(days => :2))::date "
            "WHERE cod_taller = :3",
            (nombre_plan, dias, cod_taller),
        )

    async def actualizar(self, cod_taller: int, campos: dict) -> None:
        """Actualiza solo los campos provistos (UPDATE dinámico)."""
        if not campos:
            return
        sets = ", ".join(f"{col} = :{i + 1}" for i, col in enumerate(campos))
        params = tuple(campos.values()) + (cod_taller,)
        query = f"UPDATE talleres SET {sets} WHERE cod_taller = :{len(campos) + 1}"
        await self.db.execute_non_query(query, params)
