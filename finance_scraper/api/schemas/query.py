
import json
from dataclasses import dataclass
from typing import Any
from fastapi import Query

from api.exceptions.report import InvalidCollectionQueryError


@dataclass(frozen=True, slots=True)
class CollectionQuery:
    page: int | None
    page_size: int
    page_cursor: str | None
    fields: tuple[str, ...] | None
    sort: tuple[str, ...]
    filters: dict[str, Any]

def _split_values(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    values: tuple[str, ...] = tuple(
        item.strip()
        for item in value.split(',')
        if item.strip()
    )
    if not values:
        raise InvalidCollectionQueryError('List query values cannot be blank')
    return values

def _parse_filters(value: str | None) -> dict[str, Any]:
    if value is None:
        return {}
    try:
        parsed: Any = json.loads(value)
    except json.JSONDecodeError as e:
        raise InvalidCollectionQueryError(
            'filter must be a JSON object of exact-match values',
        ) from e
    if not isinstance(parsed, dict):
        raise InvalidCollectionQueryError('filter must be a JSON object')
    if any(
        not isinstance(item, (str, int, float, bool)) and item is not None
        for item in parsed.values()
    ):
        raise InvalidCollectionQueryError(
            'filter values must be scalar JSON values',
        )
    return parsed

def get_collection_query(
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    page_cursor: str | None = Query(default=None, min_length=1, max_length=256),
    fields: str | None = Query(default=None, min_length=1, max_length=512),
    sort: str | None = Query(default=None, min_length=1, max_length=256),
    filter_value: str | None = Query(
        default=None,
        alias='filter',
        min_length=1,
        max_length=2048,
    ),
) -> CollectionQuery:
    if page is not None and page_cursor is not None:
        raise InvalidCollectionQueryError(
            'page and page_cursor cannot be used together',
        )
    return CollectionQuery(
        page=page,
        page_size=page_size,
        page_cursor=page_cursor,
        fields=_split_values(fields),
        sort=_split_values(sort) or (),
        filters=_parse_filters(filter_value),
    )
