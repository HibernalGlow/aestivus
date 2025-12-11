"""
任务执行API
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, Dict, Set, Any
import asyncio
import uuid
from datetime import datetime

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskExecuteRequest(BaseModel):
    flowId: str
    inputs: Optional[Dict[str, Any]] = None


class TaskStatus(BaseModel):
    id: str
    flowId: str
    status: str  # pending | running | completed | failed | cancelled
    nodeStatuses: Dict[str, dict] = {}
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None
    error: Optional[str] = None


# 简单的内存任务存储
tasks: Dict[str, TaskStatus] = {}


# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.connections:
            self.connections[task_id] = set()
        self.connections[task_id].add(websocket)

    def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.connections:
            self.connections[task_id].discard(websocket)
            if not self.connections[task_id]:
                del self.connections[task_id]

    async def broadcast(self, task_id: str, message: dict):
        if task_id in self.connections:
            dead = []
            for ws in self.connections[task_id]:
                try:
                    await ws.send_json(message)
                except:
                    dead.append(ws)
            for ws in dead:
                self.connections[task_id].discard(ws)


manager = ConnectionManager()


@router.post("/execute")
async def execute_task(request: TaskExecuteRequest):
    """执行流程"""
    task_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    task = TaskStatus(
        id=task_id,
        flowId=request.flowId,
        status="pending",
        startedAt=now
    )
    tasks[task_id] = task
    
    # 异步启动任务执行
    asyncio.create_task(_run_task(task_id, request.flowId, request.inputs or {}))
    
    return {"taskId": task_id}


async def _run_task(task_id: str, flow_id: str, inputs: dict):
    """执行任务的异步函数"""
    task = tasks.get(task_id)
    if not task:
        return
    
    task.status = "running"
    await manager.broadcast(task_id, {
        "type": "task_started",
        "taskId": task_id,
        "data": {"status": "running", "timestamp": datetime.now().isoformat()}
    })
    
    try:
        # TODO: 实际的流程执行逻辑
        # 这里是占位符，后续会实现真正的流程执行
        await asyncio.sleep(1)
        
        await manager.broadcast(task_id, {
            "type": "task_output",
            "taskId": task_id,
            "nodeId": "system",
            "data": {"output": f"流程 {flow_id} 开始执行...", "timestamp": datetime.now().isoformat()}
        })
        
        await asyncio.sleep(2)
        
        task.status = "completed"
        task.completedAt = datetime.now().isoformat()
        
        await manager.broadcast(task_id, {
            "type": "task_completed",
            "taskId": task_id,
            "data": {"status": "completed", "timestamp": datetime.now().isoformat()}
        })
        
    except Exception as e:
        task.status = "failed"
        task.error = str(e)
        task.completedAt = datetime.now().isoformat()
        
        await manager.broadcast(task_id, {
            "type": "task_error",
            "taskId": task_id,
            "data": {"error": str(e), "timestamp": datetime.now().isoformat()}
        })


@router.get("/{task_id}", response_model=TaskStatus)
async def get_task(task_id: str):
    """获取任务状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return tasks[task_id]


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task = tasks[task_id]
    if task.status == "running":
        task.status = "cancelled"
        task.completedAt = datetime.now().isoformat()
        
        await manager.broadcast(task_id, {
            "type": "task_cancelled",
            "taskId": task_id,
            "data": {"status": "cancelled", "timestamp": datetime.now().isoformat()}
        })
    
    return {"success": True}


@router.get("/history")
async def get_task_history(limit: int = 20):
    """获取执行历史"""
    sorted_tasks = sorted(
        tasks.values(),
        key=lambda t: t.startedAt or "",
        reverse=True
    )
    return sorted_tasks[:limit]


@router.websocket("/ws/{task_id}")
async def websocket_task(websocket: WebSocket, task_id: str):
    """任务WebSocket连接"""
    await manager.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
