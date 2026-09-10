from fastapi import APIRouter, Body
from pydantic import BaseModel, HttpUrl, Field
from typing import Annotated

class Item(BaseModel):
    name: str
    height: float
    description: str | None = None
    tax: float | None = None

router = APIRouter()

@router.post("/items/")
async def create_item(item: Item):
    item_dict = item.model_dump()
    if item.tax is not None:
        price_with_tax = item.height + item.tax
        item_dict.update({"price_with_tax": price_with_tax})
    return item_dict

# 请求体加路径参数 + 查询参数
@router.put("/items/{item_id}")
async def update_item(item_id: int, item: Item, query: str | None = None):
    result = {"item_id": item_id, **item.model_dump()}
    if query:
        result.update({"query": query})
    return result


# 请求体 多个请求体参数
# 请求体中如果想要扩展先前的模型，可以使用 Body 指示 FastAPI 将其作为请求体的另一个键进行处理
# 嵌入单个请求体参数 可以使用一个特殊的 Body 参数 embed item: Annotated[Item, Body(embed=True)]
class User(BaseModel):
    username: str
    full_name: str | None = None

@router.put("/many/{many_id}")
async def update_many(many_id: int, item: Item, user: User, importance: Annotated[int, Body()]):
    results = {"many_id": many_id, "item": item, "user": user, "importance": importance}
    return results


# 嵌套请求体
class Image(BaseModel):
    url: HttpUrl
    name: str

class ItemOffer(BaseModel):
    name: str
    description: str | None = Field(default="我不传看看什么情况", title="The description of the item", max_length=100)
    height: float = Field(default=1.70, gt=0)
    tax: float | None = None
    images: list[Image] | None = None

class Offer(BaseModel):
    name: str
    description: str | None = Field(default="不传看看描述")
    items: list[ItemOffer]

    # 声明请求示例数据
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
    "name": "offers",
    "items": [
        {
            "name": "itemoffer",
            "tax": 3.22,
            "images": [
                {
                    "url": "http://127.0.0.1:8000/test.png",
                    "name": "测试图片"
                },
                {
                    "url": "http://127.0.0.1:8000/test.png",
                    "name": "测试图片"
                }
            ]
        },
        {
            "name": "itemoffer",
            "tax": 3.22,
            "images": [
                {
                    "url": "http://127.0.0.1:8000/test.png",
                    "name": "测试图片"
                },
                {
                    "url": "http://127.0.0.1:8000/test.png",
                    "name": "测试图片"
                }
            ]
        }
    ]
}
            ]
        }
    }

@router.post("/offers/")
async def create_offer(offer: Offer):
    return offer