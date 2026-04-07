"""
FinRegQA 安全模块
Security utilities: JWT, password hashing
"""
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from ..models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """创建刷新令牌"""
    expire = datetime.utcnow() + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_password_reset_token(email: str) -> str:
    """创建密码重置令牌"""
    expire = datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": email, "exp": expire, "type": "password_reset"}
    return jwt.encode(payload, settings.PASSWORD_RESET_SECRET_KEY, algorithm=settings.ALGORITHM)


def create_email_verification_token(email: str) -> str:
    """创建邮箱验证令牌"""
    expire = datetime.utcnow() + timedelta(hours=24)
    payload = {"sub": email, "exp": expire, "type": "email_verification"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, secret_key: str = None) -> Optional[dict]:
    """解码JWT令牌"""
    try:
        return jwt.decode(token, secret_key or settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_access_token(token: str) -> Optional[int]:
    """验证访问令牌"""
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        try:
            return int(payload.get("sub"))
        except (TypeError, ValueError):
            return None
    return None


def verify_refresh_token(token: str) -> Optional[int]:
    """验证刷新令牌"""
    payload = decode_token(token)
    if payload and payload.get("type") == "refresh":
        try:
            return int(payload.get("sub"))
        except (TypeError, ValueError):
            return None
    return None


def verify_password_reset_token(token: str, db: Session = None) -> Optional[str]:
    """验证密码重置令牌"""
    payload = decode_token(token, settings.PASSWORD_RESET_SECRET_KEY)
    if payload and payload.get("type") == "password_reset":
        return payload.get("sub")
    return None


def verify_email_verification_token(token: str) -> Optional[str]:
    """验证邮箱验证令牌"""
    payload = decode_token(token)
    if payload and payload.get("type") == "email_verification":
        return payload.get("sub")
    return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="令牌无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user_id = verify_access_token(token)
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户账户已被禁用")
    
    return user
