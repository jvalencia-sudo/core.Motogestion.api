from typing import Dict, List, Optional
from repository.base_repository import BaseRepository


class AdminUserRepository(BaseRepository):
    def __init__(self):
        super().__init__("auth", "USUARIOS", "documento_usu", omit_key=False)

    async def search_users_with_filters(
        self,
        nombre: Optional[str] = None,
        correo: Optional[str] = None,
        documento_usu: Optional[str] = None,
        cod_est_usu: Optional[int] = None,
        cod_prf_usu: Optional[int] = None,
        cod_rol_prf_usu: Optional[int] = None,
        cod_tipo_usu: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """
        Busca usuarios con filtros dinámicos y paginación
        """
        where_clauses = []
        params = []
        param_index = 1

        # Construir condiciones WHERE dinámicamente
        if nombre:
            where_clauses.append(
                f"(UPPER(nombre_usu) LIKE :{param_index} OR "
                f"UPPER(apellido_1_usu) LIKE :{param_index + 1} OR "
                f"UPPER(apellido_2_usu) LIKE :{param_index + 2})"
            )
            search_pattern = f"%{nombre.upper()}%"
            params.extend([search_pattern, search_pattern, search_pattern])
            param_index += 3

        if correo:
            where_clauses.append(f"UPPER(correo_usu) LIKE :{param_index}")
            params.append(f"%{correo.upper()}%")
            param_index += 1

        if documento_usu:
            where_clauses.append(f"documento_usu = :{param_index}")
            params.append(documento_usu)
            param_index += 1

        if cod_est_usu is not None:
            where_clauses.append(f"cod_est_usu = :{param_index}")
            params.append(cod_est_usu)
            param_index += 1

        if cod_prf_usu is not None:
            where_clauses.append(f"cod_prf_usu = :{param_index}")
            params.append(cod_prf_usu)
            param_index += 1

        if cod_rol_prf_usu is not None:
            where_clauses.append(f"cod_rol_prf_usu = :{param_index}")
            params.append(cod_rol_prf_usu)
            param_index += 1

        if cod_tipo_usu is not None:
            where_clauses.append(f"cod_tipo_usu = :{param_index}")
            params.append(cod_tipo_usu)
            param_index += 1

        # Construir la cláusula WHERE
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Query para contar total de registros
        count_query = f"SELECT COUNT(*) as total FROM {self.table_name} WHERE {where_clause}"
        total_result = await self.db.get_first(count_query, tuple(params))
        total = total_result.get('TOTAL', 0) if total_result else 0

        # Query principal con paginación
        data_query = f"""
        SELECT * FROM {self.table_name}
        WHERE {where_clause}
        ORDER BY documento_usu DESC
        OFFSET :{param_index} ROWS FETCH NEXT :{param_index + 1} ROWS ONLY
        """
        params.extend([offset, limit])

        data = await self.db.execute(data_query, tuple(params))

        return {
            'data': data,
            'total': total,
            'limit': limit,
            'offset': offset,
            'total_pages': (total + limit - 1) // limit if limit > 0 else 0
        }

    async def crear_pre_registrado(
        self, documento: str, nombre: str, apellido_1: str, apellido_2: Optional[str],
        correo: str, cod_prf: int, cod_rol: int, cod_est: int = 1, cod_tipo: int = 2
    ) -> None:
        # Usuario PRE-REGISTRADO en el taller actual (cod_taller por DEFAULT = app.tenant_id).
        # sub NULL hasta su primer login (modelo de login cerrado por correo).
        await self.db.execute_non_query(
            f"INSERT INTO {self.table_name} "
            "(documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu, correo_usu, "
            " contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu) "
            "VALUES (:1, :2, :3, :4, :5, 'auth0_managed', :6, :7, NULL, :8, :9)",
            (documento, nombre, apellido_1, apellido_2, correo, cod_tipo, cod_est, cod_prf, cod_rol),
        )

    async def get_user_by_sub(self, sub_id: str) -> Optional[Dict]:
        """Obtiene usuario por sub_id de Auth0"""
        return await self.get_one(
            f"SELECT * FROM {self.table_name} WHERE sub_id_usu = :1",
            (sub_id,)
        )

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Obtiene usuario por correo electrónico"""
        return await self.get_one(
            f"SELECT * FROM {self.table_name} WHERE correo_usu = :1",
            (email,)
        )

    async def get_user_by_documento(self, documento: str) -> Optional[Dict]:
        """Obtiene usuario por documento"""
        return await self.get_one(
            f"SELECT * FROM {self.table_name} WHERE documento_usu = :1",
            (documento,)
        )

    async def deactivate_user(self, documento_usu: str) -> None:
        """Desactiva un usuario (soft delete)"""
        await self.db.execute_non_query(
            f"UPDATE {self.table_name} SET cod_est_usu = 2 WHERE documento_usu = :1",
            (documento_usu,)
        )

    async def activate_user(self, documento_usu: str) -> None:
        """Activa un usuario"""
        await self.db.execute_non_query(
            f"UPDATE {self.table_name} SET cod_est_usu = 1 WHERE documento_usu = :1",
            (documento_usu,)
        )

    async def update_user_profile(
        self,
        documento_usu: str,
        cod_prf_usu: int,
        cod_rol_prf_usu: int
    ) -> None:
        """Actualiza el perfil y rol de un usuario"""
        await self.db.execute_non_query(
            f"""UPDATE {self.table_name}
                SET cod_prf_usu = :1, cod_rol_prf_usu = :2
                WHERE documento_usu = :3""",
            (cod_prf_usu, cod_rol_prf_usu, documento_usu)
        )

    async def get_usuarios_perfiles(self) -> List[Dict]:
        """
        Obtiene todos los usuarios con información de perfiles y roles desde la vista
        """
        query = "SELECT * FROM vw_usuarios_perfiles"
        return await self.db.execute(query)

    async def get_usuario_perfil_by_documento(self, documento: str) -> Optional[Dict]:
        """
        Obtiene un usuario específico con su perfil completo desde la vista
        """
        query = "SELECT * FROM vw_usuarios_perfiles WHERE documento_usu = :1"
        return await self.db.get_first(query, (documento,))
