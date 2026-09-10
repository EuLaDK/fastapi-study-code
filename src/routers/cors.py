from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def cors_example():
    return {"message": "跨域请求成功"}
