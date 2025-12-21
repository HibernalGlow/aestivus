"""
存储服务 API - 使用 SQLModel + SQLite 进行数据持久化
替代前端 localStorage，解决配额限制问题
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional, List, Any
import json
import time

from db.database import get_session
from db.models import NodeLayout, LayoutPreset, DefaultPreset

router = APIRouter(prefix="/storage", tags=["storage"])


# ========== 请求/响应模型 ==========

class LayoutConfigRequest(BaseModel):
    """布局配置请求"""
    config: dict  # 完整的 NodeConfig 对象


class PresetCreateRequest(BaseModel):
    """创建预设请求"""
    id: str
    name: str
    node_type: str
    layout: List[dict]  # GridItem[]
    tab_groups: Optional[List[dict]] = None  # TabGroup[]
    is_builtin: bool = False


class PresetUpdateRequest(BaseModel):
    """更新预设请求"""
    name: Optional[str] = None
    layout: Optional[List[dict]] = None
    tab_groups: Optional[List[dict]] = None


class DefaultPresetRequest(BaseModel):
    """默认预设配置请求"""
    fullscreen_preset_id: Optional[str] = None
    normal_preset_id: Optional[str] = None


# ========== Layouts API ==========

@router.get("/layouts")
def list_layouts(session: Session = Depends(get_session)) -> List[str]:
    """
    列出所有已保存的布局 node_type
    
    Returns:
        node_type 列表
    """
    layouts = session.exec(select(NodeLayout)).all()
    return [layout.node_type for layout in layouts]


@router.get("/layouts/{node_type}")
def get_layout(node_type: str, session: Session = Depends(get_session)) -> Optional[dict]:
    """
    获取指定节点类型的布局配置
    
    Args:
        node_type: 节点类型，如 "trename", "repacku"
    
    Returns:
        NodeConfig 对象，不存在则返回 null
    """
    layout = session.get(NodeLayout, node_type)
    if not layout:
        return None
    return json.loads(layout.config)


@router.put("/layouts/{node_type}")
def set_layout(
    node_type: str, 
    request: LayoutConfigRequest, 
    session: Session = Depends(get_session)
) -> dict:
    """
    保存或更新布局配置（upsert）
    
    Args:
        node_type: 节点类型
        request: 包含 config 的请求体
    
    Returns:
        {"success": True}
    """
    existing = session.get(NodeLayout, node_type)
    config_json = json.dumps(request.config, ensure_ascii=False)
    
    if existing:
        existing.config = config_json
        existing.updated_at = time.time() * 1000
        session.add(existing)
    else:
        layout = NodeLayout(
            node_type=node_type,
            config=config_json,
            updated_at=time.time() * 1000
        )
        session.add(layout)
    
    session.commit()
    return {"success": True}


@router.delete("/layouts/{node_type}")
def delete_layout(node_type: str, session: Session = Depends(get_session)) -> dict:
    """
    删除布局配置
    
    Args:
        node_type: 节点类型
    
    Returns:
        {"success": True}（幂等操作，不存在也返回成功）
    """
    layout = session.get(NodeLayout, node_type)
    if layout:
        session.delete(layout)
        session.commit()
    return {"success": True}


# ========== Presets API ==========

@router.get("/presets")
def list_presets(
    node_type: Optional[str] = Query(None, description="按节点类型过滤"),
    session: Session = Depends(get_session)
) -> List[dict]:
    """
    列出所有预设
    
    Args:
        node_type: 可选，按节点类型过滤
    
    Returns:
        预设列表
    """
    if node_type:
        statement = select(LayoutPreset).where(LayoutPreset.node_type == node_type)
    else:
        statement = select(LayoutPreset)
    
    presets = session.exec(statement).all()
    
    result = []
    for preset in presets:
        item = {
            "id": preset.id,
            "name": preset.name,
            "nodeType": preset.node_type,
            "layout": json.loads(preset.layout),
            "createdAt": preset.created_at,
            "isBuiltin": preset.is_builtin,
        }
        if preset.tab_groups:
            item["tabGroups"] = json.loads(preset.tab_groups)
        result.append(item)
    
    return result


@router.post("/presets")
def create_preset(
    request: PresetCreateRequest, 
    session: Session = Depends(get_session)
) -> dict:
    """
    创建新预设
    
    Args:
        request: 预设数据
    
    Returns:
        创建的预设
    """
    # 检查 ID 是否已存在
    existing = session.get(LayoutPreset, request.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"预设 ID 已存在: {request.id}")
    
    preset = LayoutPreset(
        id=request.id,
        name=request.name,
        node_type=request.node_type,
        layout=json.dumps(request.layout, ensure_ascii=False),
        tab_groups=json.dumps(request.tab_groups, ensure_ascii=False) if request.tab_groups else None,
        created_at=time.time() * 1000,
        is_builtin=request.is_builtin,
    )
    session.add(preset)
    session.commit()
    session.refresh(preset)
    
    result = {
        "id": preset.id,
        "name": preset.name,
        "nodeType": preset.node_type,
        "layout": json.loads(preset.layout),
        "createdAt": preset.created_at,
        "isBuiltin": preset.is_builtin,
    }
    if preset.tab_groups:
        result["tabGroups"] = json.loads(preset.tab_groups)
    
    return result


@router.put("/presets/{preset_id}")
def update_preset(
    preset_id: str,
    request: PresetUpdateRequest,
    session: Session = Depends(get_session)
) -> dict:
    """
    更新预设
    
    Args:
        preset_id: 预设 ID
        request: 要更新的字段
    
    Returns:
        更新后的预设
    """
    preset = session.get(LayoutPreset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail=f"预设不存在: {preset_id}")
    
    if request.name is not None:
        preset.name = request.name
    if request.layout is not None:
        preset.layout = json.dumps(request.layout, ensure_ascii=False)
    if request.tab_groups is not None:
        preset.tab_groups = json.dumps(request.tab_groups, ensure_ascii=False)
    
    session.add(preset)
    session.commit()
    session.refresh(preset)
    
    result = {
        "id": preset.id,
        "name": preset.name,
        "nodeType": preset.node_type,
        "layout": json.loads(preset.layout),
        "createdAt": preset.created_at,
        "isBuiltin": preset.is_builtin,
    }
    if preset.tab_groups:
        result["tabGroups"] = json.loads(preset.tab_groups)
    
    return result


@router.delete("/presets/{preset_id}")
def delete_preset(preset_id: str, session: Session = Depends(get_session)) -> dict:
    """
    删除预设
    
    Args:
        preset_id: 预设 ID
    
    Returns:
        {"success": True}
    """
    preset = session.get(LayoutPreset, preset_id)
    if preset:
        session.delete(preset)
        session.commit()
    return {"success": True}


# ========== Defaults API ==========

@router.get("/defaults/{node_type}")
def get_defaults(node_type: str, session: Session = Depends(get_session)) -> Optional[dict]:
    """
    获取默认预设配置
    
    Args:
        node_type: 节点类型
    
    Returns:
        默认预设配置，不存在则返回 null
    """
    defaults = session.get(DefaultPreset, node_type)
    if not defaults:
        return None
    
    return {
        "nodeType": defaults.node_type,
        "fullscreenPresetId": defaults.fullscreen_preset_id,
        "normalPresetId": defaults.normal_preset_id,
    }


@router.put("/defaults/{node_type}")
def set_defaults(
    node_type: str,
    request: DefaultPresetRequest,
    session: Session = Depends(get_session)
) -> dict:
    """
    设置默认预设配置
    
    Args:
        node_type: 节点类型
        request: 默认预设配置
    
    Returns:
        {"success": True}
    """
    existing = session.get(DefaultPreset, node_type)
    
    if existing:
        existing.fullscreen_preset_id = request.fullscreen_preset_id
        existing.normal_preset_id = request.normal_preset_id
        session.add(existing)
    else:
        defaults = DefaultPreset(
            node_type=node_type,
            fullscreen_preset_id=request.fullscreen_preset_id,
            normal_preset_id=request.normal_preset_id,
        )
        session.add(defaults)
    
    session.commit()
    return {"success": True}


# ========== 批量操作 API（用于迁移） ==========

class BulkLayoutsRequest(BaseModel):
    """批量布局请求"""
    layouts: dict  # {node_type: config}


class BulkPresetsRequest(BaseModel):
    """批量预设请求"""
    presets: List[PresetCreateRequest]


@router.post("/bulk/layouts")
def bulk_set_layouts(
    request: BulkLayoutsRequest,
    session: Session = Depends(get_session)
) -> dict:
    """
    批量保存布局配置（用于迁移）
    
    Args:
        request: {layouts: {node_type: config}}
    
    Returns:
        {"success": True, "count": N}
    """
    count = 0
    for node_type, config in request.layouts.items():
        existing = session.get(NodeLayout, node_type)
        config_json = json.dumps(config, ensure_ascii=False)
        
        if existing:
            existing.config = config_json
            existing.updated_at = time.time() * 1000
            session.add(existing)
        else:
            layout = NodeLayout(
                node_type=node_type,
                config=config_json,
                updated_at=time.time() * 1000
            )
            session.add(layout)
        count += 1
    
    session.commit()
    return {"success": True, "count": count}


@router.post("/bulk/presets")
def bulk_create_presets(
    request: BulkPresetsRequest,
    session: Session = Depends(get_session)
) -> dict:
    """
    批量创建预设（用于迁移）
    
    Args:
        request: {presets: [...]}
    
    Returns:
        {"success": True, "count": N}
    """
    count = 0
    for preset_data in request.presets:
        # 跳过已存在的
        existing = session.get(LayoutPreset, preset_data.id)
        if existing:
            continue
        
        preset = LayoutPreset(
            id=preset_data.id,
            name=preset_data.name,
            node_type=preset_data.node_type,
            layout=json.dumps(preset_data.layout, ensure_ascii=False),
            tab_groups=json.dumps(preset_data.tab_groups, ensure_ascii=False) if preset_data.tab_groups else None,
            created_at=time.time() * 1000,
            is_builtin=preset_data.is_builtin,
        )
        session.add(preset)
        count += 1
    
    session.commit()
    return {"success": True, "count": count}
