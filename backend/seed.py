"""一次性种子数据：创建邀请码"""
from app.models.base import init_db, SessionLocal
from app.models.invite_code import InviteCode

init_db()
db = SessionLocal()

for code_str in ["DEMO01", "DEMO02", "DEMO03"]:
    existing = db.query(InviteCode).filter(InviteCode.code == code_str).first()
    if not existing:
        db.add(InviteCode(code=code_str))
        print(f"创建: {code_str}")
    else:
        print(f"已存在: {code_str}")

db.commit()
db.close()
print("\n可用邀请码: DEMO01, DEMO02, DEMO03")