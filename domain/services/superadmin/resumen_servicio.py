from domain.contracts.superadmin.resumen_contract import (
    ResumenPlataformaContract,
    VencimientoProximoContract,
)
from domain.services.suscripciones.suscripcion_servicio import CUPOS_FUNDADOR, PRECIO_FUNDADOR
from repository.talleres.taller_repositorio import TallerRepositorio


class ResumenServicio:
    """Tablero de negocio del super-admin (F0-14): MRR, talleres por estado,
    cupos fundador, vencimientos próximos y conversión prueba->pago."""

    def __init__(self):
        self.taller_repo = TallerRepositorio()

    async def obtener(self) -> ResumenPlataformaContract:
        por_estado = await self.taller_repo.resumen_por_estado()
        talleres_por_estado = {f.get("ESTADO_TAL"): f.get("TOTAL") for f in por_estado}
        total_talleres = sum(talleres_por_estado.values())

        fundadores = await self.taller_repo.contar_por_precio_susc(PRECIO_FUNDADOR)
        vencimientos = await self.taller_repo.vencimientos_proximos(7)

        return ResumenPlataformaContract(
            mrr=await self.taller_repo.mrr(),
            talleres_por_estado=talleres_por_estado,
            cupos_fundador_restantes=max(CUPOS_FUNDADOR - fundadores, 0),
            total_talleres=total_talleres,
            conversion_prueba_pago=await self.taller_repo.conversion_prueba_pago(),
            vencimientos_proximos=[
                VencimientoProximoContract(
                    cod_taller=v.get("COD_TALLER"),
                    nombre_tal=v.get("NOMBRE_TAL"),
                    telefono_tal=v.get("TELEFONO_TAL"),
                    fecha_fin_susc_tal=v.get("FECHA_FIN_SUSC_TAL"),
                    dias_restantes=v.get("DIAS_RESTANTES"),
                )
                for v in vencimientos
            ],
        )
