import random
from fastapi import APIRouter, Query
from typing import Annotated, Literal
from pydantic import AfterValidator, BaseModel, Field
# 声明的参数不是路径参数时，路径操作函数会把参数自动解释为查询参数
router = APIRouter()

fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]

@router.get("/items/")
async def read_item(skip: int = 0, limit: int = 10):
    return fake_items_db[skip : skip + limit]

# 多个路径和多个查询参数 如果要把查询参数设置为必选，就不要声明默认值
@router.get("/users/{user_id}/items/{item_id}")
async def read_user_item(
    user_id: int, item_id: str, q: str | None = None, short: bool = False
): 
    item = {"item_id": item_id, "owner_id": user_id}
    if q:
        item.update({"q": q})
    if not short:
        item.update(
            {
                "description": "This is an amazing item that has a long description"
            }
        )
    return item

# 查询参数和字符串校验
# 可以添加最小最大限制，还可以添加正则, 默认值，如果不填默认值就是必填参数
# ^：必须以接下来的字符开头，前面没有其他字符。
# fixedquery：值必须精确等于 fixedquery。
# $：到此结束，在 fixedquery 之后没有更多字符。
@router.get("/check/")
async def read_check(q: Annotated[str | None, Query(min_length=10,max_length=30,pattern="^fixedquery$")] = 'fixedquery'):
    results = {"check": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results

# 查询参数列表多个值
@router.get("/list/")
async def read_list(q: Annotated[list[str] | None, Query()] = ['几', '多', '轮', '回', '少', '一', '人']):
    query_items = {"q": q}
    return query_items

# 也可以添加title，description
# 参数设置别名 http://127.0.0.1:8000/items/?item-query=foobaritems
# 弃用参数 deprecated=True 传给 Query
# 从openAPI中排除参数 include_in_schema 设为 False
# Query(
#             title="Query string",
#             description="Query string for the items to search in the database that have a good match",
#             min_length=3,
#             alias="item-query",
#             deprecated=True,
#             include_in_schema=False
#         ),


# 自定义校验
data = {
    "isbn-9781529046137": "The Hitchhiker's Guide to the Galaxy",
    "imdb-tt0371724": "The Hitchhiker's Guide to the Galaxy",
    "isbn-9781439512982": "Isaac Asimov: The Complete Stories, Vol. 2",
}

def check_valod_id(id: str):
    if not id.startswith(("isbn-", "imdb-")):
        raise ValueError('Invalid ID format, it must start with "isbn-" or "imdb-"')
    return id

@router.get("/valid/")
async def read_valid(
    id: Annotated[str | None, AfterValidator(check_valod_id)] = None,
):
    if id:
        item = data.get(id)
    else:
        id, item = random.choice(list(data.items()))
    return {"id": id, "name": item}

# 查询参数模型
class FilterParams(BaseModel):
    # 禁止额外的查询参数 加上这个就是不能有其他的没有定义的参数出现在URL上
    model_config = {"extra": "forbid"}

    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    order_by: Literal["created_at", "updated_at"] = "created_at"
    tags: list[str] = []

# 这样代表着你需要传的参数就是这几个
@router.get("/model/")
async def read_model(filter_query: Annotated[FilterParams, Query()]):
    return filter_query