from typing import Dict, List, Optional

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
        """Estado de suscripción del taller (para el gating y el cálculo de
        precio). talleres no tiene RLS."""
        return await self.db.get_first(
            "SELECT estado_tal, plan_tal, fecha_fin_susc_tal, precio_susc_tal, "
            "fecha_creacion_tal "
            "FROM talleres WHERE cod_taller = :1",
            (cod_taller,),
        )

    async def obtener_config_comprobante(self, cod_taller: int) -> Optional[Dict]:
        """Datos del taller para imprimir en el comprobante de servicio:
        nombre/dirección/teléfono reales del encabezado, texto de pie y días
        de garantía por defecto. talleres no tiene RLS."""
        return await self.db.get_first(
            "SELECT nombre_tal, direccion_tal, telefono_tal, texto_pie_comprobante, "
            "dias_garantia_pred FROM talleres WHERE cod_taller = :1",
            (cod_taller,),
        )

    async def contar_por_precio_susc(self, monto: int) -> int:
        """Cuenta talleres que ya tienen ese precio pactado (congelado desde su
        primer pago aprobado). Se usa para contar cupos de precio fundador."""
        row = await self.db.get_first(
            "SELECT count(*) AS total FROM talleres WHERE precio_susc_tal = :1",
            (monto,),
        )
        return (row.get("TOTAL") or 0) if row else 0

    async def extender_prueba(self, cod_taller: int, dias: int) -> None:
        """Extiende la ventana de prueba sin tocar estado_tal (solo aplica mientras
        sigue en 'prueba'; para un taller ya 'activo' se usa pago manual o ajuste de
        precio). Mismo GREATEST(vencimiento, hoy) que activar_suscripcion."""
        await self.db.execute_non_query(
            "UPDATE talleres SET "
            "  fecha_fin_susc_tal = (GREATEST(COALESCE(fecha_fin_susc_tal, CURRENT_DATE), CURRENT_DATE) "
            "                        + make_interval(days => :1))::date "
            "WHERE cod_taller = :2 AND estado_tal = 'prueba'",
            (dias, cod_taller),
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

    async def resumen_por_estado(self) -> List[Dict]:
        """Cantidad de talleres por estado_tal (Resumen de super-admin, F0-14)."""
        return await self.db.execute(
            "SELECT estado_tal, count(*) AS total FROM talleres GROUP BY estado_tal", None
        )

    async def mrr(self) -> int:
        """Ingreso mensual recurrente: suma del precio pactado (o el del plan
        catálogo si aún no tiene uno pactado) de los talleres 'activo'."""
        row = await self.db.get_first(
            "SELECT coalesce(sum(coalesce(t.precio_susc_tal, p.precio_plan)), 0) AS total "
            "FROM talleres t LEFT JOIN planes p ON p.nombre_plan = t.plan_tal "
            "WHERE t.estado_tal = 'activo'",
            None,
        )
        return (row.get("TOTAL") or 0) if row else 0

    async def vencimientos_proximos(self, dias: int = 7) -> List[Dict]:
        """Talleres 'activo' cuya suscripción vence en los próximos `dias`."""
        return await self.db.execute(
            "SELECT cod_taller, nombre_tal, telefono_tal, fecha_fin_susc_tal, "
            "  (fecha_fin_susc_tal - CURRENT_DATE) AS dias_restantes "
            "FROM talleres "
            "WHERE estado_tal = 'activo' AND fecha_fin_susc_tal IS NOT NULL "
            "  AND fecha_fin_susc_tal BETWEEN CURRENT_DATE AND CURRENT_DATE + make_interval(days => :1) "
            "ORDER BY fecha_fin_susc_tal",
            (dias,),
        )

    async def conversion_prueba_pago(self) -> float:
        """Fracción de talleres que ya pagaron al menos una vez (precio_susc_tal
        se congela en el primer pago aprobado, ver SuscripcionServicio)."""
        row = await self.db.get_first(
            "SELECT count(*) FILTER (WHERE precio_susc_tal IS NOT NULL)::float "
            "  / greatest(count(*), 1) AS conversion "
            "FROM talleres",
            None,
        )
        return float(row.get("CONVERSION") or 0.0) if row else 0.0

    async def obtener_con_ultimo_pago(self, cod_taller: int) -> Optional[Dict]:
        """Un taller con su último pago aprobado (para el detalle de super-admin)."""
        return await self.db.get_first(
            "SELECT t.*, "
            "  (SELECT max(p.fecha) FROM pagos p WHERE p.cod_taller = t.cod_taller "
            "     AND p.estado = 'APPROVED') AS ultimo_pago_fecha "
            "FROM talleres t WHERE t.cod_taller = :1",
            (cod_taller,),
        )

    async def listar_con_filtro(self, estado: Optional[str] = None) -> List[Dict]:
        """Lista de talleres para el panel de super-admin, con último pago
        aprobado (subconsulta correlacionada: pagos tampoco tiene RLS)."""
        where = "WHERE t.estado_tal = :1" if estado else ""
        query = (
            "SELECT t.*, "
            "  (SELECT max(p.fecha) FROM pagos p WHERE p.cod_taller = t.cod_taller "
            "     AND p.estado = 'APPROVED') AS ultimo_pago_fecha "
            f"FROM talleres t {where} ORDER BY t.fecha_creacion_tal DESC"
        )
        return await self.db.execute(query, (estado,) if estado else None)

    # ---- Statements para acciones transaccionales de super-admin (F0-14) ----
    # Cada acción las compone con un INSERT a auditoria_superadmin en un único
    # execute_transaction (ver domain/services/superadmin/acciones_taller_servicio.py):
    # todo o nada, igual que reemplazar_permisos de F0-13.

    @staticmethod
    def statement_extender_prueba(cod_taller: int, dias: int):
        return (
            "UPDATE talleres SET "
            "  fecha_fin_susc_tal = (GREATEST(COALESCE(fecha_fin_susc_tal, CURRENT_DATE), CURRENT_DATE) "
            "                        + make_interval(days => :1))::date "
            "WHERE cod_taller = :2 AND estado_tal = 'prueba'",
            (dias, cod_taller),
        )

    @staticmethod
    def statement_activar_suscripcion(cod_taller: int, nombre_plan: str, dias: int):
        return (
            "UPDATE talleres SET estado_tal = 'activo', plan_tal = :1, "
            "  fecha_fin_susc_tal = (GREATEST(COALESCE(fecha_fin_susc_tal, CURRENT_DATE), CURRENT_DATE) "
            "                        + make_interval(days => :2))::date "
            "WHERE cod_taller = :3",
            (nombre_plan, dias, cod_taller),
        )

    @staticmethod
    def statement_congelar_precio_si_nulo(cod_taller: int, monto: int):
        return (
            "UPDATE talleres SET precio_susc_tal = :1 WHERE cod_taller = :2 AND precio_susc_tal IS NULL",
            (monto, cod_taller),
        )

    @staticmethod
    def statement_cambiar_estado(cod_taller: int, estado: str):
        return ("UPDATE talleres SET estado_tal = :1 WHERE cod_taller = :2", (estado, cod_taller))

    @staticmethod
    def statement_ajustar_precio(cod_taller: int, precio: int):
        return (
            "UPDATE talleres SET precio_susc_tal = :1 WHERE cod_taller = :2",
            (precio, cod_taller),
        )

    async def actualizar(self, cod_taller: int, campos: dict) -> None:
        """Actualiza solo los campos provistos (UPDATE dinámico)."""
        if not campos:
            return
        sets = ", ".join(f"{col} = :{i + 1}" for i, col in enumerate(campos))
        params = tuple(campos.values()) + (cod_taller,)
        query = f"UPDATE talleres SET {sets} WHERE cod_taller = :{len(campos) + 1}"
        await self.db.execute_non_query(query, params)
