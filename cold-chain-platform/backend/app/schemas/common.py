from pydantic import BaseModel


class PageMeta(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20


class PageResponse[T](BaseModel):
    items: list[T]
    meta: PageMeta

