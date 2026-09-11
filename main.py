from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers.user import router as user_router
from src.routers.pathParameter import router as path_parameter_router
from src.routers.queryParameters import router as query_parameter_router
from src.routers.requestBody import router as request_body_router
from src.routers.cookieParameter import router as cookie_parameter_router
from src.routers.responseModel import router as response_model_router
from src.routers.form import router as form_router
from src.routers.errorHttpException import router as error_router
from src.routers.dependency import router as dependency_router
from src.routers.authSafe import router as auth_router
from src.routers.jwtToken import router as jwt_router
from src.routers.cors import router as cors_router
from src.routers.sqlmodel_example import router as sqlmodel_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 单个注册
# 把routers里面的user的router注册到app上
app.include_router(user_router, prefix="/users", tags=["用户模块"])
# 把routers里面的pathParameter的router注册到app上
app.include_router(path_parameter_router, prefix="/path", tags=["路径参数模块"])
app.include_router(query_parameter_router, prefix="/query", tags=["查询参数模块"])
app.include_router(request_body_router, prefix="/request", tags=["请求体模块"])
app.include_router(cookie_parameter_router, prefix="/cookie", tags=["cookie模块"])
app.include_router(response_model_router, prefix='/response', tags=["响应模块"])
app.include_router(form_router, prefix="/form", tags=["表单模块"])
app.include_router(error_router, prefix="/errors", tags=["错误处理模块"])
app.include_router(dependency_router, prefix="/dependencies", tags=["依赖项模块"])
app.include_router(auth_router, prefix="/auth", tags=["安全验证"])
app.include_router(jwt_router, prefix="/jwt", tags=["jwt令牌校验"])
app.include_router(cors_router, prefix="/cors", tags=["CORS跨域"])
app.include_router(sqlmodel_router, prefix="/db", tags=["SQLModel数据库"])


# # 统一维护所有子路由配置
# routers_config = [
#     {"router": user_router, "prefix": "/users", "tags": ["用户模块"]},
#     {"router": path_parameter_router, "prefix": "/path", "tags": ["路径参数模块"]},
#     # 以后新增路由，在这里追加一行即可
#     # {"router": xxx_router, "prefix": "/xxx", "tags": ["xxx模块"]},
# ]

# # 循环批量注册
# for cfg in routers_config:
#     app.include_router(
#         cfg["router"],
#         prefix=cfg["prefix"],
#         tags=cfg["tags"]
#     )
