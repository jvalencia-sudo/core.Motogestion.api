from typing import Dict, Optional

from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from domain.models.tablero.tablero_model import MecanicoItem, TableroItem, TableroResponse
from domain.services.ordenes_trabajo.validaciones_entrega import validar_saldo_para_entrega
from infrastructure.dependencies.current_user import usuario_tiene_permiso
from infrastructure.exceptions.domain_exception import DomainException
from repository.tablero.tablero_repositorio import TableroRepositorio
from repository.admin.admin_user_repository import AdminUserRepository

ESTADO_ENTREGADA = 4

# F1-12: ya no hay códigos de rol fijos -- "ve todo" (antes Administrador o
# Recepcionista) es ahora es_admin_usu o el permiso explícito ver_todo:tablero;
# cualquier otro perfil se trata como "solo lo suyo" (antes, el único código
# posible para eso era 2=Mecánico).
# F1-05: se saca el 5 (Anulada) de los estados válidos -- solo se llega ahí
# por PATCH /ordenes-trabajo/{id}/anular (con motivo y devolución de stock).
ESTADOS_VALIDOS = {1, 2, 3, 4, 6}
# Estados a los que un usuario SIN ver_todo:tablero puede llevar SUS OT (su flujo de trabajo)
ESTADOS_MECANICO = {1, 2, 3}  # Pendiente, En Proceso, Completada


class TableroServicio:
    def __init__(self):
        self.repo = TableroRepositorio()
        # Los mecánicos son usuarios: se leen por el repo dueño de esa tabla.
        self.usuario_repo = AdminUserRepository()

    async def _es_gestor(self, current: Optional[Dict]) -> bool:
        if current is None:
            return False
        if current.get("ES_ADMIN_USU"):
            return True
        return await usuario_tiene_permiso(current, "ver_todo:tablero")

    async def obtener(self, current: Optional[Dict], mecanico_param: Optional[str]) -> TableroResponse:
        """Alcance:
        - Admin o con ver_todo:tablero: ve todos o el mecánico que seleccione.
        - Cualquier otro perfil: SIEMPRE su propio tablero (ignora el parámetro).
        - Sin usuario identificado: tablero vacío (fail-closed)."""
        if current is None:
            return TableroResponse(es_gestor=False, mecanicos=[], items=[])

        es_gestor = await self._es_gestor(current)
        documento = mecanico_param or None if es_gestor else current.get("DOCUMENTO_USU")

        mecanicos = []
        if es_gestor:
            filas = await self.usuario_repo.listar_mecanicos()
            mecanicos = [
                MecanicoItem(documento_usu=f.get("DOCUMENTO_USU"), nombre=f.get("NOMBRE"))
                for f in filas
            ]

        filas = await self.repo.listar_ordenes(documento)
        items = [self._map(f) for f in filas]
        return TableroResponse(es_gestor=es_gestor, mecanicos=mecanicos, items=items)

    async def cambiar_estado(
        self,
        current: Optional[Dict],
        consecutivo_ot: int,
        cod_estado: int,
        confirmar_credito: bool = False,
    ) -> Dict:
        """Cambia el estado de una OT desde el tablero, con reglas por alcance:
        - Sin ver_todo:tablero (ni admin): solo SUS OT y solo a Pendiente/En Proceso/Completada.
        - Admin o con ver_todo:tablero: cualquier OT a cualquier estado (salvo Anulada).
        El RLS ya acota al taller del usuario."""
        if current is None:
            raise DomainException("No autenticado", HTTP_403_FORBIDDEN)
        if cod_estado not in ESTADOS_VALIDOS:
            raise DomainException("Estado inválido", 400)

        ot = await self.repo.get_ot_mecanico(consecutivo_ot)
        if not ot:
            raise DomainException("Orden no encontrada", HTTP_404_NOT_FOUND)

        es_gestor = await self._es_gestor(current)
        if not es_gestor:
            if ot.get("DOCUMENTO_USU_MC_OT") != current.get("DOCUMENTO_USU"):
                raise DomainException("Solo puedes mover tus propias órdenes", HTTP_403_FORBIDDEN)
            if cod_estado not in ESTADOS_MECANICO:
                raise DomainException("No puedes mover la orden a ese estado", HTTP_403_FORBIDDEN)

        # F1-07: arrastrar y soltar en el tablero es hoy el único camino que
        # la UI real usa para mover una orden a Entregada -- si queda con
        # saldo pendiente, exige confirmar "entregar a crédito".
        if cod_estado == ESTADO_ENTREGADA:
            await validar_saldo_para_entrega(consecutivo_ot, confirmar_credito)

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
