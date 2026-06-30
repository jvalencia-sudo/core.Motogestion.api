import random
import time
from typing import Dict, List, Optional

import jwt

from domain.contracts.auth.login_contract import LoginContract
from domain.contracts.auth.user_contract import (
    UserCreationContract,
    UserUpdateContract,
)
from domain.models.auth.user_model import (
    UserModel,
    UserWithPermissionsModel,
)
from domain.models.providers.auth0_user import Auth0UserModel
from domain.services.auth.permiso_servicio import PermisoServicio
from domain.services.base_service import BaseService
from starlette.status import HTTP_403_FORBIDDEN

from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.providers.auth.auth0_provider import Auth0Provider
from infrastructure.utils.tenant_context import set_tenant
from repository.auth.user_repository import UserRepository
from repository.auth.user_business_repository import UserBusinessRepository
from infrastructure.commons.enums.user import UserTypeEnum


class UserService(BaseService[UserModel, UserRepository]):
    def __init__(self):
        super().__init__(UserRepository())
        self.user_business_repository = UserBusinessRepository()
        self.permiso_servicio = PermisoServicio()

    def __parse__(self, record: Dict) -> UserModel:
        return UserModel.model_validate(record)



    def generate_provisional_document(self) -> str:
        """Genera un documento provisional único"""
        timestamp = str(int(time.time()))[-8:]  # Últimos 8 dígitos del timestamp
        random_num = str(random.randint(100, 999))  # 3 dígitos aleatorios
        return f"{timestamp}{random_num}"  # 11 dígitos total

    async def login(self, request: LoginContract) -> UserWithPermissionsModel:
        """
        Login CERRADO: solo entra quien YA esté registrado en el sistema.
        - Si el usuario existe por sub (ya vinculado) -> entra.
        - Si es su primer ingreso y su correo está pre-registrado (sin sub) -> se
          vincula el sub y entra.
        - Si no está registrado -> 403 (no se crean usuarios sueltos).
        """
        auth_user = await Auth0Provider().verify(request.token)
        sub = auth_user.user_id

        existing_user = await self.repository.get_user_by_sub(sub)

        if not existing_user:
            # Primer ingreso: el correo debe estar pre-registrado (registro de taller o invitación)
            acceso = await self.repository.get_acceso_por_correo(request.email)
            if not acceso:
                raise DomainException("Usuario no registrado en el sistema", HTTP_403_FORBIDDEN)
            set_tenant(acceso.get("COD_TALLER"))
            await self.repository.vincular_sub(acceso.get("DOCUMENTO_USU"), sub)
            existing_user = await self.repository.get_user_by_sub(sub)

        user = self._map_user_from_db(existing_user, sub, request)

        permissions = await self.permiso_servicio.obtener_permisos_por_perfil(
            user.cod_prf_usu,
            user.cod_rol_prf_usu
        )
        permission_names = [p.nombre_prm for p in permissions]

        nombre_tal = await self.repository.get_nombre_taller(existing_user.get("COD_TALLER"))
        perfil = await self.repository.get_nombre_perfil(user.cod_prf_usu)

        return UserWithPermissionsModel(
            **user.model_dump(),
            permissions=permission_names,
            nombre_tal=nombre_tal,
            perfil=perfil,
        )

    async def invitar(self, contract) -> Dict:
        """Crea un miembro del equipo en el taller actual (pre-registrado por correo).
        El taller sale del contexto de la petición (resolve_tenant)."""
        rol = contract.rol if contract.rol in (1, 2, 3) else 2
        nombre, apellido_1, _ = self._split_full_name(contract.nombre)
        documento = self.generate_provisional_document()
        await self.repository.crear_pre_registrado(
            documento, nombre, apellido_1, contract.correo, rol, rol
        )
        return {"correo": contract.correo, "documento_usu": documento, "rol": rol}

    def _map_user_from_db(self, db_user: Dict, sub_id: str, request: LoginContract) -> UserModel:
        """Maps database user record to UserModel"""
        return UserModel(
            documento_usu=db_user.get("DOCUMENTO_USU", 0),
            nombre_usu=db_user.get("NOMBRE_USU", request.name),
            apellido_1_usu=db_user.get("APELLIDO_1_USU", ""),
            apellido_2_usu=db_user.get("APELLIDO_2_USU"),
            correo_usu=db_user.get("CORREO_USU", request.email),
            contrasena_usu=db_user.get("CONTRASENA_USU", "auth0_managed"),
            cod_tipo_usu=db_user.get("COD_TIPO_USU", 1),
            cod_est_usu=db_user.get("COD_EST_USU", 1),
            sub_id_usu=db_user.get("SUB_ID_USU", sub_id),
            cod_prf_usu=db_user.get("COD_PRF_USU", 1),
            cod_rol_prf_usu=db_user.get("COD_ROL_PRF_USU", 1),
        )

    async def _create_new_user(self, sub_id: str, request: LoginContract) -> UserModel:
        """Creates a new user in the database"""
        # Split full name into components
        nombre, apellido_1, apellido_2 = self._split_full_name(request.name)

        try:
            # Create user in Auth0 if needed, then in DB
            new_user_id = await self.create_or_add_user(
                UserCreationContract(
                    documento_usu=self.generate_provisional_document(),
                    name=request.name,
                    email=request.email,
                    sub_id_usu=sub_id,
                    customer_id=None,
                    user_type=UserTypeEnum.CUSTOMER,
                    is_creation=False,  # Don't create in Auth0, already exists
                    nombre_usu=nombre,
                    apellido_1_usu=apellido_1,
                    apellido_2_usu=apellido_2 if apellido_2 else None,
                    cod_prf_usu=1,  # Default profile
                    cod_rol_prf_usu=1,  # Default role
                )
            )

            # Fetch the newly created user
            created_user = await self.repository.get_user_by_id(new_user_id)

            if not created_user:
                raise DomainException("Error: User created but could not be retrieved")

            return self._map_user_from_db(created_user, sub_id, request)

        except Exception as e:
            # Handle race condition - user might have been created by another request
            if "ORA-00001" in str(e) or "unique constraint" in str(e).lower():
                print(f"Constraint violation detected, retrying search for sub_id: {sub_id}")
                existing_user = await self.repository.get_user_by_sub(sub_id)
                if existing_user:
                    return self._map_user_from_db(existing_user, sub_id, request)
                else:
                    raise DomainException("Error: User could not be created or found after constraint violation")
            else:
                raise DomainException(f"Error creating user: {str(e)}")

    def _split_full_name(self, full_name: str) -> tuple[str, str, str]:
        """Función auxiliar para dividir nombres"""
        parts = full_name.strip().split()
        if len(parts) == 1:
            return parts[0], "Sin Apellido", ""
        elif len(parts) == 2:
            return parts[0], parts[1], ""
        elif len(parts) >= 3:
            nombre = parts[0]
            apellido_1 = parts[1]
            apellido_2 = " ".join(parts[2:])
            return nombre, apellido_1, apellido_2
        else:
            return "Usuario", "Sin Apellido", ""

    async def get_auth_user_by_sub(self, sub: str) -> Optional[UserModel]:
        user = await self.repository.get_user_by_sub(sub)
        if not user:
            return None
        businesses = await self.user_business_repository.get_businesses_by_user_id(
            user["user_id"]
        )
        user["businesses"] = businesses
        return self.__parse_with_businesses__(user)

    async def get_all_users_from_auth_provider(self) -> list[Auth0UserModel]:
        users = await Auth0Provider().get_users()
        return self.__parse_all_custom__(users, Auth0UserModel)

    async def create_or_add_user(
        self, contract: UserCreationContract, login: bool = False
    ):
        sub_id_usu = contract.sub_id_usu
        provider = Auth0Provider()

        if contract.is_creation:
            try:
                new_user = await provider.create_user(contract)
            except Exception as ex:
                raise DomainException(str(ex))
            if not new_user:
                raise DomainException("Error creating user")

        user = await self.get_auth_user_by_sub(sub_id_usu)
        if user:
            raise DomainException("User already exists")

        if contract.user_type == UserTypeEnum.CUSTOMER and not login:
            # Comentar temporalmente hasta configurar roles en Auth0
            # await provider.assign_customer_role(sub_id_usu)
            print(f"Saltando asignación de rol para: {sub_id_usu}")

        # Dividir nombre si no está dividido en el contract
        if not contract.nombre_usu:
            nombre, apellido_1, apellido_2 = contract.split_name()
        else:
            nombre = contract.nombre_usu
            apellido_1 = contract.apellido_1_usu or "Sin Apellido"
            apellido_2 = contract.apellido_2_usu

        # Crear el UserModel con los campos correctos de la BD
        new_user = await self.create(
            UserModel(
                documento_usu=self.generate_provisional_document(),
                nombre_usu=nombre,
                apellido_1_usu=apellido_1,
                apellido_2_usu=apellido_2,
                correo_usu=contract.email,
                contrasena_usu="auth0_managed",
                cod_tipo_usu=1,
                cod_est_usu=1,
                sub_id_usu=sub_id_usu,
                cod_prf_usu=contract.cod_prf_usu,
                cod_rol_prf_usu=contract.cod_rol_prf_usu,
            )
        )

        # Add user to business if business_id is provided

        return new_user

    async def update_user(self, user_id: int, user: UserUpdateContract):
        provider = Auth0Provider()
        existing_user = await self.get_user(user_id)
        if not existing_user:
            raise DomainException("User not found")
        user.sub_id_usu = existing_user.sub_id_usu

        # Dividir nombre si es necesario
        if not user.nombre_usu:
            parts = user.name.strip().split()
            if len(parts) >= 1:
                user.nombre_usu = parts[0]
            if len(parts) >= 2:
                user.apellido_1_usu = parts[1]
            if len(parts) >= 3:
                user.apellido_2_usu = " ".join(parts[2:])

        updated_user = await self.update(
            UserModel(
                documento_usu=user_id,
                nombre_usu=user.nombre_usu or existing_user.nombre_usu,
                apellido_1_usu=user.apellido_1_usu or existing_user.apellido_1_usu,
                apellido_2_usu=user.apellido_2_usu or existing_user.apellido_2_usu,
                correo_usu=user.email,
                contrase_usu=existing_user.contrase_usu,
                cod_est_usu=existing_user.cod_est_usu,
                sub_id_usu=user.sub_id_usu,
            )
        )

        if user.user_type == UserTypeEnum.CUSTOMER:
            # await provider.assign_customer_role(user.sub_id_usu)  # Comentado temporalmente
            pass
        elif user.user_type == UserTypeEnum.ADMIN:
            # await provider.assign_admin_role(user.sub_id_usu)  # Comentado temporalmente
            pass

        # Update business associations if provided
        if user.business_ids is not None:
            current_businesses = (
                await self.user_business_repository.get_businesses_by_user_id(user_id)
            )
            current_business_ids = [b["business_id"] for b in current_businesses]

            # Remove user from businesses not in the new list
            for business_id in current_business_ids:
                if business_id not in user.business_ids:
                    await self.user_business_repository.remove_user_from_business(
                        user_id, business_id
                    )

            # Add user to new businesses
            for business_id in user.business_ids:
                if business_id not in current_business_ids:
                    await self.user_business_repository.add_user_to_business(
                        user_id, business_id
                    )

        return updated_user

    async def get_user(self, user_id: str) -> UserModel:
        user = await self.repository.get_user_by_id(user_id)
        businesses = await self.user_business_repository.get_businesses_by_user_id(
            user_id
        )
        user["businesses"] = businesses
        if not user:
            raise DomainException("User not found")
        return self.__parse_with_businesses__(user)


