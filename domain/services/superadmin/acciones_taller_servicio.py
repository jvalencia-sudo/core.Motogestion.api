from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from domain.contracts.superadmin.accion_taller_contract import (
    AjustarPrecioContract,
    ExtenderPruebaContract,
    PagoManualContract,
    SuspenderReactivarContract,
)
from infrastructure.exceptions.domain_exception import DomainException
from repository.pagos.pago_repositorio import PagoRepositorio
from repository.superadmin.auditoria_repositorio import AuditoriaRepositorio
from repository.talleres.taller_repositorio import TallerRepositorio

DIAS_PLAN = 30  # mismo valor que SuscripcionServicio: un pago (Wompi o manual) activa 30 días


class AccionesTallerServicio:
    """Las 4 acciones de super-admin sobre la suscripción de un taller (F0-14):
    todas exigen motivo y quedan en auditoria_superadmin, cada una como una
    única transacción (UPDATE taller + INSERT auditoría) -- o queda todo
    aplicado, o no queda nada a medias."""

    def __init__(self):
        self.taller_repo = TallerRepositorio()
        self.pago_repo = PagoRepositorio()
        self.auditoria_repo = AuditoriaRepositorio()

    async def _taller_o_404(self, cod_taller: int) -> dict:
        taller = await self.taller_repo.get_suscripcion(cod_taller)
        if not taller:
            raise DomainException("Taller no encontrado", HTTP_404_NOT_FOUND)
        return taller

    async def extender_prueba(self, cod_taller: int, contract: ExtenderPruebaContract, usuario: str) -> dict:
        taller = await self._taller_o_404(cod_taller)
        if taller.get("ESTADO_TAL") != "prueba":
            raise DomainException(
                "Este taller no está en prueba -- usa pago manual o ajustar precio",
                HTTP_400_BAD_REQUEST,
            )
        statements = [
            self.taller_repo.statement_extender_prueba(cod_taller, contract.dias),
            self.auditoria_repo.statement_registrar(
                usuario, cod_taller, "extender_prueba", contract.motivo,
                valor_anterior={"fecha_fin_susc_tal": str(taller.get("FECHA_FIN_SUSC_TAL"))},
                valor_nuevo={"dias_extendidos": contract.dias},
            ),
        ]
        await self.taller_repo.execute_transaction(statements)
        return {"success": True, "message": f"Prueba extendida {contract.dias} días"}

    async def pago_manual(self, cod_taller: int, contract: PagoManualContract, usuario: str) -> dict:
        taller = await self._taller_o_404(cod_taller)
        statements = [
            (
                "INSERT INTO pagos (cod_taller, nombre_plan, monto, referencia, estado, medio, detalle_medio) "
                "VALUES (:1, :2, :3, :4, 'APPROVED', 'MANUAL', :5)",
                (cod_taller, contract.nombre_plan, contract.monto,
                 f"MANUAL-{cod_taller}-{usuario}-{contract.monto}", contract.detalle_medio),
            ),
            self.taller_repo.statement_congelar_precio_si_nulo(cod_taller, contract.monto),
            self.taller_repo.statement_activar_suscripcion(cod_taller, contract.nombre_plan, DIAS_PLAN),
            self.auditoria_repo.statement_registrar(
                usuario, cod_taller, "pago_manual", contract.motivo,
                valor_anterior={"estado_tal": taller.get("ESTADO_TAL")},
                valor_nuevo={
                    "monto": contract.monto, "detalle_medio": contract.detalle_medio,
                    "nombre_plan": contract.nombre_plan,
                },
            ),
        ]
        await self.taller_repo.execute_transaction(statements)
        return {"success": True, "message": "Pago manual registrado y suscripción activada"}

    async def suspender(self, cod_taller: int, contract: SuspenderReactivarContract, usuario: str) -> dict:
        return await self._cambiar_estado(cod_taller, "suspendido", "suspender", contract, usuario)

    async def reactivar(self, cod_taller: int, contract: SuspenderReactivarContract, usuario: str) -> dict:
        return await self._cambiar_estado(cod_taller, "activo", "reactivar", contract, usuario)

    async def _cambiar_estado(
        self, cod_taller: int, estado_nuevo: str, accion: str,
        contract: SuspenderReactivarContract, usuario: str,
    ) -> dict:
        taller = await self._taller_o_404(cod_taller)
        statements = [
            self.taller_repo.statement_cambiar_estado(cod_taller, estado_nuevo),
            self.auditoria_repo.statement_registrar(
                usuario, cod_taller, accion, contract.motivo,
                valor_anterior={"estado_tal": taller.get("ESTADO_TAL")},
                valor_nuevo={"estado_tal": estado_nuevo},
            ),
        ]
        await self.taller_repo.execute_transaction(statements)
        return {"success": True, "message": f"Taller {estado_nuevo}"}

    async def ajustar_precio(self, cod_taller: int, contract: AjustarPrecioContract, usuario: str) -> dict:
        taller = await self._taller_o_404(cod_taller)
        statements = [
            self.taller_repo.statement_ajustar_precio(cod_taller, contract.precio_susc_tal),
            self.auditoria_repo.statement_registrar(
                usuario, cod_taller, "ajustar_precio", contract.motivo,
                valor_anterior={"precio_susc_tal": taller.get("PRECIO_SUSC_TAL")},
                valor_nuevo={"precio_susc_tal": contract.precio_susc_tal},
            ),
        ]
        await self.taller_repo.execute_transaction(statements)
        return {"success": True, "message": "Precio pactado actualizado"}
