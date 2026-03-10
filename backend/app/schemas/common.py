from pydantic import BaseModel
from typing import Generic, TypeVar, Any
from uuid import UUID

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "OK"


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Any = None
