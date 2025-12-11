"""
工具管理API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

router = APIRouter(prefix="/tools", tags=["tools"])

# 配置目录
CONFIG_DIR = Path("config")
DEFAULTS_FILE = CONFIG_DIR / "defaults.json"
PRESETS_DIR = CONFIG_DIR / "presets"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
PRESETS_DIR.mkdir(parents=True, exist_ok=True)


# 工具定义 (后续从TOML配置加载)
TOOLS = {
    "repacku": {
        "name": "repacku",
        "displayName": "Repacku",
        "description": "文件重打包工具",
        "category": "file",
        "schema": {
            "path": {"type": "string", "required": True, "description": "输入路径"}
        }
    },
    "samea": {
        "name": "samea",
        "displayName": "Samea",
        "description": "相似文件分析",
        "category": "file",
        "schema": {
            "path": {"type": "string", "required": True, "description": "输入路径"},
            "threshold": {"type": "number", "default": 0.9, "description": "相似度阈值"},
            "method": {"type": "string", "default": "hash", "enum": ["hash", "pixel"], "description": "比较方法"}
        }
    },
    "crashu": {
        "name": "crashu",
        "displayName": "Crashu",
        "description": "崩溃文件处理",
        "category": "file",
        "schema": {
            "path": {"type": "string", "required": True, "description": "输入路径"}
        }
    },
    "migratef": {
        "name": "migratef",
        "displayName": "Migratef",
        "description": "文件迁移工具",
        "category": "file",
        "schema": {
            "path": {"type": "string", "required": True, "description": "输入路径"},
            "target": {"type": "string", "required": True, "description": "目标路径"},
            "mode": {"type": "string", "default": "move", "enum": ["copy", "move"], "description": "迁移模式"},
            "existing_dir": {"type": "string", "default": "merge", "enum": ["skip", "merge", "replace"], "description": "已存在目录处理"}
        }
    },
    "nameu": {
        "name": "nameu",
        "displayName": "Nameu",
        "description": "文件命名工具",
        "category": "file",
        "schema": {
            "path": {"type": "string", "required": True, "description": "输入路径"}
        }
    },
    "formatv": {
        "name": "formatv",
        "displayName": "Formatv",
        "description": "视频格式化",
        "category": "video",
        "schema": {
            "path": {"type": "string", "required": True, "description": "输入路径"}
        }
    }
}


class ToolDefaultsUpdate(BaseModel):
    parameters: Dict[str, Any]


class PresetCreate(BaseModel):
    name: str
    description: str = ""
    tool_name: str
    parameters: Dict[str, Any]


def _load_defaults() -> Dict:
    if DEFAULTS_FILE.exists():
        with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_defaults(defaults: Dict):
    with open(DEFAULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(defaults, f, ensure_ascii=False, indent=2)


@router.get("/")
async def list_tools():
    """获取所有可用工具"""
    return list(TOOLS.values())


@router.get("/{tool_name}")
async def get_tool(tool_name: str):
    """获取工具详情"""
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
    return TOOLS[tool_name]


@router.get("/{tool_name}/schema")
async def get_tool_schema(tool_name: str):
    """获取工具参数Schema"""
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
    return TOOLS[tool_name].get("schema", {})


@router.get("/{tool_name}/defaults")
async def get_tool_defaults(tool_name: str):
    """获取工具默认参数"""
    defaults = _load_defaults()
    return {"parameters": defaults.get(tool_name, {})}


@router.put("/{tool_name}/defaults")
async def update_tool_defaults(tool_name: str, data: ToolDefaultsUpdate):
    """更新工具默认参数"""
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
    
    defaults = _load_defaults()
    defaults[tool_name] = data.parameters
    _save_defaults(defaults)
    return {"success": True}


@router.get("/{tool_name}/presets")
async def list_tool_presets(tool_name: str):
    """获取工具的参数预设"""
    presets = []
    for path in PRESETS_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                preset = json.load(f)
                if preset.get("tool_name") == tool_name:
                    presets.append(preset)
        except:
            pass
    return presets


@router.post("/presets")
async def create_preset(data: PresetCreate):
    """创建参数预设"""
    if data.tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail=f"Tool {data.tool_name} not found")
    
    preset_path = PRESETS_DIR / f"{data.name}.json"
    preset_data = {
        "name": data.name,
        "description": data.description,
        "tool_name": data.tool_name,
        "parameters": data.parameters
    }
    
    with open(preset_path, "w", encoding="utf-8") as f:
        json.dump(preset_data, f, ensure_ascii=False, indent=2)
    
    return {"success": True, "name": data.name}


@router.get("/{tool_name}/last-params")
async def get_last_params(tool_name: str):
    """获取最近一次成功执行的参数"""
    # TODO: 从执行历史中获取
    return {"parameters": None}
