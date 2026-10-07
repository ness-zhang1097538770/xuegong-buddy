"""查寝考勤 API。"""

import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.dorm import Dorm, DormCheck
from app.models.todo import TodoItem
from app.models.operation_log import OperationLog

router = APIRouter(prefix="/dorm", tags=["查寝考勤"])


@router.get("/grid")
def get_dorm_grid(
    building: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回宿舍三色网格数据，按楼栋楼层分组。"""
    query = db.query(Dorm).filter(Dorm.owner_id == user.id)
    if building:
        query = query.filter(Dorm.building == building)

    dorms = query.order_by(Dorm.building, Dorm.floor, Dorm.room).all()

    # 获取今日查寝记录
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    check_map = {}
    checks = (
        db.query(DormCheck)
        .filter(DormCheck.date == today, DormCheck.operator_id == user.id)
        .all()
    )
    for c in checks:
        check_map[c.dorm_id] = c

    # 按楼栋楼层分组
    buildings = {}
    for d in dorms:
        b = d.building or "未命名楼栋"
        f = d.floor or "1F"
        if b not in buildings:
            buildings[b] = {}
        if f not in buildings[b]:
            buildings[b][f] = []

        check = check_map.get(d.id)
        status = d.status
        if check:
            status = check.status

        buildings[b][f].append({
            "id": d.id,
            "room": d.room,
            "members": json.loads(d.members) if d.members else [],
            "status": status,  # unchecked / normal / abnormal
            "abnormal_type": check.abnormal_type if check else "",
            "note": check.note if check else "",
        })

    return {"buildings": buildings, "today": today}


@router.get("/buildings")
def list_buildings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回楼栋列表。"""
    buildings = (
        db.query(Dorm.building)
        .filter(Dorm.owner_id == user.id, Dorm.building != "")
        .distinct()
        .all()
    )
    return {"buildings": sorted([b[0] for b in buildings if b[0]])}


@router.get("/anomalies")
def get_anomalies(
    building: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回异常宿舍列表。"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    query = (
        db.query(DormCheck)
        .filter(
            DormCheck.date == today,
            DormCheck.status == "abnormal",
            DormCheck.operator_id == user.id,
        )
    )
    if building:
        query = query.join(Dorm).filter(Dorm.building == building)

    checks = query.all()
    results = []
    for c in checks:
        dorm = db.query(Dorm).filter(Dorm.id == c.dorm_id).first()
        results.append({
            "id": c.id,
            "dorm_id": c.dorm_id,
            "building": dorm.building if dorm else "",
            "room": dorm.room if dorm else "",
            "abnormal_type": c.abnormal_type,
            "note": c.note,
            "members": json.loads(dorm.members) if dorm and dorm.members else [],
        })

    return {"anomalies": results}


@router.post("/check")
def mark_dorm_check(
    dorm_id: int = Query(...),
    status: str = Query(..., regex="^(normal|abnormal)$"),
    abnormal_type: str = Query(""),
    note: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标记一间宿舍状态。"""
    dorm = db.query(Dorm).filter(
        Dorm.id == dorm_id, Dorm.owner_id == user.id
    ).first()
    if not dorm:
        raise HTTPException(status_code=404, detail="宿舍不存在")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 更新或创建今日检查记录
    check = (
        db.query(DormCheck)
        .filter(DormCheck.dorm_id == dorm_id, DormCheck.date == today)
        .first()
    )
    if check:
        check.status = status
        check.abnormal_type = abnormal_type
        check.note = note
    else:
        check = DormCheck(
            dorm_id=dorm_id,
            date=today,
            status=status,
            abnormal_type=abnormal_type,
            note=note,
            operator_id=user.id,
        )
        db.add(check)

    dorm.status = status

    # 异常时创建待办
    if status == "abnormal":
        existing_todo = (
            db.query(TodoItem)
            .filter(
                TodoItem.source_type == "dorm",
                TodoItem.source_id == dorm_id,
                TodoItem.status == "pending",
            )
            .first()
        )
        if not existing_todo:
            todo = TodoItem(
                source_type="dorm",
                source_id=dorm_id,
                title=f"宿舍异常：{dorm.building} {dorm.room} - {abnormal_type or '异常'}",
                target_name=f"{dorm.building} {dorm.room}",
                due_date=today,
                priority=100,
                handler_id=user.id,
            )
            db.add(todo)

    log = OperationLog(
        user_id=user.id,
        action="dorm_check",
        detail=f"标记宿舍 {dorm.building} {dorm.room} 为 {status} | {abnormal_type}",
    )
    db.add(log)
    db.commit()

    return {"message": "已标记", "status": status}


@router.post("/seed-demo")
def seed_demo_dorms(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """生成演示宿舍数据。"""
    buildings = {
        "梅园 3 号楼": {"1F": ["301", "302", "303", "304", "305"], "2F": ["401", "402", "403", "404", "405"]},
        "兰园 5 号楼": {"1F": ["201", "202", "203", "204"], "2F": ["301", "302", "303"]},
    }
    names = ["张伟", "李强", "王磊", "赵明", "陈亮", "刘洋", "周涛", "吴昊", "孙策", "韩信", "刘备", "关羽"]

    count = 0
    for building, floors in buildings.items():
        for floor, rooms in floors.items():
            for i, room in enumerate(rooms):
                members = names[i*2:i*2+2] if i*2+2 <= len(names) else names[i*2:i*2+1]
                dorm = Dorm(
                    building=building,
                    floor=floor,
                    room=room,
                    members=json.dumps(members, ensure_ascii=False),
                    owner_id=user.id,
                )
                db.add(dorm)
                count += 1

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"入库失败: {str(e)}")
    return {"message": f"已生成 {count} 间演示宿舍"}