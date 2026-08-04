from typing import Dict, List

from repository.base_repository import BaseRepository


class PaqueteComponenteRepositorio(BaseRepository):
    """Componentes (receta/BOM) de los productos tipo PAQUETE. Acotado por RLS al taller."""

    def __init__(self):
        super().__init__(
            schema="",
            table_name="paquete_componentes",
            primary_key="cod_paq_comp",
            omit_key=True,
            sequence_name="seq_paquete_componentes",
        )

    async def listar_por_paquete(self, cod_pro_paq: int) -> List[Dict]:
        """Componentes de un paquete, con nombre/tipo/stock del producto incluido.
        Lee de la vista de dominio (no consulta la tabla productos directamente)."""
        query = (
            "select cod_pro_comp, nombre_pro, tipo_pro, stock_pro, cantidad_comp "
            "from vw_paquete_componentes "
            "where cod_pro_paq = :1 "
            "order by nombre_pro"
        )
        return await self.execute(query, (cod_pro_paq,))

    async def eliminar_por_paquete(self, cod_pro_paq: int) -> None:
        """Borra todos los componentes de un paquete (para el reemplazo total)."""
        await self.execute_non_query(
            "delete from paquete_componentes where cod_pro_paq = :1", (cod_pro_paq,)
        )
