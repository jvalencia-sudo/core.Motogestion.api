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

    async def sembrar_perfiles(self) -> None:
        """Crea los perfiles por defecto del taller (Admin/Mecánico/Recepcionista)
        con sus permisos, vía la función fn_seed_perfiles_taller. El taller se toma
        del contexto (app.tenant_id, ya fijado por el servicio). Debe llamarse ANTES
        de crear_dueno (el dueño referencia el perfil Admin del taller)."""
        await self.db.execute_non_query(
            "SELECT fn_seed_perfiles_taller(current_setting('app.tenant_id')::integer)"
        )

    async def crear_dueno(self, documento: str, nombre: str, apellido: str, correo: str) -> None:
        """Crea el usuario dueño (perfil Admin) PRE-REGISTRADO: sin sub aún (se
        vincula en su primer login). cod_taller lo pone el DEFAULT (app.tenant_id) y
        el perfil Admin se resuelve del propio taller (el RLS filtra perfiles)."""
        await self.db.execute_non_query(
            "INSERT INTO usuarios "
            "(documento_usu, nombre_usu, apellido_1_usu, correo_usu, contrasena_usu, "
            " cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu) "
            "VALUES (:1, :2, :3, :4, 'auth0_managed', 1, 1, NULL, "
            "        (SELECT cod_prf FROM perfiles WHERE cod_rol_prf = 1 LIMIT 1), 1)",
            (documento, nombre, apellido, correo),
        )

    async def actualizar(self, cod_taller: int, campos: dict) -> None:
        """Actualiza solo los campos provistos (UPDATE dinámico)."""
        if not campos:
            return
        sets = ", ".join(f"{col} = :{i + 1}" for i, col in enumerate(campos))
        params = tuple(campos.values()) + (cod_taller,)
        query = f"UPDATE talleres SET {sets} WHERE cod_taller = :{len(campos) + 1}"
        await self.db.execute_non_query(query, params)

    async def sembrar_catalogos(self) -> None:
        """Catálogos base para que el taller sea usable desde el primer día.
        cod_taller lo pone el DEFAULT (app.tenant_id, ya fijado por el servicio)."""
        for nombre_mar in ["Yamaha", "Honda", "Suzuki", "Kawasaki", "Bajaj", "AKT", "KTM", "Auteco"]:
            await self.db.execute_non_query(
                "INSERT INTO marcas (nombre_mar) VALUES (:1)", (nombre_mar,)
            )
        for nombre_imp, pct in [("IVA", 19.00), ("IVA Reducido", 5.00), ("Excluido", 0.00)]:
            await self.db.execute_non_query(
                "INSERT INTO impuestos (nombre_imp, porcentaje_imp) VALUES (:1, :2)",
                (nombre_imp, pct),
            )
