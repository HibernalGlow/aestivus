# AestivalFlow 设计文档

> **版本**: 1.0.0  
> **创建日期**: 2025-12-12  
> **项目定位**: Python工具链可视化编排与执行平台

---

## 一、项目概述

### 1.1 背景与动机

基于命令使用分析报告，用户拥有一套成熟的Python工具链用于文件处理、视频处理等任务。这些工具：
- 高度自动化（平均参数使用率仅5%）
- 存在固定工作流模式（如 `samea → crashu → migratef`）
- 但缺乏统一的可视化界面和流程编排能力

**AestivalFlow** 旨在为这些工具提供：
1. 统一的GUI界面，支持拖拽式流程编排
2. 实时任务状态监控与日志展示
3. 剪贴板/路径输入等通用输入模块
4. 本地包兼容层，无需修改原有工具代码

### 1.2 核心目标

| 目标 | 描述 |
|------|------|
| **可视化编排** | 使用SvelteFlow实现节点拖拽式工作流编排 |
| **实时监控** | WebSocket推送任务执行状态、进度、日志 |
| **模块化输入** | 剪贴板读取、路径选择、参数配置等可复用输入模块 |
| **零侵入集成** | 通过适配器模式封装现有Python包，无需修改源码 |
| **多兼容执行** | 支持模块导入、独立venv、CLI三种执行模式 |
| **参数持久化** | 工具默认参数、预设、执行历史自动保存 |

---

## 二、需求分析

### 2.1 目标工具清单

根据命令使用分析报告，需集成的Python工具：

#### 文件处理工具链（核心）
| 工具 | 使用频率 | 功能 | 参数复杂度 |
|------|----------|------|------------|
| `repacku` | 82次 | 文件重打包 | 低（0%参数） |
| `rawfilter` | 51次 | 原始文件过滤 | 低（2%参数） |
| `samea` | 50次 | 相似文件分析 | 中（16%参数） |
| `crashu` | 46次 | 崩溃文件处理 | 低（9%参数） |
| `migratef` | 52次 | 文件迁移 | 低（4%参数） |
| `nameu` | 39次 | 文件命名 | 低（3%参数） |
| `cleanf` | 16次 | 清理文件 | 低 |
| `dissolvef` | - | 解散文件 | 低 |
| `coveru` | - | 封面处理 | 低 |

#### 视频处理工具
| 工具 | 使用频率 | 功能 |
|------|----------|------|
| `formatv` | 37次 | 视频格式化 |
| `brakev` | - | 视频压缩(HandBrake) |

#### 其他工具
| 工具 | 功能 |
|------|------|
| `psdc` | PSD转换 |
| `synct` | 同步任务 |
| `linku` | 链接工具 |
| `lata` | 懒人任务工具 |

### 2.2 常见工作流模式

```
工作流1: 文件整理流程 (8次)
┌─────────┐    ┌─────────┐    ┌──────────┐
│  samea  │───▶│ crashu  │───▶│ migratef │
└─────────┘    └─────────┘    └──────────┘

工作流2: 视频处理流程 (14次)
┌──────────┐    ┌──────────┐
│ formatv  │───▶│ migratef │
└──────────┘    └──────────┘

工作流3: 完整清理流程 (4次)
┌─────────┐    ┌─────────┐    ┌──────────┐    ┌───────────────────┐
│  samea  │───▶│ crashu  │───▶│ migratef │───▶│ 目标: E:\...\4EHV │
└─────────┘    └─────────┘    └──────────┘    └───────────────────┘
```

### 2.3 功能需求

#### P0 - 核心功能
- [ ] **节点编排系统**: SvelteFlow节点拖拽、连线、保存/加载流程
- [ ] **任务执行引擎**: 按流程顺序执行Python工具，支持并行分支
- [ ] **实时状态推送**: WebSocket推送执行进度、输出日志、错误信息
- [ ] **通用输入节点**: 剪贴板读取、文件夹选择、文件选择、文本输入

#### P1 - 重要功能
- [ ] **工具适配器层**: 为每个Python工具创建标准化适配器
- [ ] **参数配置面板**: 可视化配置工具参数
- [ ] **执行历史记录**: 保存执行记录，支持回溯查看
- [ ] **流程模板**: 预设常用工作流模板

#### P1+ - 环境与配置 (详见 [TOOL_RUNTIME.md](./TOOL_RUNTIME.md))
- [ ] **独立venv支持**: 每个工具可配置独立虚拟环境
- [ ] **pip -e模式**: 本地开发包editable安装
- [ ] **多兼容执行**: Module导入 / 独立Venv / 全局CLI
- [ ] **参数持久化**: 默认值、预设、执行历史

#### P2 - 增强功能
- [ ] **条件分支节点**: 根据前序输出决定后续路径
- [ ] **循环节点**: 批量处理多个输入
- [ ] **定时任务**: 支持定时触发流程执行

---

## 三、系统架构

### 3.1 整体架构图

```
┌────────────────────────────────────────────────────────────────────────┐
│                           AestivalFlow                                  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Frontend (SvelteKit)                          │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │   │
│  │  │  SvelteFlow  │ │   shadcn/ui  │ │      Tailwind CSS        │ │   │
│  │  │  节点编排器   │ │   组件库     │ │        样式系统          │ │   │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘ │   │
│  │  ┌──────────────────────────────────────────────────────────────┐│   │
│  │  │                    状态管理 (Svelte Stores)                   ││   │
│  │  │  • flowStore (流程状态)  • taskStore (任务状态)              ││   │
│  │  │  • configStore (配置)    • logStore (日志)                   ││   │
│  │  └──────────────────────────────────────────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │ HTTP/WS                                  │
│  ┌───────────────────────────┴─────────────────────────────────────┐   │
│  │                    Backend (FastAPI)                             │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │   │
│  │  │  REST API    │ │  WebSocket   │ │    任务调度引擎          │ │   │
│  │  │  流程CRUD    │ │  实时推送    │ │    TaskExecutor          │ │   │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘ │   │
│  │  ┌──────────────────────────────────────────────────────────────┐│   │
│  │  │                    工具适配器层 (Adapters)                    ││   │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            ││   │
│  │  │  │ repacku │ │  samea  │ │ crashu  │ │migratef │ ...        ││   │
│  │  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘            ││   │
│  │  └──────────────────────────────────────────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │ subprocess                               │
│  ┌───────────────────────────┴─────────────────────────────────────┐   │
│  │                    Python工具包 (现有)                           │   │
│  │  repacku │ rawfilter │ samea │ crashu │ migratef │ nameu │ ...  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
├────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Tauri Shell (可选)                            │   │
│  │  • 窗口管理  • 文件系统访问  • 系统对话框  • 剪贴板访问          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| **前端框架** | SvelteKit 5 | 现有项目基础，响应式性能优秀 |
| **流程编排** | SvelteFlow | Svelte原生Flow库，支持自定义节点 |
| **UI组件** | shadcn/svelte + bits-ui | 现有项目已集成，美观现代 |
| **样式** | Tailwind CSS 4 | 现有项目已集成 |
| **图标** | Lucide | 现有项目已集成 |
| **包管理** | yarn | 用户指定 |
| **后端框架** | FastAPI | 现有项目基础，异步性能好 |
| **实时通信** | WebSocket | 任务状态实时推送 |
| **任务执行** | asyncio + subprocess | 异步执行Python工具 |
| **桌面端** | Tauri 2 | 现有项目基础，轻量跨平台 |
| **数据存储** | JSON文件 / SQLite | 轻量级，流程配置持久化 |

### 3.3 数据流设计

```
用户操作                前端                    后端                    工具执行
   │                     │                       │                        │
   │  拖拽节点           │                       │                        │
   ├────────────────────▶│                       │                        │
   │                     │  更新flowStore        │                        │
   │                     ├──────────────────────▶│                        │
   │                     │                       │                        │
   │  点击执行           │                       │                        │
   ├────────────────────▶│                       │                        │
   │                     │  POST /flow/execute   │                        │
   │                     ├──────────────────────▶│                        │
   │                     │                       │  创建任务              │
   │                     │                       ├───────────────────────▶│
   │                     │                       │                        │
   │                     │  WS: task_started     │                        │
   │                     │◀────────────────────── │                        │
   │  显示执行中         │                       │                        │
   │◀────────────────────│                       │                        │
   │                     │                       │  stdout/stderr         │
   │                     │  WS: task_output      │◀───────────────────────│
   │                     │◀────────────────────── │                        │
   │  实时日志           │                       │                        │
   │◀────────────────────│                       │                        │
   │                     │                       │  执行完成              │
   │                     │  WS: task_completed   │◀───────────────────────│
   │                     │◀────────────────────── │                        │
   │  显示结果           │                       │                        │
   │◀────────────────────│                       │                        │
```

---

## 四、模块设计

### 4.1 前端模块结构

```
src/
├── lib/
│   ├── components/
│   │   ├── ui/                    # shadcn组件 (现有)
│   │   ├── flow/                  # 流程编排组件
│   │   │   ├── FlowCanvas.svelte      # SvelteFlow画布
│   │   │   ├── NodePalette.svelte     # 节点面板
│   │   │   ├── NodeConfigPanel.svelte # 节点配置面板
│   │   │   └── FlowToolbar.svelte     # 工具栏
│   │   ├── nodes/                 # 自定义节点组件
│   │   │   ├── BaseNode.svelte        # 节点基类
│   │   │   ├── InputNode.svelte       # 输入节点
│   │   │   ├── ToolNode.svelte        # 工具节点
│   │   │   ├── OutputNode.svelte      # 输出节点
│   │   │   └── ConditionNode.svelte   # 条件节点
│   │   ├── execution/             # 执行相关组件
│   │   │   ├── TaskProgress.svelte    # 任务进度
│   │   │   ├── LogViewer.svelte       # 日志查看器
│   │   │   └── ExecutionHistory.svelte# 执行历史
│   │   └── input/                 # 输入模块组件
│   │       ├── ClipboardInput.svelte  # 剪贴板输入
│   │       ├── PathInput.svelte       # 路径输入
│   │       └── TextInput.svelte       # 文本输入
│   ├── stores/                    # 状态管理
│   │   ├── flowStore.ts               # 流程状态
│   │   ├── taskStore.ts               # 任务状态
│   │   ├── nodeStore.ts               # 节点注册
│   │   └── wsStore.ts                 # WebSocket连接
│   ├── services/                  # 服务层
│   │   ├── api.ts                     # REST API封装
│   │   ├── websocket.ts               # WebSocket服务
│   │   └── tauri.ts                   # Tauri桥接
│   ├── types/                     # 类型定义
│   │   ├── flow.ts                    # 流程类型
│   │   ├── node.ts                    # 节点类型
│   │   └── task.ts                    # 任务类型
│   └── utils/                     # 工具函数
│       ├── flowUtils.ts               # 流程工具
│       └── nodeUtils.ts               # 节点工具
└── routes/
    ├── +layout.svelte
    ├── +page.svelte               # 主页/流程列表
    └── flow/
        └── [id]/
            └── +page.svelte       # 流程编辑页
```

### 4.2 后端模块结构

```
src-python/
├── api/
│   ├── __init__.py
│   ├── endpoints.py               # 基础端点 (现有)
│   ├── flow_api.py                # 流程管理API
│   ├── task_api.py                # 任务执行API
│   └── websocket_api.py           # WebSocket端点
├── core/
│   ├── __init__.py
│   ├── executor.py                # 任务执行引擎
│   ├── scheduler.py               # 任务调度器
│   └── flow_parser.py             # 流程解析器
├── adapters/                      # 工具适配器
│   ├── __init__.py
│   ├── base.py                    # 适配器基类
│   ├── file_tools/                # 文件处理工具
│   │   ├── repacku_adapter.py
│   │   ├── rawfilter_adapter.py
│   │   ├── samea_adapter.py
│   │   ├── crashu_adapter.py
│   │   ├── migratef_adapter.py
│   │   ├── nameu_adapter.py
│   │   ├── cleanf_adapter.py
│   │   └── dissolvef_adapter.py
│   ├── video_tools/               # 视频处理工具
│   │   ├── formatv_adapter.py
│   │   └── brakev_adapter.py
│   └── other_tools/               # 其他工具
│       ├── psdc_adapter.py
│       ├── synct_adapter.py
│       └── linku_adapter.py
├── models/
│   ├── __init__.py
│   ├── flow.py                    # 流程数据模型
│   ├── node.py                    # 节点数据模型
│   └── task.py                    # 任务数据模型
├── storage/
│   ├── __init__.py
│   └── flow_storage.py            # 流程持久化
├── main.py                        # 入口 (扩展现有)
└── requirements.txt
```

### 4.3 节点类型设计

#### 4.3.1 输入节点 (Input Nodes)

| 节点 | 输出类型 | 描述 |
|------|----------|------|
| `clipboard` | `string` | 读取剪贴板内容 |
| `file_picker` | `string[]` | 文件选择对话框 |
| `folder_picker` | `string` | 文件夹选择对话框 |
| `text_input` | `string` | 手动文本输入 |
| `path_input` | `string` | 路径输入(支持拖拽) |

#### 4.3.2 工具节点 (Tool Nodes)

| 节点 | 输入 | 输出 | 参数 |
|------|------|------|------|
| `repacku` | `path` | `path` | - |
| `rawfilter` | `path` | `path[]` | `pattern?` |
| `samea` | `path` | `path[], report` | `threshold?`, `method?` |
| `crashu` | `path` | `path[]` | - |
| `migratef` | `path[]` | `path` | `target`, `mode`, `existing_dir` |
| `nameu` | `path[]` | `path[]` | `pattern?` |
| `formatv` | `path[]` | `path[]` | `format?`, `quality?` |

#### 4.3.3 控制节点 (Control Nodes)

| 节点 | 描述 |
|------|------|
| `condition` | 条件分支，根据输入值路由 |
| `loop` | 循环处理数组输入 |
| `merge` | 合并多个输入 |
| `delay` | 延迟执行 |

#### 4.3.4 输出节点 (Output Nodes)

| 节点 | 描述 |
|------|------|
| `log` | 输出到日志面板 |
| `notification` | 系统通知 |
| `file_output` | 保存到文件 |

---

## 五、API设计

### 5.1 REST API

#### 流程管理
```
GET    /v1/flows                  # 获取流程列表
POST   /v1/flows                  # 创建新流程
GET    /v1/flows/{id}             # 获取流程详情
PUT    /v1/flows/{id}             # 更新流程
DELETE /v1/flows/{id}             # 删除流程
POST   /v1/flows/{id}/duplicate   # 复制流程
```

#### 任务执行
```
POST   /v1/tasks/execute          # 执行流程
GET    /v1/tasks/{id}             # 获取任务状态
POST   /v1/tasks/{id}/cancel      # 取消任务
GET    /v1/tasks/history          # 执行历史
```

#### 工具管理
```
GET    /v1/tools                  # 获取可用工具列表
GET    /v1/tools/{name}           # 获取工具详情
GET    /v1/tools/{name}/schema    # 获取工具参数Schema
```

#### 系统功能
```
GET    /v1/system/clipboard       # 读取剪贴板
POST   /v1/system/browse          # 打开文件/文件夹选择对话框
GET    /v1/system/health          # 健康检查
```

### 5.2 WebSocket API

#### 连接端点
```
WS /v1/ws/tasks/{task_id}         # 任务实时状态
WS /v1/ws/system                  # 系统事件
```

#### 消息格式
```typescript
// 任务事件
interface TaskEvent {
  type: 'task_started' | 'task_progress' | 'task_output' | 'task_completed' | 'task_error';
  taskId: string;
  nodeId?: string;
  data: {
    progress?: number;      // 0-100
    output?: string;        // stdout内容
    error?: string;         // stderr内容
    result?: any;           // 执行结果
    timestamp: string;
  };
}

// 节点状态
interface NodeStatus {
  nodeId: string;
  status: 'pending' | 'running' | 'completed' | 'error' | 'skipped';
  startTime?: string;
  endTime?: string;
  output?: any;
  error?: string;
}
```

### 5.3 数据模型

#### 流程定义
```typescript
interface Flow {
  id: string;
  name: string;
  description?: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
  createdAt: string;
  updatedAt: string;
}

interface FlowNode {
  id: string;
  type: string;           // 节点类型
  position: { x: number; y: number };
  data: {
    label: string;
    config: Record<string, any>;  // 节点配置
  };
}

interface FlowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}
```

#### 任务定义
```typescript
interface Task {
  id: string;
  flowId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  nodeStatuses: Record<string, NodeStatus>;
  startedAt?: string;
  completedAt?: string;
  error?: string;
}
```

---

## 六、适配器设计

### 6.1 适配器基类

```python
# src-python/adapters/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ToolInput(BaseModel):
    """工具输入基类"""
    pass

class ToolOutput(BaseModel):
    """工具输出基类"""
    success: bool
    message: str
    data: Any = None

class BaseAdapter(ABC):
    """工具适配器基类"""
    
    name: str                    # 工具名称
    display_name: str            # 显示名称
    description: str             # 工具描述
    category: str                # 分类: file, video, other
    input_schema: type           # 输入Schema (Pydantic)
    output_schema: type          # 输出Schema (Pydantic)
    
    @abstractmethod
    async def execute(
        self, 
        input_data: ToolInput,
        on_progress: callable = None,
        on_output: callable = None
    ) -> ToolOutput:
        """执行工具"""
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Dict) -> bool:
        """验证输入"""
        pass
    
    def get_schema(self) -> Dict:
        """获取参数Schema (用于前端生成表单)"""
        return self.input_schema.model_json_schema()
```

### 6.2 示例适配器

```python
# src-python/adapters/file_tools/samea_adapter.py

import asyncio
import subprocess
from typing import Optional
from pydantic import BaseModel, Field
from ..base import BaseAdapter, ToolInput, ToolOutput

class SameaInput(ToolInput):
    path: str = Field(..., description="要分析的目录路径")
    threshold: float = Field(default=0.9, description="相似度阈值", ge=0, le=1)
    method: str = Field(default="hash", description="比较方法", enum=["hash", "pixel"])

class SameaOutput(ToolOutput):
    similar_groups: list = Field(default=[], description="相似文件组")
    report_path: Optional[str] = Field(None, description="报告文件路径")

class SameaAdapter(BaseAdapter):
    name = "samea"
    display_name = "相似文件分析"
    description = "分析目录中的相似文件，支持hash和pixel两种比较方法"
    category = "file"
    input_schema = SameaInput
    output_schema = SameaOutput
    
    async def execute(
        self,
        input_data: SameaInput,
        on_progress: callable = None,
        on_output: callable = None
    ) -> SameaOutput:
        cmd = ["samea", input_data.path]
        if input_data.threshold != 0.9:
            cmd.extend(["--threshold", str(input_data.threshold)])
        if input_data.method != "hash":
            cmd.extend(["--method", input_data.method])
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # 实时读取输出
        async for line in process.stdout:
            if on_output:
                await on_output(line.decode())
        
        await process.wait()
        
        if process.returncode == 0:
            return SameaOutput(
                success=True,
                message="分析完成",
                similar_groups=[],  # 从输出解析
            )
        else:
            stderr = await process.stderr.read()
            return SameaOutput(
                success=False,
                message=f"执行失败: {stderr.decode()}"
            )
    
    def validate_input(self, input_data: dict) -> bool:
        try:
            SameaInput(**input_data)
            return True
        except:
            return False
```

### 6.3 适配器注册

```python
# src-python/adapters/__init__.py

from .base import BaseAdapter
from .file_tools.repacku_adapter import RepackuAdapter
from .file_tools.samea_adapter import SameaAdapter
from .file_tools.crashu_adapter import CrashuAdapter
from .file_tools.migratef_adapter import MigratefAdapter
# ... 其他适配器

# 适配器注册表
ADAPTERS: dict[str, type[BaseAdapter]] = {
    "repacku": RepackuAdapter,
    "samea": SameaAdapter,
    "crashu": CrashuAdapter,
    "migratef": MigratefAdapter,
    # ...
}

def get_adapter(name: str) -> BaseAdapter:
    """获取适配器实例"""
    if name not in ADAPTERS:
        raise ValueError(f"Unknown adapter: {name}")
    return ADAPTERS[name]()

def list_adapters() -> list[dict]:
    """列出所有适配器"""
    return [
        {
            "name": adapter.name,
            "displayName": adapter.display_name,
            "description": adapter.description,
            "category": adapter.category,
            "schema": adapter().get_schema()
        }
        for adapter in ADAPTERS.values()
    ]
```

---

## 七、前端组件设计

### 7.1 SvelteFlow集成

```svelte
<!-- src/lib/components/flow/FlowCanvas.svelte -->
<script lang="ts">
  import { SvelteFlow, Background, Controls, MiniMap } from '@xyflow/svelte';
  import { flowStore } from '$lib/stores/flowStore';
  import { nodeTypes } from '$lib/components/nodes';
  
  // 自定义节点类型注册
  const customNodeTypes = {
    input: InputNode,
    tool: ToolNode,
    output: OutputNode,
    condition: ConditionNode
  };
</script>

<div class="h-full w-full">
  <SvelteFlow
    nodes={$flowStore.nodes}
    edges={$flowStore.edges}
    nodeTypes={customNodeTypes}
    on:nodeschange={flowStore.onNodesChange}
    on:edgeschange={flowStore.onEdgesChange}
    on:connect={flowStore.onConnect}
    fitView
  >
    <Background />
    <Controls />
    <MiniMap />
  </SvelteFlow>
</div>
```

### 7.2 自定义节点

```svelte
<!-- src/lib/components/nodes/ToolNode.svelte -->
<script lang="ts">
  import { Handle, Position } from '@xyflow/svelte';
  import { cn } from '$lib/utils';
  
  export let data: {
    label: string;
    toolName: string;
    status: 'idle' | 'running' | 'completed' | 'error';
    config: Record<string, any>;
  };
  
  const statusColors = {
    idle: 'border-gray-300',
    running: 'border-blue-500 animate-pulse',
    completed: 'border-green-500',
    error: 'border-red-500'
  };
</script>

<div class={cn(
  "px-4 py-2 rounded-lg border-2 bg-white shadow-md min-w-[150px]",
  statusColors[data.status]
)}>
  <Handle type="target" position={Position.Left} />
  
  <div class="flex items-center gap-2">
    <div class="w-2 h-2 rounded-full" class:bg-blue-500={data.status === 'running'} />
    <span class="font-medium text-sm">{data.label}</span>
  </div>
  <div class="text-xs text-gray-500 mt-1">{data.toolName}</div>
  
  <Handle type="source" position={Position.Right} />
</div>
```

### 7.3 实时日志组件

```svelte
<!-- src/lib/components/execution/LogViewer.svelte -->
<script lang="ts">
  import { taskStore } from '$lib/stores/taskStore';
  import { ScrollArea } from '$lib/components/ui/scroll-area';
  
  let logContainer: HTMLElement;
  
  // 自动滚动到底部
  $: if ($taskStore.logs.length && logContainer) {
    logContainer.scrollTop = logContainer.scrollHeight;
  }
</script>

<div class="h-full flex flex-col bg-gray-900 rounded-lg">
  <div class="px-4 py-2 border-b border-gray-700">
    <span class="text-white font-medium">执行日志</span>
  </div>
  
  <ScrollArea class="flex-1 p-4" bind:element={logContainer}>
    {#each $taskStore.logs as log}
      <div class="font-mono text-sm mb-1" class:text-green-400={log.type === 'stdout'} class:text-red-400={log.type === 'stderr'}>
        <span class="text-gray-500">[{log.timestamp}]</span>
        <span class="text-blue-400">[{log.nodeId}]</span>
        {log.content}
      </div>
    {/each}
  </ScrollArea>
</div>
```

---

## 八、WebUI兼容性设计

### 8.1 双端架构

```
                    ┌──────────────────┐
                    │   SvelteKit UI   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────────┐ ┌─────────────────┐
    │   Tauri Mode    │ │    Web Mode     │
    │                 │ │                 │
    │ • 本地文件访问  │ │ • 远程API访问   │
    │ • 系统对话框    │ │ • 文件上传      │
    │ • 剪贴板(native)│ │ • 剪贴板(web API)│
    └────────┬────────┘ └────────┬────────┘
             │                   │
             └─────────┬─────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  FastAPI Backend │
              │  (localhost/远程) │
              └─────────────────┘
```

### 8.2 平台抽象层

```typescript
// src/lib/services/platform.ts

interface PlatformService {
  readClipboard(): Promise<string>;
  writeClipboard(text: string): Promise<void>;
  openFileDialog(options?: FileDialogOptions): Promise<string[]>;
  openFolderDialog(): Promise<string | null>;
}

// Tauri实现
class TauriPlatform implements PlatformService {
  async readClipboard() {
    const { readText } = await import('@tauri-apps/plugin-clipboard-manager');
    return readText();
  }
  
  async openFileDialog(options) {
    const { open } = await import('@tauri-apps/plugin-dialog');
    return open({ multiple: true, ...options });
  }
}

// Web实现 (通过后端API)
class WebPlatform implements PlatformService {
  async readClipboard() {
    return navigator.clipboard.readText();
  }
  
  async openFileDialog() {
    // 触发文件上传或通过API打开对话框
    const response = await fetch('/v1/system/browse', {
      method: 'POST',
      body: JSON.stringify({ type: 'file', multiple: true })
    });
    return response.json();
  }
}

// 平台检测与导出
export const platform: PlatformService = 
  window.__TAURI__ ? new TauriPlatform() : new WebPlatform();
```

---

## 九、实施计划

### 9.1 阶段划分

#### Phase 1: 基础框架 (1-2周)
- [ ] 迁移包管理器从pnpm到yarn
- [ ] 集成SvelteFlow
- [ ] 实现基础节点类型（输入、输出）
- [ ] 实现流程保存/加载
- [ ] WebSocket基础通信

#### Phase 2: 工具集成 (2-3周)
- [ ] 实现适配器基类
- [ ] 集成核心文件工具 (repacku, samea, crashu, migratef)
- [ ] 实现任务执行引擎
- [ ] 实时日志推送

#### Phase 3: UI完善 (1-2周)
- [ ] 节点配置面板
- [ ] 执行历史
- [ ] 流程模板
- [ ] 错误处理与重试

#### Phase 4: 扩展功能 (1-2周)
- [ ] 集成剩余工具
- [ ] 条件分支、循环节点
- [ ] WebUI独立部署支持
- [ ] 文档与测试

### 9.2 里程碑

| 里程碑 | 目标 | 预计时间 |
|--------|------|----------|
| M1 | 可运行的流程编排界面 | Week 2 |
| M2 | 单工具执行与日志显示 | Week 4 |
| M3 | 完整工作流执行 | Week 6 |
| M4 | 生产可用版本 | Week 8 |

---

## 十、风险评估

### 10.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| SvelteFlow与Svelte5兼容性 | 中 | 高 | 评估@xyflow/svelte版本，准备降级方案 |
| Python工具stdout解析困难 | 中 | 中 | 为每个工具定制输出解析器 |
| WebSocket连接不稳定 | 低 | 中 | 实现重连机制和状态恢复 |
| 大文件处理性能 | 中 | 中 | 分片处理、进度反馈 |

### 10.2 依赖风险

| 依赖 | 风险 | 缓解措施 |
|------|------|----------|
| 现有Python工具 | 工具接口变更 | 适配器隔离，版本锁定 |
| SvelteFlow | 库不成熟 | 保留回退到react-flow + iframe方案 |
| Tauri 2 | 新版本API变化 | 关注官方更新，及时跟进 |

---

## 十一、总结

AestivalFlow将为现有Python工具链提供统一的可视化编排界面，核心价值在于：

1. **零侵入**: 通过适配器层封装，无需修改现有工具代码
2. **可视化**: SvelteFlow提供直观的拖拽式流程编排
3. **实时性**: WebSocket推送确保任务状态实时可见
4. **模块化**: 输入、工具、输出节点解耦，灵活组合
5. **双端兼容**: 同时支持Tauri桌面端和纯Web部署

建议从Phase 1开始迭代开发，优先实现核心文件处理工作流（samea → crashu → migratef），验证架构可行性后再扩展。
