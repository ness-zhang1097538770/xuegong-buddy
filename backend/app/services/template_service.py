"""模板服务：CRUD + 内置模板种子数据。"""

import json
from sqlalchemy.orm import Session
from app.models.template import Template

# === 内置模板定义 ===
BUILTIN_TEMPLATES = [
    {
        "name": "谈心谈话记录",
        "category": "谈话记录",
        "style": "soft",
        "description": "记录与学生的一对一谈心谈话内容",
        "system_prompt": "你是一位有亲和力的高校辅导员。请根据填写信息生成谈心谈话记录，语气温和、体现关心、不评判学生。",
        "user_prompt_template": """## 谈心谈话记录

谈话对象：{student_name}
班级：{class_name}
谈话时间：{date}
谈话地点：{location}
谈话主题：{topic}
背景说明：{background}

请按以下格式生成：
一、谈话背景与目的
二、学生陈述要点
三、辅导员反馈与建议
四、后续跟进计划

语气要求：温和关心，不使用批评语言。""",
        "variables": json.dumps(["student_name", "class_name", "date", "location", "topic", "background"]),
    },
    {
        "name": "主题班会方案",
        "category": "班会方案",
        "style": "formal",
        "description": "策划一次主题班会的完整方案",
        "system_prompt": "你是一位经验丰富的高校辅导员。请根据填写信息生成主题班会方案，格式规范、活动设计可操作。",
        "user_prompt_template": """## 主题班会方案

班会主题：{theme}
班级：{class_name}
时间：{date}
地点：{location}
活动目标：{goal}

请按以下格式生成：
一、班会背景与目标
二、班会流程设计（含时间分配）
三、互动环节设计
四、预期效果与总结要点""",
        "variables": json.dumps(["theme", "class_name", "date", "location", "goal"]),
    },
    {
        "name": "团日活动方案",
        "category": "班会方案",
        "style": "formal",
        "description": "策划一次团日活动的完整方案",
        "system_prompt": "你是一位团委工作指导老师。请生成规范的团日活动方案。",
        "user_prompt_template": """## 团日活动方案

活动主题：{theme}
团支部：{class_name}
活动时间：{date}
活动地点：{location}
活动目标：{goal}

请按以下格式生成：
一、活动背景与意义
二、活动流程安排
三、团员参与设计
四、活动总结与宣传方案""",
        "variables": json.dumps(["theme", "class_name", "date", "location", "goal"]),
    },
    {
        "name": "评优推荐意见",
        "category": "评优",
        "style": "formal",
        "description": "为学生撰写评优推荐意见",
        "system_prompt": "你是一位严谨的高校辅导员。请生成规范的评优推荐意见，突出学生优势，语言正式得体。",
        "user_prompt_template": """## 评优推荐意见

被推荐人：{student_name}
学号：{student_id}
班级：{class_name}
推荐奖项：{award_name}
主要事迹：{achievements}

请按以下格式生成：
一、思想政治表现
二、学业与科研能力
三、综合素质评价
四、推荐意见结论""",
        "variables": json.dumps(["student_name", "student_id", "class_name", "award_name", "achievements"]),
    },
    {
        "name": "困难生认定材料",
        "category": "评优",
        "style": "formal",
        "description": "撰写家庭经济困难学生认定材料",
        "system_prompt": "你是一位认真负责的辅导员。请生成规范的困难生认定申请材料描述。注意保护学生隐私，不涉及具体疾病等敏感细节。",
        "user_prompt_template": """## 困难生认定材料

学生姓名：{student_name}
学号：{student_id}
班级：{class_name}
家庭情况概要：{family_situation}
申请理由：{reason}

请生成一份客观、规范的困难生认定材料描述，注意隐私保护。""",
        "variables": json.dumps(["student_name", "student_id", "class_name", "family_situation", "reason"]),
    },
    {
        "name": "月度工作总结",
        "category": "总结",
        "style": "brief",
        "description": "撰写学工月度工作总结",
        "system_prompt": "你是一位高效的学工办行政人员。请生成简洁、条理清晰的月度工作总结。",
        "user_prompt_template": """## 月度工作总结

月份：{month}
撰写人：{author}
主要工作事项：{tasks}
取得成效：{results}
存在问题：{problems}
下月计划：{next_plan}

请按以下格式生成简结的工作总结：
一、本月工作概述
二、重点事项进展
三、存在问题与改进
四、下月工作计划""",
        "variables": json.dumps(["month", "author", "tasks", "results", "problems", "next_plan"]),
    },
    {
        "name": "学期工作简报",
        "category": "简报",
        "style": "brief",
        "description": "撰写学期学工工作简报",
        "system_prompt": "你是一位高校学工办文秘。请生成正式的学期工作简报，数据清晰、条理分明。",
        "user_prompt_template": """## 学期工作简报

学期：{semester}
部门：{department}
重点工作：{highlights}
数据统计：{statistics}
特色活动：{events}

请生成一份正式的学期工作简报。""",
        "variables": json.dumps(["semester", "department", "highlights", "statistics", "events"]),
    },
    {
        "name": "突发事件情况报告",
        "category": "报告",
        "style": "formal",
        "description": "撰写学生突发事件初步情况报告",
        "system_prompt": "你是一位冷静、专业的高校辅导员。请生成突发事件情况报告。注意：仅描述事实和已采取措施，不做责任认定和处置结论。",
        "user_prompt_template": """## 突发事件情况报告

发生时间：{time}
发生地点：{location}
涉事人员：{persons}
事件经过：{description}
已采取措施：{measures}
当前状态：{status}

请生成客观的情况报告，仅描述事实和已采取措施。""",
        "variables": json.dumps(["time", "location", "persons", "description", "measures", "status"]),
    },
    {
        "name": "通知公告",
        "category": "通知",
        "style": "formal",
        "description": "撰写学工相关通知公告",
        "system_prompt": "你是一位高校行政人员。请生成规范的通知公告，措辞正式、信息完整。",
        "user_prompt_template": """## 通知公告

发布单位：{department}
发布日期：{date}
通知标题：{title}
通知内容要点：{content}

请生成一份格式规范的通知公告。""",
        "variables": json.dumps(["department", "date", "title", "content"]),
    },
    {
        "name": "学生综合评语",
        "category": "评语",
        "style": "soft",
        "description": "为学生撰写期末综合评语",
        "system_prompt": "你是一位关爱学生的辅导员。请生成个性化的学生综合评语，肯定优点、温和指出改进方向。",
        "user_prompt_template": """## 学生综合评语

学生姓名：{student_name}
班级：{class_name}
学年：{academic_year}
学业表现：{academic_performance}
活动参与：{activities}
优点：{strengths}
待改进：{areas_to_improve}

请生成一段150-200字的个性化综合评语。""",
        "variables": json.dumps(["student_name", "class_name", "academic_year", "academic_performance", "activities", "strengths", "areas_to_improve"]),
    },
]


def seed_builtin_templates(db: Session):
    """首次启动时检查并创建内置模板。"""
    count = db.query(Template).filter(Template.is_builtin == True).count()
    if count >= len(BUILTIN_TEMPLATES):
        return
    for tmpl in BUILTIN_TEMPLATES:
        existing = db.query(Template).filter(
            Template.name == tmpl["name"], Template.is_builtin == True
        ).first()
        if not existing:
            db.add(Template(**tmpl, is_builtin=True))
    db.commit()


def get_templates(db: Session, category: str | None = None, style: str | None = None):
    query = db.query(Template)
    if category:
        query = query.filter(Template.category == category)
    if style:
        query = query.filter(Template.style == style)
    return query.order_by(Template.is_builtin.desc(), Template.created_at.desc()).all()


def get_template(db: Session, template_id: int) -> Template | None:
    return db.query(Template).filter(Template.id == template_id).first()


def create_template(db: Session, user_id: int, data: dict) -> Template:
    tmpl = Template(**data, creator_id=user_id)
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


def update_template(db: Session, user_id: int, template_id: int, data: dict) -> Template:
    tmpl = get_template(db, template_id)
    if tmpl is None:
        raise ValueError("模板不存在")
    if tmpl.is_builtin:
        raise ValueError("内置模板不可修改")
    if tmpl.creator_id != user_id:
        raise PermissionError("无权修改他人模板")
    for key, value in data.items():
        if value is not None:
            setattr(tmpl, key, value)
    db.commit()
    db.refresh(tmpl)
    return tmpl


def delete_template(db: Session, user_id: int, template_id: int):
    tmpl = get_template(db, template_id)
    if tmpl is None:
        raise ValueError("模板不存在")
    if tmpl.is_builtin:
        raise ValueError("内置模板不可删除")
    if tmpl.creator_id != user_id:
        raise PermissionError("无权删除他人模板")
    db.delete(tmpl)
    db.commit()