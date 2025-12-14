"""
WebSocket API
提供实时日志推送和执行状态更新
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter(tags=["websocket"])


# ============ 连接管理 ============

class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # 活跃连接: {task_id: set of websockets}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # 全局连接（接收所有消息）
        self.global_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, task_id: Optional[str] = None):
        """
        接受 WebSocket 连接
        
        Args:
            websocket: WebSocket 连接
            task_id: 任务 ID（可选，如果提供则只接收该任务的消息）
        """
        await websocket.accept()
        
        if task_id:
            if task_id not in self.active_connections:
                self.active_connections[task_id] = set()
            self.active_connections[task_id].add(websocket)
        else:
            self.global_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket, task_id: Optional[str] = None):
        """
        断开 WebSocket 连接
        
        Args:
            websocket: WebSocket 连接
            task_id: 任务 ID
        """
        if task_id and task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        else:
            self.global_connections.discard(websocket)
    
    async def send_to_task(self, task_id: str, message: dict):
        """
        向特定任务的所有连接发送消息
        
        Args:
            task_id: 任务 ID
            message: 消息内容
        """
        connections = self.active_connections.get(task_id, set()) | self.global_connections
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass  # 忽略发送失败的连接
    
    async def broadcast(self, message: dict):
        """
        向所有连接广播消息
        
        Args:
            message: 消息内容
        """
        all_connections = self.global_connections.copy()
        for connections in self.active_connections.values():
            all_connections |= connections
        
        for connection in all_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


# 全局连接管理器实例
manager = ConnectionManager()


# ============ 消息类型 ============

class LogMessage(BaseModel):
    """日志消息"""
    type: str = "log"
    task_id: str
    node_id: Optional[str] = None
    level: str = "info"  # info, warn, error
    message: str
    timestamp: str = ""
    
    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now().isoformat()
        super().__init__(**data)


class ProgressMessage(BaseModel):
    """进度消息"""
    type: str = "progress"
    task_id: str
    node_id: Optional[str] = None
    progress: int  # 0-100
    message: str
    timestamp: str = ""
    
    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now().isoformat()
        super().__init__(**data)


class StatusMessage(BaseModel):
    """状态消息"""
    type: str = "status"
    task_id: str
    node_id: Optional[str] = None
    status: str  # idle, running, completed, error
    message: str = ""
    timestamp: str = ""
    
    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now().isoformat()
        super().__init__(**data)


# ============ 辅助函数 ============

async def send_log(task_id: str, message: str, node_id: str = None, level: str = "info"):
    """发送日志消息"""
    log = LogMessage(
        task_id=task_id,
        node_id=node_id,
        level=level,
        message=message
    )
    await manager.send_to_task(task_id, log.model_dump())


async def send_progress(task_id: str, progress: int, message: str, node_id: str = None):
    """发送进度消息"""
    msg = ProgressMessage(
        task_id=task_id,
        node_id=node_id,
        progress=progress,
        message=message
    )
    await manager.send_to_task(task_id, msg.model_dump())


async def send_status(task_id: str, status: str, message: str = "", node_id: str = None):
    """发送状态消息"""
    msg = StatusMessage(
        task_id=task_id,
        node_id=node_id,
        status=status,
        message=message
    )
    await manager.send_to_task(task_id, msg.model_dump())


# ============ WebSocket 端点 ============

@router.websocket("/ws/tasks/{task_id}")
async def websocket_task(websocket: WebSocket, task_id: str):
    """
    任务 WebSocket 端点
    
    连接后接收指定任务的实时日志和状态更新。
    
    Args:
        websocket: WebSocket 连接
        task_id: 任务 ID
    """
    await manager.connect(websocket, task_id)
    
    try:
        # 发送连接成功消息
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "message": f"已连接到任务 {task_id}"
        })
        
        # 保持连接，接收客户端消息
        while True:
            try:
                data = await websocket.receive_text()
                # 可以处理客户端发送的命令
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                pass
                
    finally:
        manager.disconnect(websocket, task_id)


@router.websocket("/ws/system")
async def websocket_system(websocket: WebSocket):
    """
    系统 WebSocket 端点
    
    连接后接收所有任务的实时日志和状态更新。
    """
    await manager.connect(websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "已连接到系统 WebSocket"
        })
        
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                pass
                
    finally:
        manager.disconnect(websocket)


# 导出
__all__ = [
    "router",
    "manager",
    "send_log",
    "send_progress", 
    "send_status",
    "LogMessage",
    "ProgressMessage",
    "StatusMessage"
]
