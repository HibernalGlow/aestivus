"""
SQLModel 数据模型定义
用于存储节点布局配置、布局预设和默认预设设置
"""

from sqlmodel import Field, SQLModel
from typing import Optional
import time


class NodeLayout(SQLModel, table=True):
    """
    节点布局配置
    存储每个节点类型的完整布局配置（gridLayout, sizeOverrides, tabGroups）
    """
    __tablename__ = "node_layouts"
    
    # 节点类型作为主键，如 "trename", "repacku", "owithu"
    node_type: str = Field(primary_key=True)
    # JSON 字符串，存储完整的 NodeConfig 对象
    config: str
    # 更新时间戳（毫秒）
    updated_at: float = Field(default_factory=lambda: time.time() * 1000)


class LayoutPreset(SQLModel, table=True):
    """
    布局预设
    用户保存的自定义布局配置
    """
    __tablename__ = "layout_presets"
    
    # 预设 ID，如 "trename-1734567890123"
    id: str = Field(primary_key=True)
    # 预设名称
    name: str
    # 适用的节点类型
    node_type: str = Field(index=True)
    # JSON 字符串，存储 GridItem[] 布局
    layout: str
    # JSON 字符串，存储 TabGroup[]，可选
    tab_groups: Optional[str] = None
    # 创建时间戳（毫秒）
    created_at: float = Field(default_factory=lambda: time.time() * 1000)
    # 是否为内置预设
    is_builtin: bool = False


class DefaultPreset(SQLModel, table=True):
    """
    默认预设配置
    存储每个节点类型在不同模式下的默认预设 ID
    """
    __tablename__ = "default_presets"
    
    # 节点类型作为主键
    node_type: str = Field(primary_key=True)
    # 全屏模式默认预设 ID
    fullscreen_preset_id: Optional[str] = None
    # 普通模式默认预设 ID
    normal_preset_id: Optional[str] = None
