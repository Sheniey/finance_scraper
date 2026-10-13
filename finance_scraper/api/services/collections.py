import base64
import binascii
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel

from api.exceptions.report import InvalidCollectionQueryError
from api.schemas.base import CollectionResponse, PaginationResponse
from api.schemas.query import CollectionQuery


def _decode_cursor(value: str) -> int:
    try:
        decoded: bytes = base64.urlsafe_b64decode(
            value + '=' * (-len(value) % 4),
        )
        prefix, offset_text = decoded.decode('ascii').split(':', maxsplit=1)
        offset: int = int(offset_text)
    except (binascii.Error, UnicodeDecodeError, ValueError) as e:
        raise InvalidCollectionQueryError('page_cursor is invalid') from e
    if prefix != 'v1' or offset < 0:
        raise InvalidCollectionQueryError('page_cursor is invalid')
    return offset


def _encode_cursor(offset: int) -> str:
    value: bytes = f'v1:{offset}'.encode('ascii')
    return base64.urlsafe_b64encode(value).decode('ascii').rstrip('=')


def _sort_value(value: Any) -> tuple[int, Any]:
    if value is None:
        return (1, '')
    if isinstance(value, (int, float, bool)):
        return (0, value)
    return (0, str(value).casefold())


def _matches_filter(actual: Any, expected: Any) -> bool:
    if actual is None or isinstance(actual, (int, float, bool)):
        return actual == expected
    return str(actual) == str(expected)


def collection_response(
    items: Sequence[BaseModel],
    query: CollectionQuery,
    *,
    allowed_fields: set[str],
    allowed_sort_fields: set[str],
    allowed_filter_fields: set[str],
    default_sort: tuple[str, ...] = (),
) -> CollectionResponse:
    field_names: set[str] = set(allowed_fields)
    selected_fields: tuple[str, ...] = query.fields or tuple(sorted(field_names))
    invalid_fields: set[str] = set(selected_fields) - field_names
    if invalid_fields:
        raise InvalidCollectionQueryError(
            f'Unsupported fields: {", ".join(sorted(invalid_fields))}',
        )

    invalid_filters: set[str] = set(query.filters) - allowed_filter_fields
    if invalid_filters:
        raise InvalidCollectionQueryError(
            f'Unsupported filters: {", ".join(sorted(invalid_filters))}',
        )

    serialized_items: list[dict[str, Any]] = [
        item.model_dump(mode='json', exclude={'success'})
        for item in items
    ]
    filtered_items: list[dict[str, Any]] = [
        item
        for item in serialized_items
        if all(
            _matches_filter(item.get(key), expected)
            for key, expected in query.filters.items()
        )
    ]

    sort_fields: tuple[str, ...] = query.sort or default_sort
    for sort_field in sort_fields:
        normalized_field: str = sort_field.lstrip('-+')
        if normalized_field not in allowed_sort_fields:
            raise InvalidCollectionQueryError(
                f'Unsupported sort field: {normalized_field}',
            )
    for sort_field in reversed(sort_fields):
        descending: bool = sort_field.startswith('-')
        name: str = sort_field.lstrip('-+')
        filtered_items.sort(
            key=lambda item: _sort_value(item.get(name)),
            reverse=descending,
        )

    total: int = len(filtered_items)
    page: int | None = query.page
    if query.page_cursor is not None:
        start: int = _decode_cursor(query.page_cursor)
    else:
        page = page or 1
        start = (page - 1) * query.page_size
    end: int = start + query.page_size
    has_more: bool = end < total
    next_cursor: str | None = _encode_cursor(end) if has_more else None
    selected_items: list[dict[str, Any]] = [
        {
            field: item[field]
            for field in selected_fields
            if field in item
        }
        for item in filtered_items[start:end]
    ]

    return CollectionResponse(
        items=selected_items,
        pagination=PaginationResponse(
            page=page,
            page_size=query.page_size,
            total=total,
            has_more=has_more,
            next_cursor=next_cursor,
        ),
    )
