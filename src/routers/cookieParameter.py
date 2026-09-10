from typing import Annotated
from fastapi import Cookie, APIRouter, Header
from pydantic import BaseModel

router = APIRouter()

@router.get("/items/")
async def read_items(ads_id: Annotated[str | None, Cookie()] = None):
    return {"ads_id": ads_id}


# Header 测试
@router.get("/header/")
async def read_header(x_token: Annotated[list[str] | None, Header()] = None):
    return {"X-Token values": x_token}

# cookie参数模型
class Cookies(BaseModel):
    # 限制只能传规定的，不可以传别的
    model_config = {"extra": "forbid"}

    session_id: str
    fatebook_tracker: str | None = None
    googall_tracker: str | None = None

@router.get("/modal/")
async def read_modal(cookies: Annotated[Cookies, Cookie()]):
    return cookies

# header 
class CommonHeaders(BaseModel):
    # 限制只能传规定的，不可以传别的 使用rest client测试的时候要把这行注释，因为rest client会默认增加一点请求头导致422报错
    model_config = {"extra": "forbid"}

    host: str
    save_data: bool
    if_modified_since: str | None = None
    traceparent: str | None = None
    x_tag: list[str] = []

@router.get("/headermodal/")
async def read_headermodal(headers: Annotated[CommonHeaders, Header()]):
    return headers