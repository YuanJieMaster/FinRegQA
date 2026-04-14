"""
FinRegQA 用户CRUD操作
User CRUD operations
"""
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta

from app.models.user import User, PasswordResetToken, UserSession
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.core.security import create_refresh_token, create_email_verification_token, create_password_reset_token
from app.core.email import email_sender
from app.core.config import settings


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        email_verified=False,
        verification_token=create_email_verification_token(user_data.email)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    email_sender.send_verification_email(to_email=user.email, username=user.username, token=user.verification_token)
    return user


def update_user(db: Session, user: User, user_data: UserUpdate) -> User:
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_user_password(db: Session, user: User, new_password: str) -> User:
    user.password_hash = get_password_hash(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def verify_user_email(db: Session, user: User) -> User:
    user.email_verified = True
    user.verification_token = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_last_login(db: Session, user: User) -> None:
    user.last_login = datetime.utcnow()
    db.add(user)
    db.commit()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_user_tokens(db: Session, user: User, user_agent: str = None, ip_address: str = None) -> dict:
    active_sessions = db.query(UserSession).filter(
        UserSession.user_id == user.id, UserSession.is_active == True
    ).count()
    
    if active_sessions >= settings.MAX_SESSIONS_PER_USER:
        oldest_session = db.query(UserSession).filter(
            UserSession.user_id == user.id, UserSession.is_active == True
        ).order_by(UserSession.created_at.asc()).first()
        if oldest_session:
            db.delete(oldest_session)
            db.commit()
    
    refresh_token = create_refresh_token(user.id)
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    session = UserSession(
        user_id=user.id, refresh_token=refresh_token, user_agent=user_agent,
        ip_address=ip_address, expires_at=expires_at, is_active=True
    )
    db.add(session)
    db.commit()
    
    from app.core.security import create_access_token
    access_token = create_access_token(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


def refresh_user_tokens(db: Session, refresh_token: str) -> Optional[dict]:
    session = db.query(UserSession).filter(
        UserSession.refresh_token == refresh_token, UserSession.is_active == True
    ).first()
    
    if not session or session.expires_at < datetime.utcnow():
        if session:
            session.is_active = False
            db.commit()
        return None
    
    user = get_user_by_id(db, session.user_id)
    if not user or user.status != "active":
        return None
    
    from app.core.security import create_access_token
    access_token = create_access_token(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


def revoke_session(db: Session, refresh_token: str) -> bool:
    session = db.query(UserSession).filter(UserSession.refresh_token == refresh_token).first()
    if not session:
        return False
    session.is_active = False
    db.commit()
    return True


def revoke_all_user_sessions(db: Session, user_id: int) -> int:
    result = db.query(UserSession).filter(
        UserSession.user_id == user_id, UserSession.is_active == True
    ).update({"is_active": False})
    db.commit()
    return result


def get_user_sessions(db: Session, user_id: int) -> List[UserSession]:
    return db.query(UserSession).filter(
        UserSession.user_id == user_id, UserSession.is_active == True
    ).order_by(UserSession.created_at.desc()).all()


def create_password_reset(db: Session, user: User) -> str:
    token = create_password_reset_token(user.email)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    reset_token = PasswordResetToken(
        user_id=user.id, token=token, token_type="reset", expires_at=expires_at, used=False
    )
    db.add(reset_token)
    db.commit()
    email_sender.send_password_reset_email(to_email=user.email, username=user.username, token=token)
    return token


def verify_password_reset_token(db: Session, token: str) -> Optional[User]:
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token, PasswordResetToken.token_type == "reset",
        PasswordResetToken.used == False
    ).first()
    
    if not reset_token or reset_token.expires_at < datetime.utcnow():
        return None
    
    return get_user_by_id(db, reset_token.user_id)


def use_password_reset_token(db: Session, token: str) -> bool:
    reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
    if not reset_token:
        return False
    reset_token.used = True
    db.commit()
    return True


def resend_verification_email(db: Session, user: User) -> bool:
    user.verification_token = create_email_verification_token(user.email)
    db.add(user)
    db.commit()
    return email_sender.send_verification_email(to_email=user.email, username=user.username, token=user.verification_token)
