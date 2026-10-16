from datetime import date
from typing import List, Optional

from starlette.status import HTTP_404_NOT_FOUND

from domain.contracts.superadmin.taller_superadmin_contract import (
    CrearNotaContract,
    NotaTallerContract,
    PagoHistorialContract,
    TallerDetalleContract,
    TallerListadoContract,
    UsuarioTallerContract,
)
from domain.contracts.talleres.taller_contract import TallerRegistroContract, TallerRegistroResponse
from domain.services.suscripciones.suscripcion_servicio import PRECIO_FUNDADOR
from domain.services.superadmin.metricas_servicio import MetricasServicio
from domain.services.talleres.taller_servicio import TallerServicio
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.tenant_context import set_tenant
from repository.admin.admin_user_repository import AdminUserRepository
from repository.pagos.pago_repositorio import PagoRepositorio
from repository.superadmin.nota_repositorio import NotaRepositorio
from repository.talleres.taller_repositorio import TallerRepositorio


class TalleresSuperAdminServicio:
    """Lista/detalle/creación de talleres y sus notas internas, para el panel de
    super-admin (F0-14). Reusa TallerServicio.registrar para 'crear taller
    manual' -- es exactamente el mismo flujo que el registro público."""

    def __init__(self):
        self.taller_repo = TallerRepositorio()
        self.pago_repo = PagoRepositorio()
        self.usuario_repo = AdminUserRepository()
        self.nota_repo = NotaRepositorio()
        self.metricas_servicio = MetricasServicio()

    @staticmethod
    def _dias_restantes(fecha_fin) -> Optional[int]:
        if not fecha_fin:
            return None
        return (fecha_fin - date.today()).days

    def _a_contrato_listado(self, fila: dict, metricas: dict) -> TallerListadoContract:
        return TallerListadoContract(
            cod_taller=fila.get("COD_TALLER"),
            nombre_tal=fila.get("NOMBRE_TAL"),
            nit_tal=fila.get("NIT_TAL"),
            correo_tal=fila.get("CORREO_TAL"),
            telefono_tal=fila.get("TELEFONO_TAL"),
            fecha_creacion_tal=fila.get("FECHA_CREACION_TAL"),
            estado_tal=fila.get("ESTADO_TAL"),
            dias_restantes=self._dias_restantes(fila.get("FECHA_FIN_SUSC_TAL")),
            precio_susc_tal=fila.get("PRECIO_SUSC_TAL"),
            es_fundador=fila.get("PRECIO_SUSC_TAL") == PRECIO_FUNDADOR,
            ultimo_pago_fecha=str(fila.get("ULTIMO_PAGO_FECHA")) if fila.get("ULTIMO_PAGO_FECHA") else None,
            ordenes_7d=metricas.get("ordenes_7d", 0),
            ordenes_30d=metricas.get("ordenes_30d", 0),
            usuarios_activos=metricas.get("usuarios_activos", 0),
            ultima_actividad=metricas.get("ultima_actividad"),
        )

    async def listar(self, estado: Optional[str] = None) -> List[TallerListadoContract]:
        filas = await self.taller_repo.listar_con_filtro(estado)
        todas_metricas = await self.metricas_servicio.metricas_de_todos_los_talleres()
        return [
            self._a_contrato_listado(f, todas_metricas.get(f.get("COD_TALLER"), {}))
            for f in filas
        ]

    async def detalle(self, cod_taller: int) -> TallerDetalleContract:
        fila = await self.taller_repo.obtener_con_ultimo_pago(cod_taller)
        if not fila:
            raise DomainException("Taller no encontrado", HTTP_404_NOT_FOUND)

        metricas = await self.metricas_servicio.metricas_de_un_taller(cod_taller)
        pagos = await self.pago_repo.listar_por_taller(cod_taller)

        set_tenant(cod_taller)
        usuarios = await self.usuario_repo.get_usuarios_perfiles()
        notas = await self.nota_repo.listar_por_taller(cod_taller)

        return TallerDetalleContract(
            taller=self._a_contrato_listado(fila, metricas),
            pagos=[
                PagoHistorialContract(
                    cod_pago=p.get("COD_PAGO"), nombre_plan=p.get("NOMBRE_PLAN"),
                    monto=p.get("MONTO"), estado=p.get("ESTADO"), medio=p.get("MEDIO"),
                    detalle_medio=p.get("DETALLE_MEDIO"), fecha=p.get("FECHA"),
                )
                for p in pagos
            ],
            usuarios=[
                UsuarioTallerContract(
                    documento_usu=u.get("DOCUMENTO_USU"), nombre_completo=u.get("NOMBRE_COMPLETO"),
                    rol=u.get("ROL"),
                    ultimo_ingreso=str(u.get("ULTIMO_INGRESO_USU")) if u.get("ULTIMO_INGRESO_USU") else None,
                )
                for u in usuarios
            ],
            notas=[
                NotaTallerContract(id=n.get("ID"), autor=n.get("AUTOR"), fecha=n.get("FECHA"), texto=n.get("TEXTO"))
                for n in notas
            ],
        )

    async def crear_manual(self, contract: TallerRegistroContract) -> TallerRegistroResponse:
        """Crea un taller a mano desde el panel (el dueño recibe la invitación por
        correo, igual que el registro público) -- mismo flujo, sin duplicar lógica."""
        return await TallerServicio().registrar(contract)

    async def crear_nota(self, cod_taller: int, contract: CrearNotaContract, autor: str) -> NotaTallerContract:
        taller = await self.taller_repo.get_by_id(cod_taller)
        if not taller:
            raise DomainException("Taller no encontrado", HTTP_404_NOT_FOUND)
        nota_id = await self.nota_repo.crear(cod_taller, autor, contract.texto)
        notas = await self.nota_repo.listar_por_taller(cod_taller)
        nota = next(n for n in notas if n.get("ID") == nota_id)
        return NotaTallerContract(
            id=nota.get("ID"), autor=nota.get("AUTOR"), fecha=nota.get("FECHA"), texto=nota.get("TEXTO")
        )
