from abc import ABC, abstractmethod
from typing import Type, Any, Dict
from enum import Enum
from pydantic import BaseModel
from pydantic import ConfigDict


class EntityTypeEnum(str, Enum):
    AGENT = "AGENT"
    OBJECT = "OBJECT"
    WORLD = "WORLD"


def get_entity_type(cls):
    from genworlds.worlds.abstracts.world import AbstractWorld
    from genworlds.agents.abstracts.agent import AbstractAgent
    from genworlds.objects.abstracts.object import AbstractObject

    if issubclass(cls, AbstractAgent):
        return EntityTypeEnum.AGENT
    elif issubclass(cls, AbstractWorld):
        return EntityTypeEnum.WORLD
    elif issubclass(cls, AbstractObject):
        return EntityTypeEnum.OBJECT
    return None


class AbstractWorldEntity(BaseModel, ABC):
    model_config = ConfigDict(extra="allow")

    id: str
    entity_type: EntityTypeEnum
    entity_class: str
    name: str
    description: str

    @classmethod
    def create(
        cls: Type["AbstractWorldEntity"],
        entity: Any,
        **additional_world_properties: Any,
    ) -> "AbstractWorldEntity":
        entity_cls = type(entity)
        entity_data = {
            "id": entity.id,
            "entity_type": get_entity_type(entity_cls),
            "entity_class": entity_cls.__name__,
            "name": entity.name,
            "description": entity.description,
            **additional_world_properties,
        }
        return cls(**entity_data)
