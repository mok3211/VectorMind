from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from server.config import settings


# 说明：
# - bcrypt 在 passlib==1.7.4 下与 bcrypt>=4 存在兼容性问题（会读取 bcrypt.__about__.__version__）
# - 为了减少环境依赖与“登录失败但不报错”的隐患，这里默认使用 pbkdf2_sha256
# - 如需更强方案可后续切 argon2（需要额外依赖）
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(*, subject: str, minutes: int | None = None) -> str:
    expire_minutes = minutes or settings.jwt_expire_minutes
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
