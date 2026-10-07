"""认证业务：注册、登录。"""

import secrets
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.invite_code import InviteCode
from app.models.operation_log import OperationLog
from app.core.security import hash_password, verify_password, create_access_token


def register_user(db: Session, email: str, password: str, invite_code: str) -> User:
    """注册新用户，校验邀请码。"""
    # 检查邮箱是否已注册
    if db.query(User).filter(User.email == email).first():
        raise ValueError("该邮箱已注册")

    # 检查邀请码
    code = db.query(InviteCode).filter(
        InviteCode.code == invite_code, InviteCode.is_used == False
    ).first()
    if code is None:
        raise ValueError("邀请码无效或已被使用")

    # 创建用户
    user = User(
        email=email,
        password_hash=hash_password(password),
        role="member",
    )
    db.add(user)
    db.flush()  # 获取 user.id

    # 标记邀请码已用
    code.is_used = True
    code.used_by_email = email

    # 操作日志
    log = OperationLog(user_id=user.id, action="register", detail=f"用户 {email} 注册")
    db.add(log)

    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, email: str, password: str) -> dict:
    """登录，返回 token 和用户信息。"""
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise ValueError("邮箱或密码错误")
    if not verify_password(password, user.password_hash):
        raise ValueError("邮箱或密码错误")

    token = create_access_token(user.id)

    # 操作日志
    log = OperationLog(user_id=user.id, action="login", detail=f"用户 {email} 登录")
    db.add(log)
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


def generate_invite_codes(db: Session, count: int) -> list[str]:
    """生成邀请码。"""
    codes = []
    for _ in range(count):
        code_str = secrets.token_hex(4).upper()  # 8 位十六进制
        code = InviteCode(code=code_str)
        db.add(code)
        codes.append(code_str)
    db.commit()
    return codes