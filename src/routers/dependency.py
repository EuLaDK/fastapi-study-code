from typing import Annotated

from fastapi import APIRouter, Depends

router = APIRouter()


async def common_parameters(q: str | None = None, skip: int = 0, limit: int = 10):
    return {"q": q, "skip": skip, "limit": limit}


@router.get("/items/")
async def read_items(commons: Annotated[dict, Depends(common_parameters)]):
    return commons


async def get_resource():
    resource = {"status": "已连接"}
    print("创建资源")
    try:
        yield resource
    finally:
        print("释放资源")


@router.get("/yield/")
async def use_resource(resource: Annotated[dict, Depends(get_resource)]):
    return resource
