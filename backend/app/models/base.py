"""数据库基类和会话工厂。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db():
    """创建所有表。首次启动调用，已有表则跳过。"""
    Base.metadata.create_all(bind=engine)
    _run_sqlite_migrations()


# SQLite 轻量迁移表：表名 -> {新增列名: 列 DDL}
# create_all 只建新表不补旧表的列，这里为历史库补列。
_SQLITE_MIGRATIONS = {
    "documents": {
        "category": "VARCHAR(30) NOT NULL DEFAULT '综合'",
    },
}


def _run_sqlite_migrations():
    if "sqlite" not in settings.database_url:
        return
    with engine.begin() as conn:
        for table, columns in _SQLITE_MIGRATIONS.items():
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            for col, ddl in columns.items():
                if col not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")