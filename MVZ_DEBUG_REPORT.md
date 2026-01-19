# MVZ 节点 404 错误诊断报告

## 问题现象
用户执行 mvz 节点时收到以下错误：
```
❌ 失败: Error: API Error: 404 Not Found
📡 WebSocket 已连接
[0] INFO: 127.0.0.1:58009 - "POST /v1/execute/node HTTP/1.1" 404 Not Found
```

## 诊断过程

### 第一步：验证路由配置
✅ **结果**：路由配置正确
- `main.py` 第 72 行正确挂载了 `execution_router`
- 完整路由路径：`/v1/execute/node`
- FastAPI 应用正确配置了 CORS

### 第二步：验证适配器注册
✅ **结果**：适配器注册正确
- `adapters/__init__.py` 中 mvz 已添加到 `_ADAPTER_REGISTRY`
- 适配器可以正常导入：`from adapters.mvz_adapter import MvzAdapter`
- 适配器实例化成功

### 第三步：测试 API 端点
❌ **发现问题**：Pydantic 验证错误
```
ValidationError: 1 validation error for MvzInput
path
  Field required [type=missing, input_value={...}]
```

## 根本原因

`MvzInput` 继承自 `AdapterInput` 基类：

```python
# adapters/base.py
class AdapterInput(BaseModel):
    """适配器输入基类"""
    path: str = Field(..., description="输入路径")  # 必需字段
```

但 mvz 节点使用 `files` 列表而不是单个 `path` 字段，导致验证失败。

## 解决方案

### 修改 MvzInput 类
**文件**: `aestivus/src-python/adapters/mvz_adapter.py`

覆盖基类的 `path` 字段，使其可选：

```python
class MvzInput(AdapterInput):
    """mvz 输入参数"""
    # 覆盖基类的 path 字段，使其可选（mvz 使用 files 列表）
    path: str = Field(default="", description="输入路径（可选，mvz 使用 files 列表）")
    action: str = Field(default="extract", description="操作类型: delete/extract/move/rename")
    files: List[str] = Field(default_factory=list, description="文件列表（archive//internal 格式）")
    # ... 其他字段保持不变
```

### 添加调试日志
**文件**: `aestivus/src-python/api/execution.py`

在 `execute_node` 函数中添加详细的调试日志：
- 记录请求信息（node_type、task_id、node_id）
- 记录适配器获取过程
- 记录输入数据构建过程
- 记录异常堆栈跟踪

## 验证结果

### 测试执行
```
[TEST] 开始测试 mvz 端点...
[TEST] ✓ mvz 适配器获取成功
[TEST] ✓ 输入数据构建成功
[TEST] ✓ 响应: success=False message='提取完成: 成功 0 个，失败 1 个'
```

✅ 404 错误已解决
✅ API 端点可以正常接收和处理请求
✅ 错误信息现在是预期的业务逻辑错误（文件不存在）

### 代码质量检查
✅ mvz_adapter.py: 602 行（在 800 行限制内）
✅ execution.py: 328 行（在 800 行限制内）
✅ 无语法错误或类型错误
✅ yarn check 通过

## 修改文件清单

| 文件 | 修改内容 | 行数 |
|------|--------|------|
| `aestivus/src-python/adapters/mvz_adapter.py` | 添加 path 字段覆盖 | 602 |
| `aestivus/src-python/api/execution.py` | 添加调试日志 | 328 |

## 后续建议

1. **考虑重构 AdapterInput 基类**
   - 使 `path` 字段可选（默认值为空字符串）
   - 这样其他不需要 path 的适配器也不需要特殊处理

2. **增加单元测试**
   - 为每个适配器的输入验证添加测试
   - 测试 API 端点的请求/响应

3. **改进错误处理**
   - 在 Pydantic 验证失败时返回更清晰的错误信息
   - 区分 404（路由不存在）和 400（请求参数错误）

## 总结

问题的根本原因是 Pydantic 模型的字段继承问题，而不是 API 路由或适配器注册问题。通过覆盖基类的 `path` 字段使其可选，问题得到完全解决。
