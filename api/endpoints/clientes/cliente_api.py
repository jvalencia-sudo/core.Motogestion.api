from typing import List
from fastapi import APIRouter, status

from domain.contracts.clientes.cliente_contract import (
    ClienteCreateContract,
    ClienteUpdateContract,
    ClienteResponseContract
)
from domain.services.clientes.cliente_servicio import ClienteServicio

router = APIRouter()


@router.get("", response_model=List[ClienteResponseContract])
async def obtener_clientes():
    """
    Obtiene todos los clientes con información completa.
    """
    servicio = ClienteServicio()
    return await servicio.obtener_todos_clientes()


@router.get("/{documento_cli}", response_model=ClienteResponseContract)
async def obtener_cliente(documento_cli: str):
    """
    Obtiene un cliente específico por su documento.

    - **documento_cli**: Documento de identificación del cliente (8-11 caracteres)
    """
    servicio = ClienteServicio()
    return await servicio.obtener_cliente_por_documento(documento_cli)


@router.post("", response_model=ClienteResponseContract, status_code=status.HTTP_201_CREATED)
async def crear_cliente(cliente: ClienteCreateContract):
    """
    Crea un nuevo cliente.

    - **documento_cli**: Documento de identificación (requerido, 8-11 caracteres)
    - **nombre_cli**: Nombre del cliente (requerido)
    - **apellido_1_cli**: Primer apellido (requerido)
    - **apellido_2_cli**: Segundo apellido (opcional)
    - **telefono_cli**: Teléfono de contacto (requerido, 10-15 caracteres)
    - **correo_cli**: Correo electrónico (requerido, debe ser válido)
    - **direccion_cli**: Dirección de residencia (opcional)
    """
    servicio = ClienteServicio()
    return await servicio.crear_cliente(cliente)


@router.put("/{documento_cli}", response_model=ClienteResponseContract)
async def actualizar_cliente(documento_cli: str, cliente: ClienteUpdateContract):
    """
    Actualiza un cliente existente.

    Todos los campos son opcionales. Solo se actualizan los campos proporcionados.

    - **documento_cli**: Documento del cliente a actualizar
    - **nombre_cli**: Nuevo nombre (opcional)
    - **apellido_1_cli**: Nuevo primer apellido (opcional)
    - **apellido_2_cli**: Nuevo segundo apellido (opcional)
    - **telefono_cli**: Nuevo teléfono (opcional)
    - **correo_cli**: Nuevo correo (opcional)
    - **direccion_cli**: Nueva dirección (opcional)
    """
    servicio = ClienteServicio()
    return await servicio.actualizar_cliente(documento_cli, cliente)


@router.delete("/{documento_cli}")
async def eliminar_cliente(documento_cli: str):
    """
    Elimina un cliente.

    - **documento_cli**: Documento del cliente a eliminar
    """
    servicio = ClienteServicio()
    await servicio.eliminar_cliente(documento_cli)
    return {"message": f"Cliente con documento {documento_cli} eliminado exitosamente"}
