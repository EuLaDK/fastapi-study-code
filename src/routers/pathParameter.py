from fastapi import APIRouter, Path
from enum import Enum
from typing import Annotated

# 预设值
# 如果你的路径操作接收一个路径参数，但你希望可能有效的路径参数值是预设的，可以使用标准Python Enum

# 创建 Enum 类
# 导入 Enum 并创建继承自 str 和 Enum 的子类
# 通过从 str 继承，API 文档就能把值的类型定义为字符串，并且能正确渲染，然后创建包含固定值的类属性

class ModelName(str, Enum):
    alexnet = 'alexnet'
    resnet = 'resnet'
    densenet = 'densenet'

router = APIRouter()

@router.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    print('-----------------------', model_name.value, '-----------------------')
    if model_name is ModelName.alexnet:
        #直接返回枚举对象，FastAPI 会自动取它的`.value`序列化为字符串返回给前端
        return {"model_name": model_name, "message": "Deep Learning FTW!"}
    elif model_name is ModelName.resnet:
        return {"model_name": model_name, "message": "ResNet is great!"}
    else:
        return {"model_name": model_name, "message": "DenseNet is awesome!"}

# 路径转换器
# 直接使用 Starlette 的选项，就可以用如下 URL 声明包含路径的路径参数：
# /files/{file_path:path} 参数名为 file_path，结尾部分的 :path 说明该参数应匹配任意路径
@router.get("/files/{file_path:path}")
async def read_file(file_path: str):
    return {"file_path": file_path}


# 数值校验路径的
# gt：大于（greater than）
# ge：大于等于（greater than or equal）
# lt：小于（less than）
# le：小于等于（less than or equal）
@router.get("/vaild/{item_id}")
async def read_vaild(
    item_id: Annotated[int, Path(title="The ID of the item to get", gt=0, le=100)],
    q: str
):
    result = {"item_id": item_id}
    if q:
        result.update({"q":q})
    return result