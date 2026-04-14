"""
FinRegQA 认证API路由
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import (
    UserCreate, UserResponse, Token, PasswordChange, PasswordResetRequest,
    PasswordResetConfirm, RefreshTokenRequest, MessageResponse
)
from app.crud import user as user_crud
from app.core.security import get_current_user, verify_password, verify_password_reset_token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    if user_crud.get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    if user_crud.get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被注册")
    return user_crud.create_user(db, user_data)


@router.post("/login", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """用户登录"""
    user_agent = request.headers.get("user-agent", "")
    client_ip = request.client.host if request.client else ""
    
    user = user_crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误", headers={"WWW-Authenticate": "Bearer"})
    
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户账户已被禁用")
    
    user_crud.update_last_login(db, user)
    return user_crud.create_user_tokens(db, user, user_agent, client_ip)


@router.post("/logout", response_model=MessageResponse)
async def logout(refresh_token: RefreshTokenRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """用户登出"""
    user_crud.revoke_session(db, refresh_token.refresh_token)
    return MessageResponse(message="登出成功")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """登出所有设备"""
    count = user_crud.revoke_all_user_sessions(db, current_user.id)
    return MessageResponse(message=f"已撤销 {count} 个会话")


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """刷新访问令牌"""
    tokens = user_crud.refresh_user_tokens(db, refresh_data.refresh_token)
    if not tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌无效或已过期", headers={"WWW-Authenticate": "Bearer"})
    return tokens


@router.post("/password/change", response_model=MessageResponse)
async def change_password(password_data: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """修改密码"""
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")
    
    user_crud.change_user_password(db, current_user, password_data.new_password)
    user_crud.revoke_all_user_sessions(db, current_user.id)
    return MessageResponse(message="密码修改成功，请重新登录")


@router.post("/password/reset-request", response_model=MessageResponse)
async def request_password_reset(reset_data: PasswordResetRequest, db: Session = Depends(get_db)):
    """请求密码重置"""
    user = user_crud.get_user_by_email(db, reset_data.email)
    if user and user.status == "active":
        user_crud.create_password_reset(db, user)
    return MessageResponse(message="如果邮箱已注册，将会收到密码重置邮件")


@router.post("/password/reset-confirm", response_model=MessageResponse)
async def confirm_password_reset(reset_data: PasswordResetConfirm, db: Session = Depends(get_db)):
    """确认密码重置"""
    email = verify_password_reset_token(reset_data.token)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="重置令牌无效或已过期")
    
    user = user_crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    user_crud.change_user_password(db, user, reset_data.new_password)
    user_crud.use_password_reset_token(db, reset_data.token)
    user_crud.revoke_all_user_sessions(db, user.id)
    return MessageResponse(message="密码重置成功，请使用新密码登录")


@router.get("/verify-email", response_model=MessageResponse)
async def verify_email(token: str, db: Session = Depends(get_db)):
    """验证邮箱"""
    from app.core.security import verify_email_verification_token
    email = verify_email_verification_token(token)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证令牌无效或已过期")
    
    user = user_crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    if user.email_verified:
        return MessageResponse(message="邮箱已经验证过了")
    
    user_crud.verify_user_email(db, user)
    return MessageResponse(message="邮箱验证成功")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(reset_data: PasswordResetRequest, db: Session = Depends(get_db)):
    """重新发送验证邮件"""
    user = user_crud.get_user_by_email(db, reset_data.email)
    if not user:
        return MessageResponse(message="如果邮箱已注册且未验证，将会收到验证邮件")
    
    if user.email_verified:
        return MessageResponse(message="邮箱已经验证过了")
    
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户账户已被禁用")
    
    user_crud.resend_verification_email(db, user)
    return MessageResponse(message="验证邮件已发送，请查收")
