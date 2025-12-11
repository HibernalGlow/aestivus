# AestivalFlow 工具运行时设计

> **版本**: 1.0.0  
> **创建日期**: 2025-12-12  
> **参考**: Airflow, Prefect, Poetry, PDM 等成熟方案

---

## 一、工具环境管理

### 1.1 设计原则

参考业界成熟做法：
- **Poetry/PDM**: 项目级虚拟环境隔离
- **Airflow**: Operator独立运行环境
- **tox**: 多环境测试隔离
- **pipx**: 工具级独立环境

### 1.2 环境模型

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AestivalFlow Runtime                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Environment Manager                        │   │
│  │  • 环境发现 (discover)   • 环境创建 (create)                 │   │
│  │  • 环境激活 (activate)   • 依赖安装 (install)                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│         ┌────────────────────┼────────────────────┐                 │
│         │                    │                    │                 │
│         ▼                    ▼                    ▼                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │  默认环境    │     │  工具独立环境 │     │  全局CLI    │           │
│  │  .venv/     │     │  tools/     │     │  PATH       │           │
│  │             │     │  ├─samea/   │     │             │           │
│  │  pip -e     │     │  │ └─.venv/ │     │  直接调用   │           │
│  │  本地开发包  │     │  ├─crashu/  │     │  命令行工具 │           │
│  │             │     │  │ └─.venv/ │     │             │           │
│  └─────────────┘     │  └─...      │     └─────────────┘           │
│                      └─────────────┘                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 工具配置结构

```toml
# config/tools.toml - 工具配置文件

# 全局默认设置
[defaults]
python = "python"
venv_path = ".venv"
mode = "module"  # module | cli | venv | auto

# 本地开发包 - 直接导入 (推荐)
[tools.samea]
display_name = "相似文件分析"
category = "file"
mode = "module"
package_path = "D:/1VSCODE/Projects/SameA"
entry_module = "samea.cli"
entry_function = "main"

[tools.samea.schema]
path = { type = "string", required = true }
threshold = { type = "float", default = 0.9 }

# 独立venv的工具 (依赖冲突时使用)
[tools.crashu]
display_name = "崩溃文件处理"
category = "file"
mode = "venv"
package_path = "D:/1VSCODE/Projects/CrashU"
venv_path = "tools/crashu/.venv"
entry_cli = "crashu"

# 全局CLI工具
[tools.ffmpeg]
display_name = "FFmpeg"
category = "video"
mode = "cli"
entry_cli = "ffmpeg"
args_style = "gnu"

# 混合模式 - 优先模块导入
[tools.migratef]
display_name = "文件迁移"
category = "file"
mode = "module"
package_path = "D:/1VSCODE/Projects/MigrateF"
entry_module = "migratef.core"
entry_function = "migrate"
entry_cli = "migratef"  # 回退CLI

[tools.migratef.defaults]
target = "E:/1Hub/EH/4EHV/already"
existing_dir = "merge"
```

---

## 二、多兼容模式执行

### 2.1 执行模式

| 模式 | 描述 | 适用场景 | 优先级 |
|------|------|----------|--------|
| `module` | Python模块直接导入 | 本地开发包，需要细粒度控制 | 1 (最高) |
| `venv` | 独立虚拟环境CLI | 依赖冲突的工具 | 2 |
| `cli` | 全局PATH命令 | 系统工具如ffmpeg | 3 |
| `auto` | 自动选择 | 默认模式 | - |

### 2.2 执行器架构

```python
# src-python/core/runtime/executor.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
from pathlib import Path
import asyncio
import importlib
import sys

class ExecutionMode:
    MODULE = "module"
    VENV = "venv"
    CLI = "cli"
    AUTO = "auto"

class BaseExecutor(ABC):
    """执行器基类"""
    
    @abstractmethod
    async def execute(
        self,
        tool_config: Dict,
        input_data: Dict,
        on_output: Optional[Callable] = None,
        on_progress: Optional[Callable] = None
    ) -> Dict:
        pass
    
    @abstractmethod
    def is_available(self, tool_config: Dict) -> bool:
        """检查执行器是否可用"""
        pass


class ModuleExecutor(BaseExecutor):
    """Python模块执行器 - 直接导入执行"""
    
    async def execute(self, tool_config, input_data, on_output=None, on_progress=None):
        entry = tool_config["entry"]
        module_path = entry["module"]
        function_name = entry.get("function", "main")
        
        # 确保包路径在sys.path中
        package_path = tool_config.get("package", {}).get("path")
        if package_path and package_path not in sys.path:
            sys.path.insert(0, package_path)
        
        # 动态导入模块
        module = importlib.import_module(module_path)
        func = getattr(module, function_name)
        
        # 执行（支持同步和异步函数）
        if asyncio.iscoroutinefunction(func):
            result = await func(**input_data, on_output=on_output)
        else:
            result = await asyncio.to_thread(func, **input_data)
        
        return {"success": True, "data": result}
    
    def is_available(self, tool_config):
        try:
            module_path = tool_config["entry"]["module"]
            importlib.import_module(module_path)
            return True
        except ImportError:
            return False


class VenvExecutor(BaseExecutor):
    """独立Venv执行器 - 在隔离环境中运行"""
    
    async def execute(self, tool_config, input_data, on_output=None, on_progress=None):
        venv_path = Path(tool_config["package"]["venv_path"])
        python_exe = venv_path / "Scripts" / "python.exe"  # Windows
        
        cli_cmd = tool_config["entry"]["cli"]
        args = self._build_args(input_data, tool_config)
        
        cmd = [str(python_exe), "-m", cli_cmd] + args
        return await self._run_subprocess(cmd, on_output)
    
    def is_available(self, tool_config):
        venv_path = Path(tool_config["package"]["venv_path"])
        python_exe = venv_path / "Scripts" / "python.exe"
        return python_exe.exists()
    
    async def _run_subprocess(self, cmd, on_output):
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout_lines = []
        async for line in process.stdout:
            text = line.decode().rstrip()
            stdout_lines.append(text)
            if on_output:
                await on_output(text)
        
        await process.wait()
        return {
            "success": process.returncode == 0,
            "output": "\n".join(stdout_lines),
            "returncode": process.returncode
        }
    
    def _build_args(self, input_data, tool_config):
        args = []
        for key, value in input_data.items():
            if value is None:
                continue
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key}")
            else:
                args.extend([f"--{key}", str(value)])
        return args


class CliExecutor(BaseExecutor):
    """全局CLI执行器 - 直接调用PATH中的命令"""
    
    async def execute(self, tool_config, input_data, on_output=None, on_progress=None):
        cli_cmd = tool_config["entry"]["cli"]
        args = self._build_args(input_data, tool_config)
        
        cmd = [cli_cmd] + args
        return await self._run_subprocess(cmd, on_output)
    
    def is_available(self, tool_config):
        import shutil
        cli_cmd = tool_config["entry"]["cli"]
        return shutil.which(cli_cmd) is not None
    
    # _run_subprocess 和 _build_args 同 VenvExecutor


class AutoExecutor(BaseExecutor):
    """自动选择执行器"""
    
    def __init__(self):
        self.executors = [
            (ExecutionMode.MODULE, ModuleExecutor()),
            (ExecutionMode.VENV, VenvExecutor()),
            (ExecutionMode.CLI, CliExecutor()),
        ]
    
    async def execute(self, tool_config, input_data, on_output=None, on_progress=None):
        executor = self._select_executor(tool_config)
        return await executor.execute(tool_config, input_data, on_output, on_progress)
    
    def is_available(self, tool_config):
        return any(e.is_available(tool_config) for _, e in self.executors)
    
    def _select_executor(self, tool_config):
        mode = tool_config.get("mode", ExecutionMode.AUTO)
        
        if mode != ExecutionMode.AUTO:
            # 指定模式
            for m, executor in self.executors:
                if m == mode and executor.is_available(tool_config):
                    return executor
        
        # 自动选择：按优先级尝试
        for _, executor in self.executors:
            if executor.is_available(tool_config):
                return executor
        
        raise RuntimeError(f"No available executor for tool: {tool_config['name']}")
```

### 2.3 环境管理器

```python
# src-python/core/runtime/env_manager.py

from pathlib import Path
import subprocess
import sys
import json

class EnvironmentManager:
    """工具环境管理器"""
    
    def __init__(self, config_path: str = "config/tools.yaml"):
        self.config_path = Path(config_path)
        self.tools_dir = Path("tools")
        self.default_venv = Path(".venv")
        
    def setup_tool(self, tool_name: str, tool_config: dict) -> bool:
        """设置工具环境"""
        mode = tool_config.get("mode", "auto")
        package_config = tool_config.get("package", {})
        
        if package_config.get("venv") == "isolated":
            return self._setup_isolated_venv(tool_name, tool_config)
        elif package_config.get("editable"):
            return self._setup_editable_package(tool_name, tool_config)
        
        return True
    
    def _setup_isolated_venv(self, tool_name: str, tool_config: dict) -> bool:
        """创建独立虚拟环境"""
        venv_path = Path(tool_config["package"]["venv_path"])
        
        if not venv_path.exists():
            print(f"Creating isolated venv for {tool_name} at {venv_path}")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        
        # 安装依赖
        package_path = tool_config["package"]["path"]
        pip_exe = venv_path / "Scripts" / "pip.exe"
        
        if tool_config["package"].get("editable"):
            subprocess.run([str(pip_exe), "install", "-e", package_path], check=True)
        else:
            subprocess.run([str(pip_exe), "install", package_path], check=True)
        
        return True
    
    def _setup_editable_package(self, tool_name: str, tool_config: dict) -> bool:
        """在默认venv中安装editable包"""
        package_path = tool_config["package"]["path"]
        pip_exe = self.default_venv / "Scripts" / "pip.exe"
        
        # 检查是否已安装
        result = subprocess.run(
            [str(pip_exe), "show", tool_name],
            capture_output=True
        )
        
        if result.returncode != 0:
            print(f"Installing {tool_name} in editable mode")
            subprocess.run([str(pip_exe), "install", "-e", package_path], check=True)
        
        return True
    
    def discover_tools(self) -> dict:
        """发现已安装的工具"""
        discovered = {}
        
        # 检查默认venv中的editable包
        pip_exe = self.default_venv / "Scripts" / "pip.exe"
        result = subprocess.run(
            [str(pip_exe), "list", "--editable", "--format=json"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            for pkg in json.loads(result.stdout):
                discovered[pkg["name"]] = {
                    "mode": "module",
                    "location": pkg.get("location", ""),
                    "editable": True
                }
        
        # 检查独立venv
        if self.tools_dir.exists():
            for tool_dir in self.tools_dir.iterdir():
                if (tool_dir / ".venv").exists():
                    discovered[tool_dir.name] = {
                        "mode": "venv",
                        "venv_path": str(tool_dir / ".venv"),
                        "isolated": True
                    }
        
        return discovered
```

---

## 三、参数持久化配置

### 3.1 配置存储结构

```
config/
├── tools.toml              # 工具定义 (静态)
├── defaults.toml           # 工具默认参数 (用户配置)
├── presets/                # 参数预设
│   ├── file_cleanup.json
│   └── video_process.json
└── history/                # 执行历史 (JSON Lines)
    └── 2025-12-12.jsonl
```

### 3.2 参数持久化模型

```python
# src-python/core/config/persistence.py

from pathlib import Path
from typing import Any, Dict, Optional
import tomllib  # Python 3.11+
import tomli_w   # 写入TOML
import json
from datetime import datetime
from pydantic import BaseModel

class ToolDefaults(BaseModel):
    """工具默认参数"""
    tool_name: str
    parameters: Dict[str, Any]
    updated_at: datetime
    
class ParameterPreset(BaseModel):
    """参数预设"""
    name: str
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    created_at: datetime

class ConfigPersistence:
    """配置持久化管理"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.defaults_file = self.config_dir / "tool_defaults.yaml"
        self.presets_dir = self.config_dir / "presets"
        self.presets_dir.mkdir(exist_ok=True)
    
    # === 工具默认参数 ===
    
    def get_tool_defaults(self, tool_name: str) -> Dict[str, Any]:
        """获取工具默认参数"""
        defaults = self._load_defaults()
        return defaults.get(tool_name, {})
    
    def set_tool_defaults(self, tool_name: str, parameters: Dict[str, Any]):
        """保存工具默认参数"""
        defaults = self._load_defaults()
        defaults[tool_name] = {
            "parameters": parameters,
            "updated_at": datetime.now().isoformat()
        }
        self._save_defaults(defaults)
    
    def merge_with_defaults(self, tool_name: str, input_params: Dict) -> Dict:
        """合并输入参数与默认值"""
        defaults = self.get_tool_defaults(tool_name).get("parameters", {})
        return {**defaults, **{k: v for k, v in input_params.items() if v is not None}}
    
    # === 参数预设 ===
    
    def save_preset(self, preset: ParameterPreset):
        """保存参数预设"""
        preset_file = self.presets_dir / f"{preset.name}.yaml"
        with open(preset_file, "w", encoding="utf-8") as f:
            yaml.dump(preset.model_dump(), f, allow_unicode=True)
    
    def load_preset(self, name: str) -> Optional[ParameterPreset]:
        """加载参数预设"""
        preset_file = self.presets_dir / f"{name}.yaml"
        if preset_file.exists():
            with open(preset_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return ParameterPreset(**data)
        return None
    
    def list_presets(self, tool_name: str = None) -> list[ParameterPreset]:
        """列出预设"""
        presets = []
        for f in self.presets_dir.glob("*.yaml"):
            preset = self.load_preset(f.stem)
            if preset and (tool_name is None or preset.tool_name == tool_name):
                presets.append(preset)
        return presets
    
    # === 私有方法 ===
    
    def _load_defaults(self) -> Dict:
        if self.defaults_file.exists():
            with open(self.defaults_file, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _save_defaults(self, defaults: Dict):
        with open(self.defaults_file, "w", encoding="utf-8") as f:
            yaml.dump(defaults, f, allow_unicode=True)
```

### 3.3 执行历史记录

```python
# src-python/core/config/history.py

from pathlib import Path
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import json

class ExecutionRecord(BaseModel):
    """执行记录"""
    id: str
    flow_id: Optional[str]
    tool_name: str
    parameters: dict
    status: str  # success | failed | cancelled
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    output_summary: Optional[str]
    error: Optional[str]

class ExecutionHistory:
    """执行历史管理"""
    
    def __init__(self, history_dir: str = "config/history"):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
    
    def record(self, record: ExecutionRecord):
        """记录执行"""
        date_str = record.started_at.strftime("%Y-%m-%d")
        history_file = self.history_dir / f"{date_str}.jsonl"
        
        with open(history_file, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
    
    def query(
        self,
        tool_name: str = None,
        status: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[ExecutionRecord]:
        """查询执行历史"""
        records = []
        
        for history_file in sorted(self.history_dir.glob("*.jsonl"), reverse=True):
            file_date = datetime.strptime(history_file.stem, "%Y-%m-%d")
            
            if start_date and file_date < start_date.date():
                continue
            if end_date and file_date > end_date.date():
                continue
            
            with open(history_file, encoding="utf-8") as f:
                for line in f:
                    record = ExecutionRecord(**json.loads(line))
                    
                    if tool_name and record.tool_name != tool_name:
                        continue
                    if status and record.status != status:
                        continue
                    
                    records.append(record)
                    if len(records) >= limit:
                        return records
        
        return records
    
    def get_last_parameters(self, tool_name: str) -> Optional[dict]:
        """获取工具最近一次成功执行的参数"""
        records = self.query(tool_name=tool_name, status="success", limit=1)
        return records[0].parameters if records else None
```

---

## 四、后端模块化结构

### 4.1 模块划分

```
src-python/
├── api/                        # API层
│   ├── __init__.py
│   ├── router.py              # 路由聚合
│   ├── flows.py               # 流程API
│   ├── tasks.py               # 任务API
│   ├── tools.py               # 工具API
│   └── websocket.py           # WebSocket
│
├── core/                       # 核心业务层
│   ├── __init__.py
│   ├── runtime/               # 运行时
│   │   ├── __init__.py
│   │   ├── executor.py        # 执行器
│   │   ├── env_manager.py     # 环境管理
│   │   └── process.py         # 进程管理
│   ├── scheduler/             # 调度器
│   │   ├── __init__.py
│   │   ├── task_queue.py      # 任务队列
│   │   └── flow_runner.py     # 流程执行器
│   └── config/                # 配置管理
│       ├── __init__.py
│       ├── persistence.py     # 持久化
│       ├── history.py         # 历史记录
│       └── loader.py          # 配置加载
│
├── adapters/                   # 适配器层
│   ├── __init__.py
│   ├── base.py                # 基类
│   ├── registry.py            # 注册表
│   └── tools/                 # 工具适配器
│       ├── __init__.py
│       ├── samea.py
│       ├── crashu.py
│       ├── migratef.py
│       └── ...
│
├── models/                     # 数据模型
│   ├── __init__.py
│   ├── flow.py
│   ├── task.py
│   └── tool.py
│
├── storage/                    # 存储层
│   ├── __init__.py
│   ├── flows.py               # 流程存储
│   └── base.py                # 存储基类
│
├── main.py                     # 入口
└── requirements.txt
```

### 4.2 依赖注入

```python
# src-python/core/__init__.py

from functools import lru_cache
from .runtime.executor import AutoExecutor
from .runtime.env_manager import EnvironmentManager
from .config.persistence import ConfigPersistence
from .config.history import ExecutionHistory
from .scheduler.flow_runner import FlowRunner

class Container:
    """简单依赖注入容器"""
    
    _instances = {}
    
    @classmethod
    def get_executor(cls) -> AutoExecutor:
        if "executor" not in cls._instances:
            cls._instances["executor"] = AutoExecutor()
        return cls._instances["executor"]
    
    @classmethod
    def get_env_manager(cls) -> EnvironmentManager:
        if "env_manager" not in cls._instances:
            cls._instances["env_manager"] = EnvironmentManager()
        return cls._instances["env_manager"]
    
    @classmethod
    def get_config(cls) -> ConfigPersistence:
        if "config" not in cls._instances:
            cls._instances["config"] = ConfigPersistence()
        return cls._instances["config"]
    
    @classmethod
    def get_history(cls) -> ExecutionHistory:
        if "history" not in cls._instances:
            cls._instances["history"] = ExecutionHistory()
        return cls._instances["history"]
    
    @classmethod
    def get_flow_runner(cls) -> FlowRunner:
        if "flow_runner" not in cls._instances:
            cls._instances["flow_runner"] = FlowRunner(
                executor=cls.get_executor(),
                config=cls.get_config(),
                history=cls.get_history()
            )
        return cls._instances["flow_runner"]
```

---

## 五、API设计补充

### 5.1 工具配置API

```python
# src-python/api/tools.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from core import Container

router = APIRouter(prefix="/tools", tags=["tools"])

class ToolDefaultsUpdate(BaseModel):
    parameters: Dict[str, Any]

class PresetCreate(BaseModel):
    name: str
    description: str
    tool_name: str
    parameters: Dict[str, Any]

# === 工具列表 ===

@router.get("/")
async def list_tools():
    """获取所有可用工具"""
    env_manager = Container.get_env_manager()
    return env_manager.discover_tools()

@router.get("/{tool_name}")
async def get_tool(tool_name: str):
    """获取工具详情"""
    # 包含schema、默认参数、执行模式等
    pass

@router.get("/{tool_name}/schema")
async def get_tool_schema(tool_name: str):
    """获取工具参数Schema"""
    pass

# === 默认参数 ===

@router.get("/{tool_name}/defaults")
async def get_defaults(tool_name: str):
    """获取工具默认参数"""
    config = Container.get_config()
    return config.get_tool_defaults(tool_name)

@router.put("/{tool_name}/defaults")
async def update_defaults(tool_name: str, data: ToolDefaultsUpdate):
    """更新工具默认参数"""
    config = Container.get_config()
    config.set_tool_defaults(tool_name, data.parameters)
    return {"success": True}

# === 参数预设 ===

@router.get("/{tool_name}/presets")
async def list_presets(tool_name: str):
    """获取工具的参数预设"""
    config = Container.get_config()
    return [p.model_dump() for p in config.list_presets(tool_name)]

@router.post("/presets")
async def create_preset(data: PresetCreate):
    """创建参数预设"""
    from core.config.persistence import ParameterPreset
    from datetime import datetime
    
    config = Container.get_config()
    preset = ParameterPreset(
        **data.model_dump(),
        created_at=datetime.now()
    )
    config.save_preset(preset)
    return {"success": True, "name": preset.name}

# === 执行历史 ===

@router.get("/{tool_name}/history")
async def get_history(tool_name: str, limit: int = 20):
    """获取工具执行历史"""
    history = Container.get_history()
    records = history.query(tool_name=tool_name, limit=limit)
    return [r.model_dump() for r in records]

@router.get("/{tool_name}/last-params")
async def get_last_params(tool_name: str):
    """获取最近一次成功执行的参数"""
    history = Container.get_history()
    params = history.get_last_parameters(tool_name)
    return {"parameters": params}

# === 环境管理 ===

@router.post("/{tool_name}/setup")
async def setup_tool_env(tool_name: str):
    """设置工具环境（创建venv、安装依赖）"""
    env_manager = Container.get_env_manager()
    # 从配置加载工具定义
    # success = env_manager.setup_tool(tool_name, tool_config)
    return {"success": True}
```

---

## 六、前端配置面板

### 6.1 参数持久化交互

```svelte
<!-- src/lib/components/nodes/ToolConfigPanel.svelte -->
<script lang="ts">
  import { api } from '$lib/services/api';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Select } from '$lib/components/ui/select';
  
  interface Props {
    toolName: string;
    currentParams: Record<string, any>;
    onUpdate: (params: Record<string, any>) => void;
  }
  
  let { toolName, currentParams, onUpdate }: Props = $props();
  
  let schema = $state<any>(null);
  let defaults = $state<Record<string, any>>({});
  let presets = $state<any[]>([]);
  let lastParams = $state<Record<string, any> | null>(null);
  
  // 加载工具配置
  async function loadToolConfig() {
    const [schemaRes, defaultsRes, presetsRes, lastRes] = await Promise.all([
      api.getToolSchema(toolName),
      api.getToolDefaults(toolName),
      api.getToolPresets(toolName),
      api.getLastParams(toolName)
    ]);
    
    schema = schemaRes;
    defaults = defaultsRes.parameters || {};
    presets = presetsRes;
    lastParams = lastRes.parameters;
  }
  
  // 应用默认参数
  function applyDefaults() {
    onUpdate({ ...currentParams, ...defaults });
  }
  
  // 应用预设
  function applyPreset(preset: any) {
    onUpdate({ ...currentParams, ...preset.parameters });
  }
  
  // 应用上次参数
  function applyLastParams() {
    if (lastParams) {
      onUpdate({ ...currentParams, ...lastParams });
    }
  }
  
  // 保存为默认
  async function saveAsDefault() {
    await api.updateToolDefaults(toolName, currentParams);
    defaults = currentParams;
  }
  
  // 保存为预设
  async function saveAsPreset(name: string) {
    await api.createPreset({
      name,
      description: '',
      tool_name: toolName,
      parameters: currentParams
    });
    presets = await api.getToolPresets(toolName);
  }
  
  $effect(() => {
    loadToolConfig();
  });
</script>

<div class="p-4 space-y-4">
  <div class="flex gap-2">
    <Button size="sm" variant="outline" onclick={applyDefaults}>
      应用默认值
    </Button>
    <Button size="sm" variant="outline" onclick={applyLastParams} disabled={!lastParams}>
      上次参数
    </Button>
    <Button size="sm" variant="outline" onclick={saveAsDefault}>
      保存为默认
    </Button>
  </div>
  
  {#if presets.length > 0}
    <div class="space-y-2">
      <label class="text-sm font-medium">预设</label>
      <Select onchange={(e) => applyPreset(presets.find(p => p.name === e.target.value))}>
        <option value="">选择预设...</option>
        {#each presets as preset}
          <option value={preset.name}>{preset.name}</option>
        {/each}
      </Select>
    </div>
  {/if}
  
  <!-- 动态参数表单 -->
  {#if schema}
    {#each Object.entries(schema.properties || {}) as [key, prop]}
      <div class="space-y-1">
        <label class="text-sm font-medium">{prop.title || key}</label>
        <Input
          type={prop.type === 'number' ? 'number' : 'text'}
          value={currentParams[key] ?? defaults[key] ?? prop.default}
          onchange={(e) => onUpdate({ ...currentParams, [key]: e.target.value })}
          placeholder={prop.description}
        />
      </div>
    {/each}
  {/if}
</div>
```

---

## 七、总结

### 设计要点

1. **多兼容执行模式**: Module > Venv > CLI，自动选择最优
2. **独立venv支持**: 依赖冲突工具可隔离运行
3. **pip -e模式**: 本地开发包默认editable安装
4. **参数持久化**: 默认值、预设、历史记录三层配置
5. **后端模块化**: 清晰的分层架构，依赖注入

### 参考业界实践

| 功能 | 参考 |
|------|------|
| 环境隔离 | Poetry, PDM, pipx |
| 多执行模式 | Airflow Operators |
| 参数持久化 | n8n, Node-RED |
| 配置管理 | Prefect, Dagster |
