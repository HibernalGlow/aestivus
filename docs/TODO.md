# aestival 开发待办清单

> **最后更新**: 2025-12-12

---

## Phase 1: 基础框架 (Week 1-2)

### 环境配置
- [ ] 迁移pnpm到yarn
- [ ] 安装@xyflow/svelte
- [ ] 配置SSR禁用
- [ ] 创建目录结构

### SvelteFlow集成
- [ ] 创建FlowCanvas组件
- [ ] 实现节点拖拽
- [ ] 实现边连接
- [ ] 添加MiniMap/Controls/Background

### 状态管理
- [ ] flowStore - 流程状态
- [ ] taskStore - 任务状态
- [ ] nodeStore - 节点注册

### 基础节点
- [ ] InputNode - 输入节点基类
- [ ] ToolNode - 工具节点基类
- [ ] OutputNode - 输出节点基类

### 流程持久化
- [ ] 流程保存API
- [ ] 流程加载API
- [ ] 本地JSON存储

---

## Phase 2: 工具运行时 (Week 3-4)

### 多兼容执行模式
- [ ] ModuleExecutor - Python模块直接导入
- [ ] VenvExecutor - 独立虚拟环境执行
- [ ] CliExecutor - 全局CLI命令执行
- [ ] AutoExecutor - 自动选择最优模式

### 环境管理
- [ ] EnvironmentManager实现
- [ ] 独立venv创建与管理
- [ ] pip -e editable包安装
- [ ] 工具发现与注册

### 适配器框架
- [ ] BaseAdapter基类
- [ ] 适配器注册表
- [ ] 工具Schema生成

### 核心工具适配器
- [ ] samea_adapter (优先)
- [ ] crashu_adapter
- [ ] migratef_adapter
- [ ] repacku_adapter
- [ ] nameu_adapter

### 任务执行引擎
- [ ] FlowExecutor实现
- [ ] 拓扑排序
- [ ] 节点输入传递
- [ ] 错误处理

### WebSocket通信
- [ ] ConnectionManager
- [ ] 任务状态广播
- [ ] 节点状态广播
- [ ] 日志实时推送

---

## Phase 3: UI与配置 (Week 5-6)

### 参数持久化
- [ ] ConfigPersistence - 配置持久化管理
- [ ] 工具默认参数保存/加载
- [ ] 参数预设(Presets)管理
- [ ] ExecutionHistory - 执行历史记录
- [ ] 最近参数快速应用

### 节点配置
- [ ] NodeConfigPanel组件
- [ ] 动态表单生成(基于Schema)
- [ ] 参数验证
- [ ] 预设选择下拉框
- [ ] "保存为默认"按钮

### 执行监控
- [ ] LogViewer组件
- [ ] TaskProgress组件
- [ ] ExecutionHistory组件

### 输入模块
- [ ] ClipboardInput组件
- [ ] PathInput组件(支持拖拽)
- [ ] FolderPicker组件
- [ ] FilePicker组件

### 流程管理
- [ ] 流程列表页
- [ ] 流程模板
- [ ] 流程复制/删除

---

## Phase 4: 扩展功能 (Week 7-8)

### 剩余工具适配器
- [ ] formatv_adapter
- [ ] brakev_adapter
- [ ] psdc_adapter
- [ ] cleanf_adapter
- [ ] linku_adapter
- [ ] rawfilter_adapter

### 高级节点
- [ ] ConditionNode - 条件分支
- [ ] LoopNode - 循环处理
- [ ] MergeNode - 合并输入
- [ ] DelayNode - 延迟执行

### 工具管理UI
- [ ] 工具列表页面
- [ ] 环境状态显示
- [ ] 一键安装/更新工具
- [ ] venv管理界面

### 文档与测试
- [ ] API文档
- [ ] 用户指南
- [ ] 单元测试
- [ ] E2E测试

---

## 里程碑检查点

| 里程碑 | 目标 | 验收标准 |
|--------|------|----------|
| **M1** | 可运行的流程编排界面 | 能拖拽节点、连线、保存流程 |
| **M2** | 单工具执行与日志 | samea能执行并显示实时日志 |
| **M3** | 完整工作流 | samea→crashu→migratef流程可执行 |
| **M4** | 生产可用 | 所有工具集成，UI完善，无重大bug |

---

## 技术债务

- [ ] 日志虚拟滚动优化
- [ ] 大流程性能优化
- [ ] 错误重试机制
- [ ] 国际化支持
