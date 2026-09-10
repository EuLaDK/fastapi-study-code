from typing import Annotated
from fastapi import APIRouter, Form, File, UploadFile
from pydantic import BaseModel

router = APIRouter()

class FormData(BaseModel):
    username: str
    password: str
    #禁止额外的表单字段
    model_config = {"extra": "forbid"}

#Form 是直接继承自 Body 的类。
@router.post("/login/")
async def login(data: Annotated[FormData, Form()]):
    return data


#File 是直接继承自 Form 的类。
# 但要注意，从 fastapi 导入的 Query、Path、File 等项，实际上是返回特定类的函数。
# 声明文件体必须使用

# 与bytes相比，使用UploadFile有多项优势：
# 无需在参数的默认值中使用File()
# 他使用spooled文件 文件会先存储在内存中，直到达到最大上限，超过该上线后会写入磁盘
# 因此，非常适合处理图像、视频、大型二进制等大文件，而不会占用所有内存
# 你可以获取上传文件的元数据 它提供file-like的async接口 它暴露了一个实际的 Python SpooledTemporaryFile 对象，你可以直接传给期望「file-like」对象的其他库。

@router.post("/files/")
async def create_file(file: Annotated[bytes, File()]):
    return {"file_size": len(file)}

@router.post("/uploadfile/")
async def create_upload_file(file: UploadFile):
    return {"filename": file.filename}