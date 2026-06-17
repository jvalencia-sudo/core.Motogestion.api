from repository.base_repository import BaseRepository


class ImpuestoRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="impuestos",
            primary_key="cod_imp",
            omit_key=True,
            sequence_name="seq_impuestos"
        )
