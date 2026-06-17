from typing import List
from fastapi import APIRouter, Depends, status
from starlette.responses import Response

from domain.contracts.productos.producto_contract import (
    ProductoCreateContract,
    ProductoUpdateContract,
    ProductoResponseContract
)
from domain.services.productos.producto_servicio import ProductoServicio
from infrastructure.dependencies.auth_request import AuthRequest

router = APIRouter()


@router.get("", response_model=List[ProductoResponseContract])
async def obtener_todos_productos(
    activos_solo: bool = False,
    # user=Depends(AuthRequest(permissions=["productos:leer"]))
):
    """
    Obtiene todos los productos con sus impuestos.

    - **activos_solo**: Si es True, solo retorna productos activos
    """
    servicio = ProductoServicio()
    if activos_solo:
        return await servicio.obtener_productos_activos()
    return await servicio.obtener_todos_productos()


@router.get("/{cod_pro}", response_model=ProductoResponseContract)
async def obtener_producto_por_id(
    cod_pro: int,
    # user=Depends(AuthRequest(permissions=["productos:leer"]))
):
    """
    Obtiene un producto específico por su código.

    - **cod_pro**: Código del producto
    """
    servicio = ProductoServicio()
    return await servicio.obtener_producto_por_id(cod_pro)


@router.post("", response_model=ProductoResponseContract, status_code=status.HTTP_201_CREATED)
async def crear_producto(
    producto: ProductoCreateContract,
    # user=Depends(AuthRequest(permissions=["productos:crear"]))
):
    """
    Crea un nuevo producto con sus impuestos.

    - **nombre_pro**: Nombre del producto (requerido)
    - **descripcion_pro**: Descripción del producto (requerido)
    - **stock_pro**: Stock actual (requerido, >= 0)
    - **stock_pro_min**: Stock mínimo (requerido, >= 0)
    - **precio_pro**: Precio del producto (requerido, >= 0)
    - **impuestos**: Lista de impuestos a aplicar (opcional)
        - **cod_imp**: Código del impuesto
        - **porcentaje**: Porcentaje a aplicar (0-100)
    """
    servicio = ProductoServicio()
    return await servicio.crear_producto(producto)


@router.put("/{cod_pro}", response_model=ProductoResponseContract)
async def actualizar_producto(
    cod_pro: int,
    producto: ProductoUpdateContract,
    # user=Depends(AuthRequest(permissions=["productos:actualizar"]))
):
    """
    Actualiza un producto existente.

    Todos los campos son opcionales. Solo se actualizan los campos proporcionados.

    - **cod_pro**: Código del producto a actualizar
    - **nombre_pro**: Nuevo nombre del producto (opcional)
    - **descripcion_pro**: Nueva descripción (opcional)
    - **stock_pro**: Nuevo stock (opcional)
    - **stock_pro_min**: Nuevo stock mínimo (opcional)
    - **precio_pro**: Nuevo precio (opcional)
    - **impuestos**: Nueva lista de impuestos (opcional, reemplaza los existentes)
    """
    servicio = ProductoServicio()
    return await servicio.actualizar_producto(cod_pro, producto)


@router.delete("/{cod_pro}", status_code=status.HTTP_200_OK)
async def desactivar_producto(
    cod_pro: int,
    # user=Depends(AuthRequest(permissions=["productos:eliminar"]))
):
    """
    Desactiva un producto (soft delete).

    El producto no se elimina de la base de datos, solo se marca como inactivo.

    - **cod_pro**: Código del producto a desactivar
    """
    servicio = ProductoServicio()
    return await servicio.desactivar_producto(cod_pro)


@router.patch("/{cod_pro}/activars", status_code=status.HTTP_200_OK)
async def activar_producto(
    cod_pro: int,
    # user=Depends(AuthRequest(permissions=["productos:actualizar"]))
):
    """
    Activa un producto previamente desactivado.

    - **cod_pro**: Código del producto a activar
    """
    servicio = ProductoServicio()
    return await servicio.activar_producto(cod_pro)
