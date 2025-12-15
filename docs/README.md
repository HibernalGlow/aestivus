# aestival 文档中心

> Python工具链可视化编排与执行平台

---

## 📚 文档索引

| 文档 | 描述 |
|------|------|
| [DESIGN.md](./DESIGN.md) | **项目设计文档** - 完整的系统架构、模块设计、API设计 |
| [TOOL_RUNTIME.md](./TOOL_RUNTIME.md) | **工具运行时设计** - 多兼容执行、独立venv、参数持久化 |
| [TECH_EVALUATION.md](./TECH_EVALUATION.md) | **技术评估报告** - SvelteFlow评估、兼容性分析、风险评估 |
| [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) | **实施指南** - 分步骤实施说明、代码示例 |
| [TODO.md](./TODO.md) | **开发待办清单** - 按阶段划分的任务列表 |

---

## 🎯 项目概述

### 核心价值
将现有的Python命令行工具（repacku, samea, crashu, migratef等）封装为可视化节点，通过拖拽式界面编排工作流程，实时监控执行状态。

### 核心特性
- **多兼容执行**: Module导入 > 独立Venv > 全局CLI，自动选择最优
- **独立环境**: 每个工具可配置独立venv，避免依赖冲突
- **pip -e支持**: 本地开发包默认editable安装
- **参数持久化**: 默认值、预设、执行历史自动保存

### 技术栈
```
前端: SvelteKit 5 + SvelteFlow + shadcn/svelte + Tailwind CSS 4
后端: FastAPI + WebSocket + asyncio (模块化架构)
桌面: Tauri 2
包管理: yarn
参考: Airflow, Prefect, Poetry 等成熟方案
```

### 目标工具

| 类别 | 工具 |
|------|------|
| 文件处理 | repacku, rawfilter, samea, crashu, migratef, nameu, cleanf |
| 视频处理 | formatv, brakev |
| 其他 | psdc, synct, linku, lata |

---

## 🚀 快速开始

```bash
# 1. 安装依赖
yarn install
pip install -r src-python/requirements.txt

# 2. 开发模式
yarn tauri dev        # Tauri桌面开发
yarn dev:standalone   # 纯Web开发

# 3. 生产构建
yarn build
python build.py
```

---

## 📊 项目进度

| 阶段 | 状态 | 说明 |
|------|------|------|
| Phase 1: 基础框架 | 🟡 设计完成 | SvelteFlow集成、状态管理 |
| Phase 2: 工具集成 | ⚪ 待开始 | 适配器、执行引擎 |
| Phase 3: UI完善 | ⚪ 待开始 | 配置面板、日志查看器 |
| Phase 4: 扩展功能 | ⚪ 待开始 | 高级节点、Web兼容 |

---

## 🔗 相关资源

- [SvelteFlow文档](https://svelteflow.dev/)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Tauri文档](https://tauri.app/)
- [shadcn/svelte](https://www.shadcn-svelte.com/)
