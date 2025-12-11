# AestivalFlow 技术评估报告

> **版本**: 1.0.0  
> **评估日期**: 2025-12-12

---

## 一、SvelteFlow 集成评估

### 1.1 库选型对比

| 库 | 框架 | Stars | 维护状态 | Svelte5支持 |
|---|---|---|---|---|
| **@xyflow/svelte** | Svelte | 1.5k+ | 活跃 | ✅ 支持 |
| svelvet | Svelte | 2k+ | 较活跃 | ⚠️ 部分支持 |
| react-flow + iframe | React | 20k+ | 活跃 | N/A (需iframe) |

**结论**: 选用 `@xyflow/svelte`，理由：
- 官方维护，与react-flow同源，功能完整
- 原生Svelte支持，无需iframe桥接
- 文档完善，社区活跃

### 1.2 @xyflow/svelte 功能评估

#### 核心功能 ✅
- [x] 节点拖拽与定位
- [x] 边连接与删除
- [x] 自定义节点组件
- [x] 自定义边类型
- [x] 缩放与平移
- [x] MiniMap、Controls、Background
- [x] 节点选择与多选
- [x] 撤销/重做 (需自行实现)

#### 限制与风险 ⚠️
| 问题 | 影响 | 解决方案 |
|------|------|----------|
| SSR不支持 | 需禁用服务端渲染 | 使用`ssr: false`配置 |
| 性能瓶颈(>1000节点) | 大流程卡顿 | 分页加载、虚拟化 |
| 触摸事件有限 | 移动端体验差 | 桌面端优先，暂不支持移动端 |

### 1.3 安装与配置

```bash
# 使用yarn安装
yarn add @xyflow/svelte
```

```typescript
// svelte.config.js - 禁用SSR
import adapter from '@sveltejs/adapter-static';

export default {
  kit: {
    adapter: adapter({
      fallback: 'index.html'
    }),
    ssr: false  // SvelteFlow需要禁用SSR
  }
};
```

---

## 二、现有项目兼容性评估

### 2.1 包管理器迁移 (pnpm → yarn)

**迁移步骤**:
```bash
# 1. 删除pnpm相关文件
rm pnpm-lock.yaml

# 2. 使用yarn安装
yarn install

# 3. 验证构建
yarn build
```

**风险**: 低 - 两者兼容性好，仅锁文件格式不同

### 2.2 现有依赖兼容性

| 依赖 | 当前版本 | 与SvelteFlow兼容 | 备注 |
|------|----------|------------------|------|
| svelte | ^5.0.0 | ✅ | @xyflow/svelte支持Svelte5 |
| @sveltejs/kit | ^2.9.0 | ✅ | 需配置ssr:false |
| tailwindcss | ^4.1.11 | ✅ | 无冲突 |
| bits-ui | ^2.8.11 | ✅ | shadcn基础 |
| @tauri-apps/api | ^2 | ✅ | 独立运行 |

### 2.3 Tauri Sidecar兼容性

现有Python sidecar架构完全兼容：
- FastAPI已配置CORS
- WebSocket端点可扩展
- 端口动态分配已实现

**需要扩展**:
- 添加流程管理API端点
- 添加任务执行API端点
- 添加WebSocket实时推送

---

## 三、Python工具适配评估

### 3.1 工具调用方式分析

| 工具 | 调用方式 | stdin/stdout | 退出码 | 适配难度 |
|------|----------|--------------|--------|----------|
| repacku | CLI | 有输出 | 标准 | 低 |
| rawfilter | CLI | 有输出 | 标准 | 低 |
| samea | CLI | 有输出 | 标准 | 中(需解析) |
| crashu | CLI | 有输出 | 标准 | 低 |
| migratef | CLI | 有输出 | 标准 | 中(参数多) |
| nameu | CLI | 有输出 | 标准 | 低 |
| formatv | CLI | 有输出 | 标准 | 低 |

### 3.2 适配策略

#### 策略A: subprocess封装 (推荐)
```python
async def execute_tool(cmd: list[str], on_output: callable):
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    async for line in process.stdout:
        await on_output(line.decode())
    return await process.wait()
```

**优点**: 零侵入，工具独立运行  
**缺点**: 依赖CLI输出格式

#### 策略B: Python模块直接导入
```python
from some_tool import main_function
result = await main_function(path="/some/path")
```

**优点**: 更精细的控制  
**缺点**: 需要工具支持作为库导入

**结论**: 优先使用策略A，对于需要深度集成的工具(如samea)可考虑策略B

### 3.3 输出解析评估

| 工具 | 输出格式 | 解析难度 | 建议 |
|------|----------|----------|------|
| repacku | 文本日志 | 低 | 直接透传 |
| samea | 结构化报告 | 中 | JSON输出模式 |
| migratef | 进度+日志 | 中 | 正则解析进度 |
| formatv | ffmpeg输出 | 高 | 解析进度百分比 |

---

## 四、WebSocket实时通信评估

### 4.1 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **FastAPI WebSocket** | 原生支持，简单 | 需手动管理连接 |
| Socket.IO | 自动重连，房间 | 额外依赖 |
| Server-Sent Events | 单向简单 | 不支持双向 |

**选择**: FastAPI原生WebSocket
- 已有FastAPI基础
- 需求简单（任务状态推送）
- 减少依赖

### 4.2 FastAPI WebSocket实现

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        self.active_connections[task_id].add(websocket)
    
    async def broadcast(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/v1/ws/tasks/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # 保持连接
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
```

### 4.3 前端WebSocket封装

```typescript
// src/lib/services/websocket.ts
import { writable } from 'svelte/store';

export function createTaskWebSocket(taskId: string) {
  const messages = writable<TaskEvent[]>([]);
  const status = writable<'connecting' | 'connected' | 'disconnected'>('connecting');
  
  const ws = new WebSocket(`ws://localhost:8009/v1/ws/tasks/${taskId}`);
  
  ws.onopen = () => status.set('connected');
  ws.onclose = () => status.set('disconnected');
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    messages.update(m => [...m, data]);
  };
  
  return {
    messages,
    status,
    close: () => ws.close()
  };
}
```

---

## 五、性能评估

### 5.1 预期性能指标

| 场景 | 目标 | 风险 |
|------|------|------|
| 流程加载 | <100ms | 低 |
| 节点渲染(50个) | <16ms/帧 | 低 |
| 节点渲染(200个) | <33ms/帧 | 中 |
| WebSocket延迟 | <50ms | 低 |
| 日志渲染(1000行) | 流畅滚动 | 中 |

### 5.2 优化策略

#### 前端
- 日志虚拟滚动 (svelte-virtual-list)
- 节点懒加载
- 防抖节点位置更新

#### 后端
- 任务队列 (asyncio.Queue)
- 日志批量推送 (每100ms)
- 连接池管理

---

## 六、安全评估

### 6.1 风险点

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| 命令注入 | 高 | 参数白名单，路径校验 |
| 路径遍历 | 高 | 限制工作目录 |
| WebSocket劫持 | 中 | Origin校验 |
| DoS | 低 | 任务并发限制 |

### 6.2 安全实现

```python
import os
import re

ALLOWED_TOOLS = {"repacku", "samea", "crashu", "migratef", ...}
ALLOWED_PATHS = [r"D:\\", r"E:\\", r"C:\\Users\\"]

def validate_path(path: str) -> bool:
    """验证路径安全性"""
    normalized = os.path.normpath(path)
    return any(normalized.startswith(p) for p in ALLOWED_PATHS)

def validate_tool(tool_name: str) -> bool:
    """验证工具名"""
    return tool_name in ALLOWED_TOOLS and re.match(r'^[a-z]+$', tool_name)
```

---

## 七、评估结论

### 7.1 可行性评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 技术可行性 | 9/10 | 所有技术栈成熟可用 |
| 工作量评估 | 7/10 | 约6-8周开发周期 |
| 风险可控性 | 8/10 | 主要风险已识别并有方案 |
| 扩展性 | 9/10 | 适配器模式支持扩展 |

### 7.2 建议

1. **立即开始**: 技术可行性高，建议立即启动Phase 1
2. **优先验证**: 先实现samea→crashu→migratef工作流验证架构
3. **保守估计**: 预留20%buffer应对未知问题
4. **渐进式迁移**: yarn迁移与功能开发并行

### 7.3 待确认事项

- [ ] 确认现有Python工具的安装路径和环境
- [ ] 确认目标用户是否需要Web独立部署
- [ ] 确认是否需要支持工具参数的持久化配置
