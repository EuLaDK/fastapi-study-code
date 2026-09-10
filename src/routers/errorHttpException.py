from fastapi import APIRouter, HTTPException

# 自定义异常处理器
class UnicornException(Exception):
    def __int__(self, name: str):
        self.name = name

router = APIRouter()

items = {"foo": "The Foo Wrestles"}
#可以给接口添加摘要和描述
# 以添加 summary 和 description：
@router.get("/items/{item_id}", summary="222", description="这是接口描述")
async def read_item(item_id: str):
    if item_id not in items:
        # 添加自定义响应头
        raise HTTPException(
            status_code=404,
            detail="Item not found",
            headers={"X-Error": "There goes my error"},
        )
    return {"item": items[item_id]}


