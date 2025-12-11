"""
流程管理API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import json
import uuid
from datetime import datetime

router = APIRouter(prefix="/flows", tags=["flows"])

FLOWS_DIR = Path("config/flows")
FLOWS_DIR.mkdir(parents=True, exist_ok=True)


class FlowNode(BaseModel):
    id: str
    type: str
    position: dict
    data: dict


class FlowEdge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None
    animated: Optional[bool] = False


class Flow(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    nodes: List[FlowNode] = []
    edges: List[FlowEdge] = []
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class FlowCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    nodes: List[FlowNode] = []
    edges: List[FlowEdge] = []


class FlowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[FlowNode]] = None
    edges: Optional[List[FlowEdge]] = None


def _get_flow_path(flow_id: str) -> Path:
    return FLOWS_DIR / f"{flow_id}.json"


def _load_flow(flow_id: str) -> Flow:
    path = _get_flow_path(flow_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Flow {flow_id} not found")
    with open(path, "r", encoding="utf-8") as f:
        return Flow(**json.load(f))


def _save_flow(flow: Flow) -> None:
    path = _get_flow_path(flow.id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(flow.model_dump(), f, ensure_ascii=False, indent=2)


@router.get("/", response_model=List[Flow])
async def list_flows():
    """获取所有流程"""
    flows = []
    for path in FLOWS_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                flows.append(Flow(**json.load(f)))
        except Exception as e:
            print(f"Error loading flow {path}: {e}")
    return sorted(flows, key=lambda f: f.updatedAt or "", reverse=True)


@router.post("/", response_model=Flow)
async def create_flow(data: FlowCreate):
    """创建新流程"""
    now = datetime.now().isoformat()
    flow = Flow(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        nodes=data.nodes,
        edges=data.edges,
        createdAt=now,
        updatedAt=now
    )
    _save_flow(flow)
    return flow


@router.get("/{flow_id}", response_model=Flow)
async def get_flow(flow_id: str):
    """获取流程详情"""
    return _load_flow(flow_id)


@router.put("/{flow_id}", response_model=Flow)
async def update_flow(flow_id: str, data: FlowUpdate):
    """更新流程"""
    flow = _load_flow(flow_id)
    
    if data.name is not None:
        flow.name = data.name
    if data.description is not None:
        flow.description = data.description
    if data.nodes is not None:
        flow.nodes = data.nodes
    if data.edges is not None:
        flow.edges = data.edges
    
    flow.updatedAt = datetime.now().isoformat()
    _save_flow(flow)
    return flow


@router.delete("/{flow_id}")
async def delete_flow(flow_id: str):
    """删除流程"""
    path = _get_flow_path(flow_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Flow {flow_id} not found")
    path.unlink()
    return {"success": True}


@router.post("/{flow_id}/duplicate", response_model=Flow)
async def duplicate_flow(flow_id: str):
    """复制流程"""
    original = _load_flow(flow_id)
    now = datetime.now().isoformat()
    
    new_flow = Flow(
        id=str(uuid.uuid4()),
        name=f"{original.name} (副本)",
        description=original.description,
        nodes=original.nodes,
        edges=original.edges,
        createdAt=now,
        updatedAt=now
    )
    _save_flow(new_flow)
    return new_flow
