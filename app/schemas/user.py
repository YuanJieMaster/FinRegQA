"""
FinRegQA Pydantic Schemas
Request/Response validation schemas
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import re


class UserBase(BaseModel):
    """用户基础Schema"""
    username: str = Field(..., min_length=6, max_length=20, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")


class UserCreate(UserBase):
    """用户注册Schema"""
    password: str = Field(..., min_length=8, max_length=50)
    confirm_password: str = Field(...)

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('密码必须包含字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含数字')
        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('两次输入的密码不一致')
        return v


class UserLogin(BaseModel):
    """用户登录Schema"""
    username: str = Field(...)
    password: str = Field(...)


class UserResponse(BaseModel):
    """用户响应Schema"""
    id: int
    username: str
    email: str
    email_verified: bool
    status: str
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfileResponse(UserResponse):
    """用户个人信息Schema"""
    pass


class UserUpdate(BaseModel):
    """用户信息更新Schema"""
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    """密码修改Schema"""
    old_password: str = Field(...)
    new_password: str = Field(..., min_length=8, max_length=50)
    confirm_password: str = Field(...)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('密码必须包含字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含数字')
        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('两次输入的密码不一致')
        return v


class Token(BaseModel):
    """Token响应Schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """刷新Token请求Schema"""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """密码重置请求Schema"""
    email: EmailStr = Field(...)


class PasswordResetConfirm(BaseModel):
    """密码重置确认Schema"""
    token: str = Field(...)
    new_password: str = Field(..., min_length=8, max_length=50)
    confirm_password: str = Field(...)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('密码必须包含字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含数字')
        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('两次输入的密码不一致')
        return v


class SessionInfo(BaseModel):
    """会话信息Schema"""
    id: int
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """会话列表响应Schema"""
    total: int
    sessions: list[SessionInfo]


class MessageResponse(BaseModel):
    """通用消息响应Schema"""
    message: str
    success: bool = True
