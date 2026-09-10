from typing import Annotated

from fastapi import Depends, APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "fakehashedsecret",
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderson",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecret2",
        "disabled": True,
    },
}

router = APIRouter()

def fake_hash_password(password: str):
    return "fakehashed" + password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User(BaseModel):
    username:str
    email: str
    full_name: str | None = None
    disabled: bool | None = None

class UserInDB(User):
    hashed_password: str

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def fake_decode_token(token):
    user = get_user(fake_users_db, token)
    return user

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = fake_decode_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@router.get("/items/")
async def read_item(token: Annotated[str, Depends(oauth2_scheme)]):
    return {"token": token}

@router.get("/user/me")
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user

@router.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(status_code=400, detail="需要密码和用户名")
    user = UserInDB(**user_dict)
    hashed_password = fake_hash_password(form_data.password)
    # print(hashed_password, user.hashed_password)
    if not hashed_password == user.hashed_password:
        raise HTTPException(status_code=400, detail="密码错误")

    return {"access_token": user.username, "token_type": "bearer"}

# Client 请求 GET /users/me + Authorization: Bearer abc123
#         ↓
# FastAPI解析接口 read_users_me，发现依赖 get_current_user
#         ↓
# 执行 get_current_user，它又依赖 oauth2_scheme
#         ↓
# 执行 OAuth2PasswordBearer：
#     读Authorization头，校验Bearer格式，提取token字符串 "abc123"
#         ↓
# token传入 get_current_user
#         ↓
# fake_decode_token("abc123") → 返回 User对象
#         ↓
# User对象返回，作为 get_current_user 的返回值，赋值给 current_user
#         ↓
# 执行 read_users_me，return current_user
#         ↓
# 返回JSON给客户端
