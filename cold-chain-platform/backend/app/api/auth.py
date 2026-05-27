from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.db import get_db
from app.models.reference import User

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    id: str
    username: str
    real_name: str
    role: str
    phone: str | None = None
    status: str


class LoginResponse(BaseModel):
    user: UserRead
    access_token: str
    token_type: str = "bearer"


def create_access_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=12)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "exp": expires,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def user_read(user: User) -> UserRead:
    return UserRead(
        id=str(user.id),
        username=user.username,
        real_name=user.real_name,
        role=user.role,
        phone=user.phone,
        status=user.status,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="账号或密码错误")
    if not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    return LoginResponse(user=user_read(user), access_token=create_access_token(user))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="请先登录")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="登录已失效") from exc
    user = db.get(User, user_id)
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="登录已失效")
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="当前账号无权执行此操作")
        return user

    return dependency
