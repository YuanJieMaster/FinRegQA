"""
FinRegQA 用户API路由
User API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import UserResponse, UserProfileResponse, UserUpdate, SessionListResponse, MessageResponse
from app.crud import user as user_crud
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """获取当前用户个人信息"""
    return current_user


@router.put("/me", response_model=UserProfileResponse)
async def update_current_user_profile(user_data: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """修改当前用户个人信息"""
    if user_data.email and user_data.email != current_user.email:
        existing_user = user_crud.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已被其他用户使用")
    return user_crud.update_user(db, current_user, user_data)


@router.get("/me/sessions", response_model=SessionListResponse)
async def get_user_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户的会话列表"""
    sessions = user_crud.get_user_sessions(db, current_user.id)
    return SessionListResponse(total=len(sessions), sessions=sessions)


@router.delete("/me/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(session_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """撤销指定会话"""
    from app.models.user import UserSession
    session = db.query(UserSession).filter(UserSession.id == session_id, UserSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    session.is_active = False
    db.commit()
    return MessageResponse(message="会话已撤销")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """通过ID获取用户信息"""
    user = user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user
