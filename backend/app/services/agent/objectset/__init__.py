"""ObjectSet: Immutable query builder for Omaha objects."""

from dataclasses import dataclass, field, replace
from typing import Any, Dict, Optional

@dataclass(frozen=True)
class Filter:
    """Immutable filter condition."""
    field: str
    operator: str
    value: Any

@dataclass(frozen=True)
class Sort:
    """Immutable sort specification."""
    field: str
    desc: bool = False

@dataclass(frozen=True)
class ObjectSet:
    """Immutable query builder for Omaha objects."""
    object_type: str
    selected: tuple = field(default_factory=tuple)
    filters: tuple = field(default_factory=tuple)
    sorts: tuple = field(default_factory=tuple)
    limit: Optional[int] = None

    def where(self, **conditions) -> "ObjectSet":
        """Add filter conditions (operator defaults to 'eq')."""
        new_filters = list(self.filters)
        for field, value in conditions.items():
            new_filters.append(Filter(field=field, operator="eq", value=value))
        return replace(self, filters=tuple(new_filters))

    def select(self, *fields) -> "ObjectSet":
        """Replace selected columns."""
        return replace(self, selected=tuple(fields))

    def order_by(self, field: str, desc: bool = False) -> "ObjectSet":
        """Add sort specification."""
        new_sorts = list(self.sorts)
        new_sorts.append(Sort(field=field, desc=desc))
        return replace(self, sorts=tuple(new_sorts))

    def limit_to(self, n: int) -> "ObjectSet":
        """Set result limit."""
        return replace(self, limit=n)

    def execute(self, omaha_service) -> Dict[str, Any]:
        """Compile and execute query using OmahaService."""
        from app.services.agent.objectset.compiler import compile_query_args
        compiled = compile_query_args(self)
        return omaha_service.query_objects(**compiled)

__all__ = ["Filter", "Sort", "ObjectSet"]
