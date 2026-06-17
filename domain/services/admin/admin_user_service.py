from typing import Dict, List, Optional
from domain.contracts.admin.admin_user_contract import (
    AdminUserCreationContract,
    AdminUserUpdateContract,
    ChangePasswordContract,
    UserFilterContract,
    UpdateUserProfileContract
)
from domain.models.auth.user_model import UserModel, VwUsuariosPerfiles
from domain.services.base_service import BaseService
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.providers.auth.auth0_provider import Auth0Provider
from repository.admin.admin_user_repository import AdminUserRepository


class AdminUserService(BaseService[UserModel, AdminUserRepository]):
    def __init__(self):
        super().__init__(AdminUserRepository())
        self.auth0_provider = Auth0Provider()

    def __parse__(self, record: Dict) -> UserModel:
        normalized = self.__normalize_keys__(record)
        return UserModel.model_validate(normalized)

    async def create_user_with_password(
        self, contract: AdminUserCreationContract
    ) -> UserModel:
        """
        Crea un usuario completo (Auth0 + BD) con contraseña
        Flujo: Primero Auth0, luego BD. Si falla BD, rollback de Auth0.

        Args:
            contract: Datos del usuario a crear

        Returns:
            UserModel: El usuario creado

        Raises:
            DomainException: Si el usuario ya existe o si hay errores
        """
        # 1. Validar que no exista en BD
        existing_user_by_email = await self.repository.get_user_by_email(
            contract.correo_usu
        )
        if existing_user_by_email:
            raise DomainException(
                f"Ya existe un usuario con el correo {contract.correo_usu}"
            )

        existing_user_by_doc = await self.repository.get_user_by_documento(
            contract.documento_usu
        )
        if existing_user_by_doc:
            raise DomainException(
                f"Ya existe un usuario con el documento {contract.documento_usu}"
            )

        # 2. Crear usuario en Auth0
        print(f"Creating user in Auth0: {contract.correo_usu}")
        try:
            # Crear contrato para Auth0
            from domain.contracts.auth.user_contract import UserCreationContract

            auth0_contract = UserCreationContract(
                name=f"{contract.nombre_usu} {contract.apellido_1_usu}",
                email=contract.correo_usu,
                password=contract.password,
                sub_id_usu="",  # Se asignará después
                is_creation=True,
                documento_usu=contract.documento_usu,
                nombre_usu=contract.nombre_usu,
                apellido_1_usu=contract.apellido_1_usu,
                apellido_2_usu=contract.apellido_2_usu,
                cod_prf_usu=contract.cod_prf_usu,
                cod_rol_prf_usu=contract.cod_rol_prf_usu,
            )

            auth0_user = await self.auth0_provider.create_user(auth0_contract)

            if not auth0_user:
                raise DomainException("Error al crear usuario en Auth0")

            sub_id_usu = auth0_user.user_id

        except Exception as e:
            raise DomainException(f"Error al crear usuario en Auth0: {str(e)}")

        # 3. Crear usuario en BD
        try:
            user_model = UserModel(
                documento_usu=int(contract.documento_usu),
                nombre_usu=contract.nombre_usu,
                apellido_1_usu=contract.apellido_1_usu,
                apellido_2_usu=contract.apellido_2_usu,
                correo_usu=contract.correo_usu,
                contrasena_usu="auth0_managed",
                cod_est_usu=contract.cod_est_usu,
                cod_tipo_usu=contract.cod_tipo_usu,
                sub_id_usu=sub_id_usu,
                cod_prf_usu=contract.cod_prf_usu,
                cod_rol_prf_usu=contract.cod_rol_prf_usu,
            )

            await self.create(user_model)

            # Buscar el usuario creado
            created_user = await self.repository.get_user_by_sub(sub_id_usu)
            if not created_user:
                raise DomainException("Usuario creado pero no se pudo recuperar")

            return self.__parse__(created_user)

        except Exception as e:
            # Rollback: eliminar usuario de Auth0
            print(f"Error creating user in DB, rolling back Auth0 user: {str(e)}")
            await self.auth0_provider.delete_user(sub_id_usu)
            raise DomainException(f"Error al crear usuario en BD: {str(e)}")

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
            raise DomainException(f"Usuario con documento {documento_usu} no encontrado")

        existing_user = self.__parse__(record)

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
                    raise DomainException(f"Ya existe otro usuario con el correo {contract.correo_usu}")

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
            cod_est_usu=contract.cod_est_usu if contract.cod_est_usu is not None else existing_user.cod_est_usu,
            cod_tipo_usu=contract.cod_tipo_usu if contract.cod_tipo_usu is not None else existing_user.cod_tipo_usu,
            sub_id_usu=existing_user.sub_id_usu,
            cod_prf_usu=contract.cod_prf_usu if contract.cod_prf_usu is not None else existing_user.cod_prf_usu,
            cod_rol_prf_usu=contract.cod_rol_prf_usu if contract.cod_rol_prf_usu is not None else existing_user.cod_rol_prf_usu,
        )

        await self.update(updated_model)

        # Recuperar usuario actualizado
        updated_record = await self.repository.get_user_by_documento(documento_usu)
        return self.__parse__(updated_record)

    async def deactivate_user(self, documento_usu: str) -> Dict[str, str]:
        """
        Desactiva un usuario (soft delete)

        Args:
            documento_usu: Documento del usuario a desactivar

        Returns:
            Dict con mensaje de confirmación
        """
        record = await self.repository.get_user_by_documento(documento_usu)
        if not record:
            raise DomainException(f"Usuario con documento {documento_usu} no encontrado")

        existing_user = self.__parse__(record)

        if existing_user.cod_est_usu == 2:
            raise DomainException("El usuario ya está desactivado")

        await self.repository.deactivate_user(documento_usu)

        return {"message": f"Usuario {documento_usu} desactivado exitosamente"}

    async def activate_user(self, documento_usu: str) -> Dict[str, str]:
        """
        Activa un usuario previamente desactivado

        Args:
            documento_usu: Documento del usuario a activar

        Returns:
            Dict con mensaje de confirmación
        """
        record = await self.repository.get_user_by_documento(documento_usu)
        if not record:
            raise DomainException(f"Usuario con documento {documento_usu} no encontrado")

        existing_user = self.__parse__(record)

        if existing_user.cod_est_usu == 1:
            raise DomainException("El usuario ya está activo")

        await self.repository.activate_user(documento_usu)

        return {"message": f"Usuario {documento_usu} activado exitosamente"}

    async def list_users_with_filters(self, filters: UserFilterContract) -> Dict:
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
            cod_rol_prf_usu=filters.cod_rol_prf_usu,
            cod_tipo_usu=filters.cod_tipo_usu,
            limit=filters.limit,
            offset=filters.offset,
        )

        # Parsear los usuarios
        users = [self.__parse__(user) for user in result["data"]]

        return {
            "users": users,
            "total": result["total"],
            "limit": result["limit"],
            "offset": result["offset"],
            "total_pages": result["total_pages"],
        }

    async def reset_user_password(
        self, documento_usu: str, contract: ChangePasswordContract
    ) -> Dict[str, str]:
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
            raise DomainException(f"Usuario con documento {documento_usu} no encontrado")

        existing_user = self.__parse__(record)

        if not existing_user.sub_id_usu:
            raise DomainException("Usuario no tiene cuenta en Auth0")

        # Resetear contraseña en Auth0
        success = await self.auth0_provider.reset_password(existing_user.sub_id_usu, contract.new_password)
        if not success:
            raise DomainException("Error al resetear contraseña en Auth0")

        return {"message": f"Contraseña actualizada exitosamente para usuario {documento_usu}"}

    async def update_user_profile(
        self, documento_usu: str, contract: UpdateUserProfileContract
    ) -> UserModel:
        """
        Actualiza el perfil y rol de un usuario (cambia sus permisos)

        Args:
            documento_usu: Documento del usuario
            contract: Nuevo perfil y rol

        Returns:
            UserModel: Usuario actualizado
        """
        record = await self.repository.get_user_by_documento(documento_usu)
        if not record:
            raise DomainException(f"Usuario con documento {documento_usu} no encontrado")

        await self.repository.update_user_profile(
            documento_usu, contract.cod_prf_usu, contract.cod_rol_prf_usu
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
            raise DomainException(f"Usuario con documento {documento_usu} no encontrado")

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
            raise DomainException(f"Usuario con documento {documento} no encontrado")

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
