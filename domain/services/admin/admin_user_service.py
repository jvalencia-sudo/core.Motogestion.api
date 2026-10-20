from typing import Dict, List
from domain.contracts.admin.admin_user_contract import (
    AdminUserCreationContract,
    AdminUserUpdateContract,
    ChangePasswordContract,
    UserFilterContract,
    UpdateUserProfileContract
)
from domain.contracts.shared.respuesta_contract import (
    MensajeResponseContract,
    UsuariosPaginadosResponseContract,
)
from domain.models.auth.user_model import UserModel, VwUsuariosPerfiles
from domain.services.base_service import BaseService
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.providers.auth.auth0_provider import Auth0Provider
from repository.admin.admin_user_repository import AdminUserRepository
from repository.auth.perfil_repositorio import PerfilRepositorio
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

# Sin el documento en el texto: este mensaje llega tal cual a logs/Sentry desde
# el handler de DomainException, y quien hizo la petición ya sabe qué documento
# escribió (viene de la propia URL/formulario).
_USUARIO_NO_ENCONTRADO = "Usuario no encontrado"
_SIN_ADMINS = "El taller debe tener al menos un administrador activo"


class AdminUserService(BaseService[UserModel, AdminUserRepository]):
    def __init__(self):
        super().__init__(AdminUserRepository())
        self.auth0_provider = Auth0Provider()
        self.perfil_repo = PerfilRepositorio()

    async def _derivar_es_admin(self, cod_prf: int) -> bool:
        es_admin = await self.perfil_repo.es_perfil_admin(cod_prf)
        if es_admin is None:
            raise DomainException("El perfil elegido no existe", HTTP_404_NOT_FOUND)
        return es_admin

    async def _assert_admin_restante(self, documento_usu: str) -> None:
        """Antes de sacar a `documento_usu` de la lista de admins activos (por
        cambio de rol o desactivación): confirma que quede al menos otro."""
        if await self.repository.contar_admins_activos(excluir_documento=documento_usu) < 1:
            raise DomainException(_SIN_ADMINS, HTTP_400_BAD_REQUEST)

    def __parse__(self, record: Dict) -> UserModel:
        normalized = self.__normalize_keys__(record)
        return UserModel.model_validate(normalized)

    async def create_user_with_password(
        self, contract: AdminUserCreationContract
    ) -> UserModel:
        """
        Crea un usuario en el taller actual, PRE-REGISTRADO por correo (login cerrado).

        No se crea cuenta en Auth0: la persona entra luego con su correo (Google/Auth0)
        y se le vincula el sub en su primer login. El `password` del contrato se ignora.
        El taller sale del contexto de la petición (cod_taller por DEFAULT).
        """
        # Validar que no exista en este taller (RLS acota a su taller)
        if await self.repository.get_user_by_email(contract.correo_usu):
            raise DomainException("Ya existe un usuario con ese correo")
        if await self.repository.get_user_by_documento(contract.documento_usu):
            raise DomainException("Ya existe un usuario con ese documento")

        es_admin_usu = await self._derivar_es_admin(contract.cod_prf_usu)
        await self.repository.crear_pre_registrado(
            documento=contract.documento_usu,
            nombre=contract.nombre_usu,
            apellido_1=contract.apellido_1_usu,
            apellido_2=contract.apellido_2_usu,
            correo=contract.correo_usu,
            cod_prf=contract.cod_prf_usu,
            es_admin=es_admin_usu,
            cod_est=contract.cod_est_usu or 1,
            cod_tipo=contract.cod_tipo_usu or 2,
        )

        created_user = await self.repository.get_user_by_documento(contract.documento_usu)
        if not created_user:
            raise DomainException("Usuario creado pero no se pudo recuperar")
        return self.__parse__(created_user)

    async def update_user_admin(
        self, documento_usu: str, contract: AdminUserUpdateContract
    ) -> UserModel:
        """
        Actualiza un usuario desde el panel de administrador

        Args:
            documento_usu: Documento del usuario a actualizar
            contract: Datos a actualizar

        Returns:
            UserModel: El usuario actualizado
        """
        # Buscar usuario existente y parsearlo
        record = await self.repository.get_user_by_documento(documento_usu)
        if not record:
            raise DomainException(_USUARIO_NO_ENCONTRADO)

        existing_user = self.__parse__(record)

        es_admin_nuevo = (
            await self._derivar_es_admin(contract.cod_prf_usu)
            if contract.cod_prf_usu is not None
            else existing_user.es_admin_usu
        )
        estado_nuevo = (
            contract.cod_est_usu if contract.cod_est_usu is not None else existing_user.cod_est_usu
        )
        era_admin_activo = existing_user.es_admin_usu and existing_user.cod_est_usu == 1
        sigue_admin_activo = es_admin_nuevo and estado_nuevo == 1
        if era_admin_activo and not sigue_admin_activo:
            await self._assert_admin_restante(documento_usu)

        # Validar correo único si se está actualizando
        if contract.correo_usu and contract.correo_usu != existing_user.correo_usu:
            # Verificar si el usuario usa login social antes de hacer cualquier cosa
            if existing_user.sub_id_usu:
                auth0_user_info = await self.auth0_provider.get_user_info(existing_user.sub_id_usu)

                if auth0_user_info:
                    identities = auth0_user_info.get('identities', [])
                    if identities:
                        provider = identities[0].get('provider', '')
                        # Si el provider no es 'auth0' significa que usa login social
                        if provider != 'auth0':
                            raise DomainException(
                                f"No se puede cambiar el email de este usuario porque usa autenticación social ({provider.upper()}). "
                                f"El email está gestionado por {provider.upper()} y no puede ser modificado."
                            )

            # Si no usa login social, validar que el email no exista
            email_record = await self.repository.get_user_by_email(contract.correo_usu)
            if email_record:
                user_by_email = self.__parse__(email_record)
                if str(user_by_email.documento_usu) != documento_usu:
                    raise DomainException("Ya existe otro usuario con ese correo")

            # Actualizar email en Auth0 (solo usuarios con auth0/database)
            if existing_user.sub_id_usu:
                success = await self.auth0_provider.update_user_email(existing_user.sub_id_usu, contract.correo_usu)
                if not success:
                    raise DomainException("Error al actualizar email en Auth0")

        # Construir modelo actualizado
        updated_model = UserModel(
            documento_usu=existing_user.documento_usu,
            nombre_usu=contract.nombre_usu or existing_user.nombre_usu,
            apellido_1_usu=contract.apellido_1_usu or existing_user.apellido_1_usu,
            apellido_2_usu=contract.apellido_2_usu if contract.apellido_2_usu is not None else existing_user.apellido_2_usu,
            correo_usu=contract.correo_usu or existing_user.correo_usu,
            contrasena_usu=existing_user.contrasena_usu or "auth0_managed",
            cod_est_usu=estado_nuevo,
            cod_tipo_usu=contract.cod_tipo_usu if contract.cod_tipo_usu is not None else existing_user.cod_tipo_usu,
            sub_id_usu=existing_user.sub_id_usu,
            cod_prf_usu=contract.cod_prf_usu if contract.cod_prf_usu is not None else existing_user.cod_prf_usu,
            es_admin_usu=es_admin_nuevo,
        )

        await self.update(updated_model)

        # Recuperar usuario actualizado
        updated_record = await self.repository.get_user_by_documento(documento_usu)
        return self.__parse__(updated_record)

    async def deactivate_user(self, documento_usu: str) -> MensajeResponseContract:
        """
        Desactiva un usuario (soft delete)

        Args:
            documento_usu: Documento del usuario a desactivar

        Returns:
            Dict con mensaje de confirmación
        """
        record = await self.repository.get_user_by_documento(documento_usu)
        if not record:
            raise DomainException(_USUARIO_NO_ENCONTRADO)

        existing_user = self.__parse__(record)

        if existing_user.cod_est_usu == 2:
            raise DomainException("El usuario ya está desactivado")

        if existing_user.es_admin_usu:
            await self._assert_admin_restante(documento_usu)

        await self.repository.deactivate_user(documento_usu)

        return MensajeResponseContract(message=f"Usuario {documento_usu} desactivado exitosamente")

    async def activate_user(self, documento_usu: str) -> MensajeResponseContract:
        """
        Activa un usuario previamente desactivado

        Args:
            documento_usu: Documento del usuario a activar

        Returns:
            Dict con mensaje de confirmación
        """
        record = await self.repository.get_user_by_documento(documento_usu)
        if not record:
            raise DomainException(_USUARIO_NO_ENCONTRADO)

        existing_user = self.__parse__(record)

        if existing_user.cod_est_usu == 1:
            raise DomainException("El usuario ya está activo")

        await self.repository.activate_user(documento_usu)

        return MensajeResponseContract(message=f"Usuario {documento_usu} activado exitosamente")

    async def list_users_with_filters(
        self, filters: UserFilterContract
    ) -> UsuariosPaginadosResponseContract:
        """
        Lista usuarios con filtros y paginación

        Args:
            filters: Filtros de búsqueda

        Returns:
            Dict con datos paginados
        """
        result = await self.repository.search_users_with_filters(
            nombre=filters.nombre,
            correo=filters.correo,
            documento_usu=filters.documento_usu,
            cod_est_usu=filters.cod_est_usu,
            cod_prf_usu=filters.cod_prf_usu,
            es_admin_usu=filters.es_admin_usu,
            cod_tipo_usu=filters.cod_tipo_usu,
            limit=filters.limit,
            offset=filters.offset,
        )

        # Parsear los usuarios
        users = [self.__parse__(user) for user in result["data"]]

        return UsuariosPaginadosResponseContract(
            users=users,
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"],
            total_pages=result["total_pages"],
        )

    async def reset_user_password(
        self, documento_usu: str, contract: ChangePasswordContract
    ) -> MensajeResponseContract:
        """
        Resetea la contraseña de un usuario

        Args:
            documento_usu: Documento del usuario
            contract: Contrato con la nueva contraseña

        Returns:
            Dict con mensaje de confirmación
        """
        record = await self.repository.get_user_by_documento(documento_usu)
        if not record:
            raise DomainException(_USUARIO_NO_ENCONTRADO)

        existing_user = self.__parse__(record)

        if not existing_user.sub_id_usu:
            raise DomainException("Usuario no tiene cuenta en Auth0")

        # Resetear contraseña en Auth0
        success = await self.auth0_provider.reset_password(existing_user.sub_id_usu, contract.new_password)
        if not success:
            raise DomainException("Error al resetear contraseña en Auth0")

        return MensajeResponseContract(message=f"Contraseña actualizada exitosamente para usuario {documento_usu}")

    async def update_user_profile(
        self, documento_usu: str, contract: UpdateUserProfileContract
    ) -> UserModel:
        """
        Actualiza el rol (perfil) de un usuario (cambia sus permisos). El
        estado admin/no-admin se deriva del perfil elegido, no se recibe
        aparte (F0-13).

        Args:
            documento_usu: Documento del usuario
            contract: Nuevo perfil

        Returns:
            UserModel: Usuario actualizado
        """
        record = await self.repository.get_user_by_documento(documento_usu)
        if not record:
            raise DomainException(_USUARIO_NO_ENCONTRADO)

        existing_user = self.__parse__(record)
        es_admin_nuevo = await self._derivar_es_admin(contract.cod_prf_usu)

        if existing_user.es_admin_usu and not es_admin_nuevo:
            await self._assert_admin_restante(documento_usu)

        await self.repository.update_user_profile(
            documento_usu, contract.cod_prf_usu, es_admin_nuevo
        )

        updated_record = await self.repository.get_user_by_documento(documento_usu)
        return self.__parse__(updated_record)

    async def get_user_by_documento(self, documento_usu: str) -> UserModel:
        """
        Obtiene un usuario por su documento

        Args:
            documento_usu: Documento del usuario

        Returns:
            UserModel: El usuario encontrado
        """
        record = await self.repository.get_user_by_documento(documento_usu)
        if not record:
            raise DomainException(_USUARIO_NO_ENCONTRADO)

        return self.__parse__(record)

    async def get_usuarios_perfiles(self) -> List[VwUsuariosPerfiles]:
        """
        Obtiene todos los usuarios con información completa de perfiles y roles desde la vista

        Returns:
            List[VwUsuariosPerfiles]: Lista de usuarios con su información de perfil y rol
        """
        usuarios = await self.repository.get_usuarios_perfiles()
        return [self.__parse_usuario_perfil__(user) for user in usuarios]

    async def get_usuario_perfil_by_documento(self, documento: str) -> VwUsuariosPerfiles:
        """
        Obtiene un usuario específico con su perfil completo desde la vista

        Args:
            documento: Documento del usuario

        Returns:
            VwUsuariosPerfiles: Usuario con información completa de perfil y rol

        Raises:
            DomainException: Si el usuario no existe
        """
        usuario = await self.repository.get_usuario_perfil_by_documento(documento)
        if not usuario:
            raise DomainException(_USUARIO_NO_ENCONTRADO)

        return self.__parse_usuario_perfil__(usuario)

    def __parse_usuario_perfil__(self, record: Dict) -> VwUsuariosPerfiles:
        """
        Parsea un registro de la vista vw_usuarios_perfiles

        Args:
            record: Diccionario con los datos del usuario desde la vista

        Returns:
            VwUsuariosPerfiles: Modelo validado
        """
        normalized = self.__normalize_keys__(record)
        return VwUsuariosPerfiles.model_validate(normalized)
