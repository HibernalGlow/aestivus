"""
执行 API
提供节点和流程的执行功能，支持 WebSocket 实时日志推送
"""

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import asyncio
from collections import defaultdict

from adapters import get_adapter, safe_execute, AdapterOutput
from api.websocket import send_log, send_progress, send_status

router = APIRouter(prefix="/execute", tags=["execution"])


# ============ 请求/响应模型 ============

class NodeExecuteRequest(BaseModel):
    """单节点执行请求"""
    node_type: str = Field(..., description="节点类型名称")
    config: Dict[str, Any] = Field(default_factory=dict, description="节点配置参数")
    task_id: Optional[str] = Field(default=None, description="任务 ID（用于 WebSocket 日志推送）")
    node_id: Optional[str] = Field(default=None, description="节点 ID（用于 WebSocket 日志推送）")


class NodeExecuteResponse(BaseModel):
    """节点执行响应"""
    success: bool
    message: str
    data: Any = None
    stats: Dict[str, int] = Field(default_factory=dict)
    output_path: Optional[str] = None
    logs: List[str] = Field(default_factory=list, description="执行日志")


class FlowNode(BaseModel):
    """流程中的节点定义"""
    id: str = Field(..., description="节点唯一 ID")
    type: str = Field(..., description="节点类型")
    config: Dict[str, Any] = Field(default_factory=dict, description="节点配置")


class FlowEdge(BaseModel):
    """流程中的边定义"""
    source: str = Field(..., description="源节点 ID")
    target: str = Field(..., description="目标节点 ID")


class FlowExecuteRequest(BaseModel):
    """流程执行请求"""
    nodes: List[FlowNode] = Field(..., description="节点列表")
    edges: List[FlowEdge] = Field(default_factory=list, description="边列表")
    task_id: Optional[str] = Field(default=None, description="任务 ID（用于 WebSocket 日志推送）")


class FlowExecuteResponse(BaseModel):
    """流程执行响应"""
    success: bool
    message: str
    node_results: Dict[str, NodeExecuteResponse] = Field(default_factory=dict)
    execution_order: List[str] = Field(default_factory=list)


# ============ 辅助函数 ============

def topological_sort(nodes: List[FlowNode], edges: List[FlowEdge]) -> List[str]:
    """
    对节点进行拓扑排序
    
    Args:
        nodes: 节点列表
        edges: 边列表
        
    Returns:
        按拓扑顺序排列的节点 ID 列表
        
    Raises:
        ValueError: 如果存在循环依赖
    """
    # 构建邻接表和入度表
    node_ids = {node.id for node in nodes}
    graph = defaultdict(list)
    in_degree = {node_id: 0 for node_id in node_ids}
    
    for edge in edges:
        if edge.source in node_ids and edge.target in node_ids:
            graph[edge.source].append(edge.target)
            in_degree[edge.target] += 1
    
    # Kahn 算法
    queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
    result = []
    
    while queue:
        node_id = queue.pop(0)
        result.append(node_id)
        
        for neighbor in graph[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    if len(result) != len(node_ids):
        raise ValueError("流程中存在循环依赖")
    
    return result


def get_upstream_output(
    node_id: str, 
    edges: List[FlowEdge], 
    node_results: Dict[str, NodeExecuteResponse]
) -> Optional[str]:
    """
    获取上游节点的输出路径
    
    Args:
        node_id: 当前节点 ID
        edges: 边列表
        node_results: 已执行节点的结果
        
    Returns:
        上游节点的输出路径，如果没有上游则返回 None
    """
    for edge in edges:
        if edge.target == node_id and edge.source in node_results:
            upstream_result = node_results[edge.source]
            if upstream_result.success and upstream_result.output_path:
                return upstream_result.output_path
    return None


# ============ API 端点 ============

@router.post("/node", response_model=NodeExecuteResponse)
async def execute_node(request: NodeExecuteRequest):
    """
    执行单个节点
    
    Args:
        request: 节点执行请求，包含节点类型和配置
        
    Returns:
        执行结果
    """
    # 生成任务 ID（如果未提供）
    task_id = request.task_id or str(uuid.uuid4())
    node_id = request.node_id
    
    # 收集日志
    collected_logs: List[str] = []
    
    try:
        # 获取适配器
        adapter = get_adapter(request.node_type)
        
        # 构建输入数据
        input_class = adapter.input_schema
        input_data = input_class(**request.config)
        
        # 发送开始状态
        await send_status(task_id, "running", f"开始执行 {adapter.display_name}", node_id)
        
        # 创建进度和日志回调
        async def on_progress(progress: int, message: str):
            await send_progress(task_id, progress, message, node_id)
        
        async def on_log(message: str):
            collected_logs.append(message)
            await send_log(task_id, message, node_id)
        
        # 获取当前事件循环，用于从子线程安全调度
        loop = asyncio.get_running_loop()
        
        # 包装同步回调为异步（线程安全）
        def sync_on_progress(progress: int, message: str):
            asyncio.run_coroutine_threadsafe(on_progress(progress, message), loop)
        
        def sync_on_log(message: str):
            collected_logs.append(message)
            asyncio.run_coroutine_threadsafe(on_log(message), loop)
        
        # 执行（带回调）
        result = await safe_execute(
            adapter, 
            input_data,
            on_progress=sync_on_progress,
            on_log=sync_on_log
        )
        
        # 发送完成状态
        status = "completed" if result.success else "error"
        await send_status(task_id, status, result.message, node_id)
        
        return NodeExecuteResponse(
            success=result.success,
            message=result.message,
            data=result.data,
            stats=result.stats,
            output_path=result.output_path,
            logs=collected_logs
        )
        
    except ValueError as e:
        await send_status(task_id, "error", str(e), node_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_msg = f"执行失败: {type(e).__name__}: {str(e)}"
        collected_logs.append(f"❌ {error_msg}")
        await send_status(task_id, "error", error_msg, node_id)
        return NodeExecuteResponse(
            success=False,
            message=error_msg,
            logs=collected_logs
        )


@router.post("/flow", response_model=FlowExecuteResponse)
async def execute_flow(request: FlowExecuteRequest):
    """
    执行整个流程
    
    按拓扑顺序依次执行所有节点，上游节点的输出作为下游节点的输入。
    支持 WebSocket 实时日志推送。
    
    Args:
        request: 流程执行请求，包含节点和边定义
        
    Returns:
        执行结果，包含每个节点的执行状态
    """
    # 生成任务 ID（如果未提供）
    task_id = request.task_id or str(uuid.uuid4())
    
    if not request.nodes:
        return FlowExecuteResponse(
            success=True,
            message="流程为空，无需执行"
        )
    
    try:
        # 拓扑排序
        execution_order = topological_sort(request.nodes, request.edges)
    except ValueError as e:
        await send_status(task_id, "error", str(e))
        return FlowExecuteResponse(
            success=False,
            message=str(e)
        )
    
    # 发送流程开始状态
    await send_status(task_id, "running", f"开始执行流程，共 {len(request.nodes)} 个节点")
    await send_log(task_id, f"执行顺序: {' → '.join(execution_order)}")
    
    # 构建节点映射
    node_map = {node.id: node for node in request.nodes}
    node_results: Dict[str, NodeExecuteResponse] = {}
    
    # 按顺序执行
    all_success = True
    for idx, node_id in enumerate(execution_order):
        node = node_map[node_id]
        
        # 发送节点开始状态
        await send_status(task_id, "running", f"执行节点 {idx + 1}/{len(execution_order)}", node_id)
        
        try:
            # 获取适配器
            adapter = get_adapter(node.type)
            
            # 构建配置，如果有上游输出则使用
            config = dict(node.config)
            upstream_output = get_upstream_output(node_id, request.edges, node_results)
            if upstream_output and 'path' not in config:
                config['path'] = upstream_output
                await send_log(task_id, f"使用上游输出路径: {upstream_output}", node_id)
            
            # 构建输入数据
            input_class = adapter.input_schema
            input_data = input_class(**config)
            
            # 创建进度和日志回调（线程安全）
            loop = asyncio.get_running_loop()
            def sync_on_progress(progress: int, message: str):
                asyncio.run_coroutine_threadsafe(send_progress(task_id, progress, message, node_id), loop)
            
            def sync_on_log(message: str):
                asyncio.run_coroutine_threadsafe(send_log(task_id, message, node_id), loop)
            
            # 执行（带回调）
            result = await safe_execute(
                adapter, 
                input_data,
                on_progress=sync_on_progress,
                on_log=sync_on_log
            )
            
            node_results[node_id] = NodeExecuteResponse(
                success=result.success,
                message=result.message,
                data=result.data,
                stats=result.stats,
                output_path=result.output_path
            )
            
            # 发送节点完成状态
            status = "completed" if result.success else "error"
            await send_status(task_id, status, result.message, node_id)
            
            if not result.success:
                all_success = False
                
        except Exception as e:
            error_msg = f"执行失败: {type(e).__name__}: {str(e)}"
            node_results[node_id] = NodeExecuteResponse(
                success=False,
                message=error_msg
            )
            await send_status(task_id, "error", error_msg, node_id)
            all_success = False
    
    # 发送流程完成状态
    final_status = "completed" if all_success else "error"
    final_message = "流程执行完成" if all_success else "部分节点执行失败"
    await send_status(task_id, final_status, final_message)
    
    return FlowExecuteResponse(
        success=all_success,
        message=final_message,
        node_results=node_results,
        execution_order=execution_order
    )
