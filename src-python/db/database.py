"""
数据库引擎和会话管理
使用 SQLite 作为嵌入式数据库
"""

from sqlmodel import create_engine, SQLModel, Session
from pathlib import Path
from typing import Generator
import os


def get_db_path() -> Path:
    """
    获取数据库文件路径
    Windows: %APPDATA%/aestivus/data.db
    Linux/Mac: ~/.local/share/aestivus/data.db
    """
    if os.name == "nt":  # Windows
        app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
        db_dir = Path(app_data) / "aestivus"
    else:  # Linux/Mac
        db_dir = Path.home() / ".local" / "share" / "aestivus"
    
    # 确保目录存在
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "data.db"


# 数据库文件路径
DB_PATH = get_db_path()

# 创建数据库引擎
# check_same_thread=False 允许多线程访问（FastAPI 需要）
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False}
)


def init_db() -> None:
    """
    初始化数据库
    创建所有定义的表（如果不存在）
    """
    # 导入模型以确保它们被注册
    from . import models  # noqa: F401
    
    SQLModel.metadata.create_all(engine)
    print(f"[db] 数据库已初始化: {DB_PATH}")


def get_session() -> Generator[Session, None, None]:
    """
    获取数据库会话（用于 FastAPI 依赖注入）
    
    Usage:
        @router.get("/items")
        def get_items(session: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        yield session
