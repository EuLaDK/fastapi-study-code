from fastapi import APIRouter, Response
from typing import Any
from pydantic import BaseModel
from fastapi.responses import JSONResponse, RedirectResponse

router = APIRouter()

class Item(BaseModel):
    name: str
    tags: list[str] = []

@router.post("/items/", response_model=Item)
async def create_item(item: Item) -> Any:
    return item

@router.get("/items/", response_model=list[Item])
async def read_items() -> Any:
    return [
        {"name": "EuLa", "tags": ["a", "b"]},
        {"name": "EuLa", "tags": ["a", "b"]},
    ]

# 直接返回Respose RedirectResponse和JSONResponse都是Respose的子类所以没问题
# 禁用响应模型  @router.get("/portal")response_model=None 这个写了async def get_portal(teleport: bool = False) -> Response | dict:这个就不会报错，成立了
# response_model_exclude_unset=True 这样写返回的里面就不会包含有默认值的字段了
@router.get("/portal")
async def get_portal(teleport: bool = False) -> Response:
    if teleport:
        return RedirectResponse(url="https://www.youtube.com")
    return JSONResponse(content={"message": "Here your interdimensional portal"})

