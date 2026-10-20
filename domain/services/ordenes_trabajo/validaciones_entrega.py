from starlette.status import HTTP_400_BAD_REQUEST

from domain.models.ordenes_trabajo.orden_trabajo_modelo import VwResumenFinancieroOt
from infrastructure.exceptions.domain_exception import DomainException
from repository.ordenes_trabajo.orden_trabajo_repositorio import OrdenTrabajoRepositorio


async def validar_saldo_para_entrega(consecutivo_ot: int, confirmar_credito: bool) -> None:
    """F1-07: si una orden queda con saldo pendiente, exige confirmar
    explícitamente "entregar a crédito" antes de dejarla pasar a Entregada --
    no bloquea la entrega, solo evita que pase desapercibido.

    Compartida por los 2 caminos que hoy pueden mover una orden a Entregada:
    OrdenTrabajoServicio (cambiar_estado/entregar_orden) y TableroServicio
    (arrastrar y soltar en el tablero, el único que usa la UI real hoy)."""
    repository = OrdenTrabajoRepositorio()
    resumen_dict = await repository.obtener_resumen_financiero(consecutivo_ot)
    if not resumen_dict:
        return
    # Las columnas vienen en MAYÚSCULAS (psycopg); BaseService.__normalize_keys__
    # hace este mismo .lower() antes de validar -- acá no hay instancia de
    # servicio de la que colgarse, así que se repite el paso mínimo.
    resumen_modelo = VwResumenFinancieroOt.model_validate(
        {k.lower(): v for k, v in resumen_dict.items()}
    )
    saldo = float(resumen_modelo.saldo_ot or 0.0)
    if saldo > 0 and not confirmar_credito:
        raise DomainException(
            f"La orden tiene un saldo pendiente de {saldo:.0f}. "
            "Confirma que se entrega a crédito para continuar.",
            HTTP_400_BAD_REQUEST
        )
