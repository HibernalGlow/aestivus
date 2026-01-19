# MVZ 节点 404 错误修复总结

## 问题描述
用户在执行 mvz 节点时收到 404 错误：
```
❌ 失败: Error: API Error: 404 Not Found
```

## 根本原因分析

### 初步调查
1. **路由配置检查**：验证了 FastAPI 路由正确挂载
   - `main.py` 第 72 行正确包含了 `execution_router`
   - 路由前缀配置正确：`/v1/execute/node`

2. **适配器注册检查**：验证了 mvz 适配器已正确注册
   - `adapters/__init__.py` 中 mvz 已添加到 `_ADAPTER_REGISTRY`
   - 适配器可以正常导入和实例化

3. **真正的问题**：通过测试脚本发现了实际错误
   - 错误信息：`1 validation error for MvzInput: path - Field required`
   - 原因：`MvzInput` 继承自 `AdapterInput`，而 `AdapterInput` 基类要求 `path` 字段
   - 但 mvz 节点使用 `files` 列表而不是单个 `path` 字段

## 解决方案

### 修改文件
**文件**: `aestivus/src-python/adapters/mvz_adapter.py`

**修改内容**：
```python
# 修改前
class MvzInput(AdapterInput):
    """mvz 输入参数"""
    action: str = Field(default="extract", description="操作类型: delete/extract/move/rename")
    files: List[str] = Field(default_factory=list, description="文件列表（archive//internal 格式）")
    # ... 其他字段

# 修改后
class MvzInput(AdapterInput):
    """mvz 输入参数"""
    # 覆盖基类的 path 字段，使其可选（mvz 使用 files 列表）
    path: str = Field(default="", description="输入路径（可选，mvz 使用 files 列表）")
    action: str = Field(default="extract", description="操作类型: delete/extract/move/rename")
    files: List[str] = Field(default_factory=list, description="文件列表（archive//internal 格式）")
    # ... 其他字段
```

### 添加调试日志
**文件**: `aestivus/src-python/api/execution.py`

在 `execute_node` 函数中添加详细的调试日志，便于未来诊断类似问题：
- 记录请求信息（node_type、task_id、node_id）
- 记录适配器获取过程
- 记录输入数据构建过程
- 记录异常堆栈跟踪

## 验证结果

### 测试结果
✅ 适配器导入成功
✅ API 端点可以正常接收请求
✅ 输入验证通过
✅ 404 错误已解决

### 代码质量检查
✅ mvz_adapter.py: 602 行（在 800 行限制内）
✅ execution.py: 328 行（在 800 行限制内）
✅ 无语法错误或类型错误

## 关键学习点

1. **Pydantic 字段继承**：子类继承父类的必需字段，需要显式覆盖才能改变其必需性
2. **API 错误诊断**：404 错误可能来自多个原因，需要逐层排查
3. **调试日志的重要性**：详细的日志可以大大加快问题诊断速度

## 后续建议

1. 考虑为其他不需要 `path` 字段的适配器也进行类似的修改
2. 在 `AdapterInput` 基类中考虑使 `path` 字段可选
3. 增加更多的单元测试来覆盖适配器的输入验证
