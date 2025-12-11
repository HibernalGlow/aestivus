# AestivalFlow 实施指南

> **版本**: 1.0.0  
> **创建日期**: 2025-12-12

---

## 一、环境准备

### 1.1 前置条件

```bash
# Node.js 18+
node --version  # v18.x 或更高

# Yarn
npm install -g yarn
yarn --version

# Python 3.8+
python --version

# Rust (Tauri需要)
rustc --version

# 确认Python工具可用
repacku --version
samea --version
crashu --version
migratef --version
```

### 1.2 项目初始化

```bash
cd d:\1VSCODE\Projects\AestivalFlow

# 清理pnpm (迁移到yarn)
rm pnpm-lock.yaml

# 使用yarn安装依赖
yarn install

# 安装新依赖
yarn add @xyflow/svelte

# 创建Python虚拟环境
python -m venv .venv
.venv\Scripts\activate
pip install -r src-python/requirements.txt
```

---

## 二、目录结构创建

### 2.1 前端目录

```bash
# 创建前端模块目录
mkdir -p src/lib/components/flow
mkdir -p src/lib/components/nodes
mkdir -p src/lib/components/execution
mkdir -p src/lib/components/input
mkdir -p src/lib/stores
mkdir -p src/lib/services
mkdir -p src/lib/types
mkdir -p src/routes/flow/[id]
```

### 2.2 后端目录

```bash
# 创建后端模块目录
mkdir -p src-python/core
mkdir -p src-python/adapters/file_tools
mkdir -p src-python/adapters/video_tools
mkdir -p src-python/adapters/other_tools
mkdir -p src-python/models
mkdir -p src-python/storage
```

---

## 三、Phase 1 实施步骤

### 3.1 Step 1: SvelteFlow基础集成

#### 3.1.1 安装依赖

```bash
yarn add @xyflow/svelte
```

#### 3.1.2 创建FlowCanvas组件

```svelte
<!-- src/lib/components/flow/FlowCanvas.svelte -->
<script lang="ts">
  import {
    SvelteFlow,
    Background,
    Controls,
    MiniMap,
    type Node,
    type Edge
  } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css';
  
  let nodes: Node[] = $state([
    {
      id: '1',
      type: 'input',
      position: { x: 0, y: 0 },
      data: { label: '输入' }
    }
  ]);
  
  let edges: Edge[] = $state([]);
</script>

<div class="h-full w-full">
  <SvelteFlow
    {nodes}
    {edges}
    fitView
  >
    <Background />
    <Controls />
    <MiniMap />
  </SvelteFlow>
</div>

<style>
  :global(.svelte-flow) {
    background: #f8fafc;
  }
</style>
```

#### 3.1.3 创建流程编辑页面

```svelte
<!-- src/routes/flow/[id]/+page.svelte -->
<script lang="ts">
  import FlowCanvas from '$lib/components/flow/FlowCanvas.svelte';
  import { page } from '$app/stores';
  
  const flowId = $derived($page.params.id);
</script>

<div class="h-screen flex flex-col">
  <header class="h-14 border-b flex items-center px-4">
    <h1 class="text-lg font-semibold">流程编辑器 - {flowId}</h1>
  </header>
  
  <main class="flex-1">
    <FlowCanvas />
  </main>
</div>
```

### 3.2 Step 2: 状态管理

#### 3.2.1 Flow Store

```typescript
// src/lib/stores/flowStore.ts
import { writable, derived } from 'svelte/store';
import type { Node, Edge } from '@xyflow/svelte';

export interface FlowState {
  id: string | null;
  name: string;
  nodes: Node[];
  edges: Edge[];
  isDirty: boolean;
}

function createFlowStore() {
  const { subscribe, set, update } = writable<FlowState>({
    id: null,
    name: '未命名流程',
    nodes: [],
    edges: [],
    isDirty: false
  });
  
  return {
    subscribe,
    
    setFlow(flow: Partial<FlowState>) {
      update(state => ({ ...state, ...flow, isDirty: false }));
    },
    
    addNode(node: Node) {
      update(state => ({
        ...state,
        nodes: [...state.nodes, node],
        isDirty: true
      }));
    },
    
    updateNode(id: string, data: Partial<Node>) {
      update(state => ({
        ...state,
        nodes: state.nodes.map(n => n.id === id ? { ...n, ...data } : n),
        isDirty: true
      }));
    },
    
    removeNode(id: string) {
      update(state => ({
        ...state,
        nodes: state.nodes.filter(n => n.id !== id),
        edges: state.edges.filter(e => e.source !== id && e.target !== id),
        isDirty: true
      }));
    },
    
    addEdge(edge: Edge) {
      update(state => ({
        ...state,
        edges: [...state.edges, edge],
        isDirty: true
      }));
    },
    
    removeEdge(id: string) {
      update(state => ({
        ...state,
        edges: state.edges.filter(e => e.id !== id),
        isDirty: true
      }));
    },
    
    reset() {
      set({
        id: null,
        name: '未命名流程',
        nodes: [],
        edges: [],
        isDirty: false
      });
    }
  };
}

export const flowStore = createFlowStore();
```

#### 3.2.2 Task Store

```typescript
// src/lib/stores/taskStore.ts
import { writable } from 'svelte/store';

export interface LogEntry {
  timestamp: string;
  nodeId: string;
  type: 'stdout' | 'stderr' | 'info';
  content: string;
}

export interface NodeStatus {
  nodeId: string;
  status: 'pending' | 'running' | 'completed' | 'error' | 'skipped';
  progress?: number;
  error?: string;
}

export interface TaskState {
  taskId: string | null;
  status: 'idle' | 'running' | 'completed' | 'failed' | 'cancelled';
  nodeStatuses: Record<string, NodeStatus>;
  logs: LogEntry[];
}

function createTaskStore() {
  const { subscribe, set, update } = writable<TaskState>({
    taskId: null,
    status: 'idle',
    nodeStatuses: {},
    logs: []
  });
  
  return {
    subscribe,
    
    startTask(taskId: string) {
      set({
        taskId,
        status: 'running',
        nodeStatuses: {},
        logs: []
      });
    },
    
    updateNodeStatus(nodeId: string, status: Partial<NodeStatus>) {
      update(state => ({
        ...state,
        nodeStatuses: {
          ...state.nodeStatuses,
          [nodeId]: { ...state.nodeStatuses[nodeId], nodeId, ...status }
        }
      }));
    },
    
    addLog(log: LogEntry) {
      update(state => ({
        ...state,
        logs: [...state.logs, log]
      }));
    },
    
    completeTask(success: boolean) {
      update(state => ({
        ...state,
        status: success ? 'completed' : 'failed'
      }));
    },
    
    reset() {
      set({
        taskId: null,
        status: 'idle',
        nodeStatuses: {},
        logs: []
      });
    }
  };
}

export const taskStore = createTaskStore();
```

### 3.3 Step 3: 自定义节点

#### 3.3.1 节点类型定义

```typescript
// src/lib/types/node.ts
export interface NodeData {
  label: string;
  toolName?: string;
  config?: Record<string, any>;
  status?: 'idle' | 'running' | 'completed' | 'error';
}

export type NodeCategory = 'input' | 'tool' | 'output' | 'control';

export interface NodeDefinition {
  type: string;
  category: NodeCategory;
  label: string;
  description: string;
  icon: string;
  inputs: string[];
  outputs: string[];
  configSchema?: Record<string, any>;
}

// 节点注册表
export const NODE_DEFINITIONS: NodeDefinition[] = [
  // 输入节点
  {
    type: 'clipboard_input',
    category: 'input',
    label: '剪贴板',
    description: '读取系统剪贴板内容',
    icon: 'clipboard',
    inputs: [],
    outputs: ['text']
  },
  {
    type: 'folder_input',
    category: 'input',
    label: '文件夹选择',
    description: '选择文件夹路径',
    icon: 'folder',
    inputs: [],
    outputs: ['path']
  },
  {
    type: 'path_input',
    category: 'input',
    label: '路径输入',
    description: '手动输入或拖拽路径',
    icon: 'type',
    inputs: [],
    outputs: ['path']
  },
  
  // 工具节点
  {
    type: 'tool_repacku',
    category: 'tool',
    label: 'Repacku',
    description: '文件重打包工具',
    icon: 'package',
    inputs: ['path'],
    outputs: ['path']
  },
  {
    type: 'tool_samea',
    category: 'tool',
    label: 'Samea',
    description: '相似文件分析',
    icon: 'search',
    inputs: ['path'],
    outputs: ['path', 'report']
  },
  {
    type: 'tool_crashu',
    category: 'tool',
    label: 'Crashu',
    description: '崩溃文件处理',
    icon: 'alert-triangle',
    inputs: ['path'],
    outputs: ['path']
  },
  {
    type: 'tool_migratef',
    category: 'tool',
    label: 'Migratef',
    description: '文件迁移工具',
    icon: 'move',
    inputs: ['path'],
    outputs: ['path'],
    configSchema: {
      target: { type: 'string', label: '目标路径' },
      mode: { type: 'select', label: '模式', options: ['copy', 'move'] }
    }
  },
  
  // 输出节点
  {
    type: 'log_output',
    category: 'output',
    label: '日志输出',
    description: '输出到日志面板',
    icon: 'terminal',
    inputs: ['any'],
    outputs: []
  }
];
```

#### 3.3.2 工具节点组件

```svelte
<!-- src/lib/components/nodes/ToolNode.svelte -->
<script lang="ts">
  import { Handle, Position } from '@xyflow/svelte';
  import * as Icons from '@lucide/svelte';
  
  interface Props {
    id: string;
    data: {
      label: string;
      toolName: string;
      status: 'idle' | 'running' | 'completed' | 'error';
      progress?: number;
    };
    selected?: boolean;
  }
  
  let { id, data, selected = false }: Props = $props();
  
  const statusStyles = {
    idle: 'border-gray-300 bg-white',
    running: 'border-blue-500 bg-blue-50 animate-pulse',
    completed: 'border-green-500 bg-green-50',
    error: 'border-red-500 bg-red-50'
  };
  
  const statusIcons = {
    idle: Icons.Circle,
    running: Icons.Loader2,
    completed: Icons.CheckCircle2,
    error: Icons.XCircle
  };
  
  const StatusIcon = $derived(statusIcons[data.status]);
</script>

<div
  class="px-4 py-3 rounded-lg border-2 shadow-sm min-w-[160px] transition-all {statusStyles[data.status]}"
  class:ring-2={selected}
  class:ring-blue-400={selected}
>
  <Handle type="target" position={Position.Left} class="!bg-gray-400" />
  
  <div class="flex items-center gap-2">
    <StatusIcon class="w-4 h-4" class:animate-spin={data.status === 'running'} />
    <span class="font-medium text-sm">{data.label}</span>
  </div>
  
  <div class="text-xs text-gray-500 mt-1 flex items-center gap-1">
    <Icons.Terminal class="w-3 h-3" />
    {data.toolName}
  </div>
  
  {#if data.status === 'running' && data.progress !== undefined}
    <div class="mt-2 h-1 bg-gray-200 rounded-full overflow-hidden">
      <div
        class="h-full bg-blue-500 transition-all"
        style="width: {data.progress}%"
      ></div>
    </div>
  {/if}
  
  <Handle type="source" position={Position.Right} class="!bg-gray-400" />
</div>
```

### 3.4 Step 4: API服务层

```typescript
// src/lib/services/api.ts
const API_BASE = 'http://localhost:8009/v1';

export interface Flow {
  id: string;
  name: string;
  nodes: any[];
  edges: any[];
  createdAt: string;
  updatedAt: string;
}

export const api = {
  // 流程管理
  async getFlows(): Promise<Flow[]> {
    const res = await fetch(`${API_BASE}/flows`);
    return res.json();
  },
  
  async getFlow(id: string): Promise<Flow> {
    const res = await fetch(`${API_BASE}/flows/${id}`);
    return res.json();
  },
  
  async createFlow(data: Partial<Flow>): Promise<Flow> {
    const res = await fetch(`${API_BASE}/flows`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return res.json();
  },
  
  async updateFlow(id: string, data: Partial<Flow>): Promise<Flow> {
    const res = await fetch(`${API_BASE}/flows/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return res.json();
  },
  
  async deleteFlow(id: string): Promise<void> {
    await fetch(`${API_BASE}/flows/${id}`, { method: 'DELETE' });
  },
  
  // 任务执行
  async executeFlow(flowId: string, inputs?: Record<string, any>): Promise<{ taskId: string }> {
    const res = await fetch(`${API_BASE}/tasks/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ flowId, inputs })
    });
    return res.json();
  },
  
  async cancelTask(taskId: string): Promise<void> {
    await fetch(`${API_BASE}/tasks/${taskId}/cancel`, { method: 'POST' });
  },
  
  // 工具列表
  async getTools(): Promise<any[]> {
    const res = await fetch(`${API_BASE}/tools`);
    return res.json();
  },
  
  // 系统功能
  async readClipboard(): Promise<string> {
    const res = await fetch(`${API_BASE}/system/clipboard`);
    const data = await res.json();
    return data.content;
  }
};
```

---

## 四、Phase 2 后端实施

### 4.1 适配器基类实现

```python
# src-python/adapters/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, Awaitable
from pydantic import BaseModel
import asyncio

class ToolInput(BaseModel):
    """工具输入基类"""
    class Config:
        extra = "allow"

class ToolOutput(BaseModel):
    """工具输出"""
    success: bool
    message: str
    data: Any = None
    error: Optional[str] = None

class BaseAdapter(ABC):
    """工具适配器基类"""
    
    name: str = ""
    display_name: str = ""
    description: str = ""
    category: str = "other"
    
    @property
    @abstractmethod
    def input_schema(self) -> type:
        """返回输入Schema类"""
        pass
    
    @abstractmethod
    async def execute(
        self,
        input_data: Dict[str, Any],
        on_progress: Optional[Callable[[int], Awaitable[None]]] = None,
        on_output: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> ToolOutput:
        """执行工具"""
        pass
    
    def validate_input(self, data: Dict) -> bool:
        """验证输入"""
        try:
            self.input_schema(**data)
            return True
        except Exception:
            return False
    
    def get_schema(self) -> Dict:
        """获取JSON Schema"""
        return self.input_schema.model_json_schema()
    
    async def _run_subprocess(
        self,
        cmd: list[str],
        on_output: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> tuple[int, str, str]:
        """运行子进程并捕获输出"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout_lines = []
        stderr_lines = []
        
        async def read_stream(stream, lines, is_stderr=False):
            async for line in stream:
                text = line.decode('utf-8', errors='replace').rstrip()
                lines.append(text)
                if on_output:
                    await on_output(text)
        
        await asyncio.gather(
            read_stream(process.stdout, stdout_lines),
            read_stream(process.stderr, stderr_lines, True)
        )
        
        await process.wait()
        return process.returncode, '\n'.join(stdout_lines), '\n'.join(stderr_lines)
```

### 4.2 示例适配器

```python
# src-python/adapters/file_tools/samea_adapter.py
from typing import Optional, Callable, Awaitable, Dict, Any
from pydantic import BaseModel, Field
from ..base import BaseAdapter, ToolOutput

class SameaInput(BaseModel):
    path: str = Field(..., description="要分析的目录路径")
    threshold: float = Field(default=0.9, ge=0, le=1, description="相似度阈值")
    method: str = Field(default="hash", description="比较方法")

class SameaAdapter(BaseAdapter):
    name = "samea"
    display_name = "相似文件分析"
    description = "分析目录中的相似文件"
    category = "file"
    
    @property
    def input_schema(self):
        return SameaInput
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        on_progress: Optional[Callable[[int], Awaitable[None]]] = None,
        on_output: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> ToolOutput:
        params = SameaInput(**input_data)
        
        cmd = ["samea", params.path]
        if params.threshold != 0.9:
            cmd.extend(["--threshold", str(params.threshold)])
        if params.method != "hash":
            cmd.extend(["--method", params.method])
        
        returncode, stdout, stderr = await self._run_subprocess(cmd, on_output)
        
        if returncode == 0:
            return ToolOutput(
                success=True,
                message="分析完成",
                data={"output": stdout}
            )
        else:
            return ToolOutput(
                success=False,
                message="执行失败",
                error=stderr
            )
```

### 4.3 任务执行引擎

```python
# src-python/core/executor.py
import asyncio
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"

@dataclass
class TaskContext:
    task_id: str
    flow_id: str
    status: TaskStatus = TaskStatus.PENDING
    node_statuses: Dict[str, NodeStatus] = field(default_factory=dict)
    node_outputs: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

class FlowExecutor:
    def __init__(self, broadcast_callback: Callable):
        self.tasks: Dict[str, TaskContext] = {}
        self.broadcast = broadcast_callback
    
    async def execute_flow(self, flow: Dict, inputs: Dict[str, Any] = None) -> str:
        """执行流程"""
        task_id = str(uuid.uuid4())
        context = TaskContext(
            task_id=task_id,
            flow_id=flow["id"],
            started_at=datetime.now()
        )
        self.tasks[task_id] = context
        
        # 异步执行
        asyncio.create_task(self._execute_flow_async(context, flow, inputs or {}))
        
        return task_id
    
    async def _execute_flow_async(self, context: TaskContext, flow: Dict, inputs: Dict):
        """异步执行流程"""
        context.status = TaskStatus.RUNNING
        await self._broadcast_status(context)
        
        try:
            # 拓扑排序获取执行顺序
            execution_order = self._topological_sort(flow["nodes"], flow["edges"])
            
            for node in execution_order:
                await self._execute_node(context, node, flow["edges"])
            
            context.status = TaskStatus.COMPLETED
            context.completed_at = datetime.now()
            
        except Exception as e:
            context.status = TaskStatus.FAILED
            context.error = str(e)
            context.completed_at = datetime.now()
        
        await self._broadcast_status(context)
    
    async def _execute_node(self, context: TaskContext, node: Dict, edges: list):
        """执行单个节点"""
        node_id = node["id"]
        context.node_statuses[node_id] = NodeStatus.RUNNING
        await self._broadcast_node_status(context, node_id)
        
        try:
            # 获取输入
            node_inputs = self._get_node_inputs(context, node_id, edges)
            
            # 根据节点类型执行
            result = await self._run_node(node, node_inputs, context)
            
            context.node_outputs[node_id] = result
            context.node_statuses[node_id] = NodeStatus.COMPLETED
            
        except Exception as e:
            context.node_statuses[node_id] = NodeStatus.ERROR
            raise
        
        await self._broadcast_node_status(context, node_id)
    
    async def _run_node(self, node: Dict, inputs: Dict, context: TaskContext) -> Any:
        """运行节点"""
        node_type = node["type"]
        
        if node_type.startswith("tool_"):
            tool_name = node_type.replace("tool_", "")
            from adapters import get_adapter
            adapter = get_adapter(tool_name)
            
            async def on_output(text: str):
                await self.broadcast(context.task_id, {
                    "type": "task_output",
                    "nodeId": node["id"],
                    "data": {"output": text}
                })
            
            result = await adapter.execute(
                {**node.get("data", {}).get("config", {}), **inputs},
                on_output=on_output
            )
            return result.data
        
        elif node_type == "clipboard_input":
            import pyperclip
            return {"text": pyperclip.paste()}
        
        elif node_type == "path_input":
            return {"path": node.get("data", {}).get("config", {}).get("path", "")}
        
        return None
    
    def _topological_sort(self, nodes: list, edges: list) -> list:
        """拓扑排序"""
        # 简化实现：按edges依赖关系排序
        node_map = {n["id"]: n for n in nodes}
        in_degree = {n["id"]: 0 for n in nodes}
        
        for edge in edges:
            in_degree[edge["target"]] += 1
        
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []
        
        while queue:
            nid = queue.pop(0)
            result.append(node_map[nid])
            
            for edge in edges:
                if edge["source"] == nid:
                    in_degree[edge["target"]] -= 1
                    if in_degree[edge["target"]] == 0:
                        queue.append(edge["target"])
        
        return result
    
    def _get_node_inputs(self, context: TaskContext, node_id: str, edges: list) -> Dict:
        """获取节点输入"""
        inputs = {}
        for edge in edges:
            if edge["target"] == node_id:
                source_output = context.node_outputs.get(edge["source"], {})
                inputs.update(source_output if isinstance(source_output, dict) else {"value": source_output})
        return inputs
    
    async def _broadcast_status(self, context: TaskContext):
        """广播任务状态"""
        await self.broadcast(context.task_id, {
            "type": "task_status",
            "data": {
                "status": context.status.value,
                "error": context.error
            }
        })
    
    async def _broadcast_node_status(self, context: TaskContext, node_id: str):
        """广播节点状态"""
        await self.broadcast(context.task_id, {
            "type": "node_status",
            "nodeId": node_id,
            "data": {
                "status": context.node_statuses[node_id].value
            }
        })
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.CANCELLED
            return True
        return False
```

---

## 五、WebSocket集成

### 5.1 后端WebSocket

```python
# src-python/api/websocket_api.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json

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
            dead_connections = []
            for ws in self.connections[task_id]:
                try:
                    await ws.send_json(message)
                except:
                    dead_connections.append(ws)
            for ws in dead_connections:
                self.connections[task_id].discard(ws)

manager = ConnectionManager()

# 在main.py中添加
@app.websocket("/v1/ws/tasks/{task_id}")
async def websocket_task(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
```

### 5.2 前端WebSocket

```typescript
// src/lib/services/websocket.ts
import { writable, type Writable } from 'svelte/store';
import { taskStore } from '$lib/stores/taskStore';

export interface TaskWebSocket {
  connect(): void;
  disconnect(): void;
  status: Writable<'connecting' | 'connected' | 'disconnected' | 'error'>;
}

export function createTaskWebSocket(taskId: string): TaskWebSocket {
  const status = writable<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  let ws: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  
  function connect() {
    if (ws?.readyState === WebSocket.OPEN) return;
    
    status.set('connecting');
    ws = new WebSocket(`ws://localhost:8009/v1/ws/tasks/${taskId}`);
    
    ws.onopen = () => {
      status.set('connected');
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };
    
    ws.onclose = () => {
      status.set('disconnected');
      // 自动重连
      reconnectTimer = setTimeout(connect, 3000) as unknown as number;
    };
    
    ws.onerror = () => {
      status.set('error');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleMessage(data);
    };
  }
  
  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    ws?.close();
    ws = null;
    status.set('disconnected');
  }
  
  function handleMessage(data: any) {
    switch (data.type) {
      case 'task_status':
        if (data.data.status === 'completed') {
          taskStore.completeTask(true);
        } else if (data.data.status === 'failed') {
          taskStore.completeTask(false);
        }
        break;
      
      case 'node_status':
        taskStore.updateNodeStatus(data.nodeId, {
          status: data.data.status
        });
        break;
      
      case 'task_output':
        taskStore.addLog({
          timestamp: new Date().toISOString(),
          nodeId: data.nodeId,
          type: 'stdout',
          content: data.data.output
        });
        break;
    }
  }
  
  return { connect, disconnect, status };
}
```

---

## 六、测试与验证

### 6.1 手动测试流程

```bash
# 1. 启动后端
cd src-python
python main.py --standalone

# 2. 启动前端
yarn dev

# 3. 访问 http://localhost:5173
# 4. 创建流程: 剪贴板输入 → Samea → 日志输出
# 5. 执行并观察实时日志
```

### 6.2 验证清单

- [ ] SvelteFlow画布正常渲染
- [ ] 节点拖拽、连线工作正常
- [ ] 流程保存/加载正常
- [ ] 任务执行触发正常
- [ ] WebSocket连接稳定
- [ ] 实时日志显示正常
- [ ] 节点状态更新正常
- [ ] 错误处理正确

---

## 七、构建与部署

### 7.1 开发模式

```bash
# Tauri开发
yarn tauri dev

# 纯Web开发
yarn dev:standalone
```

### 7.2 生产构建

```bash
# 构建前端
yarn build

# 构建Tauri应用
python build.py
```

---

## 八、常见问题

### Q1: SvelteFlow SSR错误
**解决**: 确保`svelte.config.js`中设置`ssr: false`

### Q2: WebSocket连接失败
**检查**: 
- 后端是否运行在正确端口
- CORS配置是否包含前端地址
- 防火墙是否阻止

### Q3: Python工具执行失败
**检查**:
- 工具是否在PATH中
- 虚拟环境是否激活
- 路径是否正确转义
