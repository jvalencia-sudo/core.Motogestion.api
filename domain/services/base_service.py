import re
from abc import ABC, abstractmethod
from typing import Dict, TypeVar, Generic, List, Optional, Tuple, Any, Union, Type

from pydantic import BaseModel

from repository.base_repository import BaseRepository

T = TypeVar("T")
TR = TypeVar("TR")
OT = TypeVar("OT")
Params = Tuple[Any]


class BaseService(ABC, Generic[T, TR]):
    def __init__(self, repository: Union[BaseRepository, TR]):
        self.repository: Union[BaseRepository, TR] = repository

    async def get_all(self) -> List[T]:
        results = await self.repository.get_all()
        return self.__parse_all__(results)

    async def create(self, model) -> Union[int, str]:
        return await self.repository.create(model)

    async def update(self, model) -> bool:
        await self.repository.update(model)
        return True

    async def get_by_id(self, entity_id: Union[int, str]) -> Optional[T]:
        result = await self.repository.get_by_id(entity_id)
        if result:
            return self.__parse__(result)
        return None

    async def delete(self, entity_id: Union[int, str]) -> bool:
        await self.repository.delete(entity_id)
        return True

    def __normalize_keys__(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza las claves a snake_case minúsculas para que Pydantic
        pueda usar su alias_generator (to_camel).

        - 'COD_ROL' → 'cod_rol'
        - 'NOMBRE_ROL' → 'nombre_rol'
        - 'codRol' → 'cod_rol'
        - 'nombreRol' → 'nombre_rol'
        """
        import re

        def to_snake_case(s: str) -> str:
            # Si ya tiene guiones bajos, solo convertir a minúsculas
            if '_' in s:
                return s.lower()

            # Convertir camelCase a snake_case
            # 'codRol' → 'cod_rol'
            # 'nombreRol' → 'nombre_rol'
            s = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
            s = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s)
            return s.lower()

        return {to_snake_case(k): v for k, v in record.items()}

    @abstractmethod
    def __parse__(self, record: Dict) -> T:
        pass

    def __parse_all__(self, records: List[Dict]) -> List[T]:
        normalized = [self.__normalize_keys__(r) for r in records]
        return [self.__parse__(r) for r in normalized]

    def __parse_all_custom__(
        self, records: List[Dict], model: Type[Union[BaseModel, OT]]
    ) -> List[OT]:
        normalized = [self.__normalize_keys__(r) for r in records]
        return [model.model_validate(r) for r in normalized]

    def __parse_custom__(
        self, record: Dict, model: Type[Union[BaseModel, OT]]
    ) -> OT:
        """
        Normaliza y convierte un único registro a un modelo Pydantic específico.
        Proporciona tipado estático completo sin exponer el dict intermedio.
        """
        normalized = self.__normalize_keys__(record)
        return model.model_validate(normalized)
