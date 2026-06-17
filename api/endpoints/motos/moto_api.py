from typing import List, Optional
from fastapi import APIRouter, status

from domain.contracts.motos.moto_contract import (
    MotoCreateContract,
    MotoUpdateContract,
    MotoResponseContract,
    MotoClienteResponseContract
)
from domain.services.motos.moto_servicio import MotoServicio

router = APIRouter()


@router.get("", response_model=List[MotoResponseContract])
async def obtener_motos(
    cliente: Optional[str] = None,
    marca: Optional[int] = None
):
    """
    Obtiene todas las motos con información completa.

    Parámetros opcionales para filtrar:
    - **cliente**: Documento del cliente para obtener sus motos
    - **marca**: Código de marca para obtener motos de esa marca
    """
    servicio = MotoServicio()

    if cliente:
        return await servicio.obtener_motos_por_cliente(cliente)
    elif marca:
        return await servicio.obtener_motos_por_marca(marca)
    else:
        return await servicio.obtener_todas_motos()


@router.get("/cliente/{documento_cli}", response_model=List[MotoClienteResponseContract])
async def obtener_motos_por_cliente(documento_cli: str):
    """
    Obtiene todas las motos de un cliente específico con información de marca.

    - **documento_cli**: Documento del cliente (8-11 caracteres)

    Retorna: Lista de motos con placa, modelo, color, cilindraje, documento del cliente, código y nombre de marca
    """
    servicio = MotoServicio()
    return await servicio.obtener_motos_cliente_simple(documento_cli)


@router.get("/{placa_mot}", response_model=MotoResponseContract)
async def obtener_moto(placa_mot: str):
    """
    Obtiene una moto específica por su placa.

    - **placa_mot**: Placa de la moto (6 caracteres)
    """
    servicio = MotoServicio()
    return await servicio.obtener_moto_por_id(placa_mot)


@router.post("", response_model=MotoResponseContract, status_code=status.HTTP_201_CREATED)
async def crear_moto(moto: MotoCreateContract):
    """
    Crea una nueva moto.

    - **placa_mot**: Placa de la moto (requerido, 6 caracteres)
    - **modelo_mot**: Año modelo de la moto (requerido, 1900-2100)
    - **color_mot**: Color de la moto (requerido)
    - **cilindraje_mot**: Cilindraje en cc (requerido, mayor a 0)
    - **documento_cli_mot**: Documento del propietario (requerido)
    - **cod_marca_mot**: Código de la marca (requerido)
    """
    servicio = MotoServicio()
    return await servicio.crear_moto(moto)


@router.put("/{placa_mot}", response_model=MotoResponseContract)
async def actualizar_moto(placa_mot: str, moto: MotoUpdateContract):
    """
    Actualiza una moto existente.

    Todos los campos son opcionales. Solo se actualizan los campos proporcionados.

    - **placa_mot**: Placa de la moto a actualizar
    - **placa_mot**: Nueva placa (opcional, 6 caracteres)
    - **modelo_mot**: Nuevo año modelo (opcional)
    - **color_mot**: Nuevo color (opcional)
    - **cilindraje_mot**: Nuevo cilindraje (opcional)
    - **documento_cli_mot**: Nuevo propietario (opcional)
    - **cod_marca_mot**: Nueva marca (opcional)
    """
    servicio = MotoServicio()
    return await servicio.actualizar_moto(placa_mot, moto)


@router.delete("/{placa_mot}")
async def eliminar_moto(placa_mot: str):
    """
    Elimina una moto.

    - **placa_mot**: Placa de la moto a eliminar
    """
    servicio = MotoServicio()
    await servicio.eliminar_moto(placa_mot)
    return {"message": f"Moto con placa {placa_mot} eliminada exitosamente"}
