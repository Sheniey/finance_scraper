
from typing import Any
from pydantic import BaseModel, Field


# ================================================== #
# RESPONSES                                          #
# ================================================== #

class OKResponse(BaseModel):
    success: bool = Field(True, description='Indicates if the request was successful')

class ErrorResponse(BaseModel):
    success: bool = Field(False, description='Indicates if the request was successful')
    error: str = Field(..., min_length=1, max_length=48, description='Error code or type')
    message: str = Field(..., min_length=1, max_length=256, description='Detailed error message')
    status_code: int = Field(..., description='HTTP status code associated with the error')

class PaginationResponse(BaseModel):
    page: int | None
    page_size: int
    total: int
    has_more: bool
    next_cursor: str | None = None

class CollectionResponse(OKResponse):
    items: list[dict[str, Any]]
    pagination: PaginationResponse
