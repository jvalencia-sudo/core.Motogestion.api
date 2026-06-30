from typing import Dict, Optional

from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from domain.models.tablero.tablero_model import MecanicoItem, TableroItem, TableroResponse
from infrastructure.exceptions.domain_exception import DomainException
from repository.tablero.tablero_repositorio import TableroRepositorio

ROL_MECANICO = 2
ROLES_GESTOR = (1, 3)  # Administrador, Recepcionista

ESTADOS_VALIDOS = {1, 2, 3, 4, 5, 6}
# Estados a los que un MECÁNICO puede llevar SUS OT (su flujo de trabajo)
ESTADOS_MECANICO = {1, 2, 3}  # Pendiente, En Proceso, Completada


class TableroServicio:
    def __init__(self):
        self.repo = TableroRepositorio()

    async def obtener(self, current: Optional[Dict], mecanico_param: Optional[str]) -> TableroResponse:
        """Alcance por ROL (enforced en el backend, NO por permisos editables):
        - Mecánico: SIEMPRE su propio tablero (ignora el parámetro).
        - Admin/Recepcionista: ve todos o el mecánico que seleccione.
        - Sin usuario identificado: tablero vacío (fail-closed)."""
        rol = (current or {}).get("COD_ROL_PRF_USU")
        es_gestor = rol in ROLES_GESTOR

        if rol == ROL_MECANICO:
            documento = (current or {}).get("DOCUMENTO_USU")
        elif es_gestor:
            documento = mecanico_param or None  # None = todos
        else:
            return TableroResponse(es_gestor=False, mecanicos=[], items=[])

        mecanicos = []
        if es_gestor:
            filas = await self.repo.listar_mecanicos()
            mecanicos = [
                MecanicoItem(documento_usu=f.get("DOCUMENTO_USU"), nombre=f.get("NOMBRE"))
                for f in filas
            ]

        filas = await self.repo.listar_ordenes(documento)
        items = [self._map(f) for f in filas]
        return TableroResponse(es_gestor=es_gestor, mecanicos=mecanicos, items=items)

    async def cambiar_estado(self, current: Optional[Dict], consecutivo_ot: int, cod_estado: int) -> Dict:
        """Cambia el estado de una OT desde el tablero, con reglas por rol:
        - Mecánico: solo SUS OT y solo a Pendiente/En Proceso/Completada.
        - Admin/Recepcionista: cualquier OT a cualquier estado.
        El RLS ya acota al taller del usuario."""
        if current is None:
            raise DomainException("No autenticado", HTTP_403_FORBIDDEN)
        if cod_estado not in ESTADOS_VALIDOS:
            raise DomainException("Estado inválido", 400)

        ot = await self.repo.get_ot_mecanico(consecutivo_ot)
        if not ot:
            raise DomainException("Orden no encontrada", HTTP_404_NOT_FOUND)

        rol = current.get("COD_ROL_PRF_USU")
        if rol == ROL_MECANICO:
            if ot.get("DOCUMENTO_USU_MC_OT") != current.get("DOCUMENTO_USU"):
                raise DomainException("Solo puedes mover tus propias órdenes", HTTP_403_FORBIDDEN)
            if cod_estado not in ESTADOS_MECANICO:
                raise DomainException("No puedes mover la orden a ese estado", HTTP_403_FORBIDDEN)
        elif rol not in ROLES_GESTOR:
            raise DomainException("Sin permisos para cambiar el estado", HTTP_403_FORBIDDEN)

        await self.repo.actualizar_estado(consecutivo_ot, cod_estado)
        return {"consecutivo_ot": consecutivo_ot, "cod_estado": cod_estado}

    @staticmethod
    def _map(f: Dict) -> TableroItem:
        fecha = f.get("FECHA_ELABORACION_OT")
        return TableroItem(
            consecutivo_ot=f.get("CONSECUTIVO_OT"),
            fecha=str(fecha) if fecha else None,
            placa=f.get("PLACA_MOT"),
            marca=f.get("MARCA_MOTO"),
            cliente=f.get("NOMBRE_COMPLETO_CLIENTE"),
            servicio=f.get("OBSERVACION_OT"),
            estado=f.get("ESTADO_OT"),
            cod_estado=f.get("COD_OT_EST_OT"),
            mecanico=f.get("MECANICO"),
            documento_mecanico=f.get("DOCUMENTO_MECANICO"),
        )
