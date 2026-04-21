from typing import Type
from app.connectors.base import BaseConnector

_CONNECTORS: dict[str, Type[BaseConnector]] = {}


def register(type_name: str, cls: Type[BaseConnector]):
    _CONNECTORS[type_name] = cls


def get_connector(type_name: str, config: dict) -> BaseConnector:
    cls = _CONNECTORS.get(type_name)
    if not cls:
        raise ValueError(f"Unknown datasource type: {type_name}")
    return cls(config)
