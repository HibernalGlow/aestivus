"""
节点管理 API
提供节点类型列表和参数 Schema 查询
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

from adapters import get_adapter, list_adapters, get_adapter_names

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("/types", response_model=List[Dict[str, Any]])
async def get_node_types():
    """
    获取所有可用的节点类型列表
    
    Returns:
        节点类型信息列表，包含名称、显示名称、描述、图标等
    """
    return list_adapters()


@router.get("/types/{name}")
async def get_node_type_info(name: str):
    """
    获取指定节点类型的详细信息
    
    Args:
        name: 节点类型名称
        
    Returns:
        节点类型详细信息
    """
    try:
        adapter = get_adapter(name)
        return adapter.get_info()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"适配器加载失败: {str(e)}")


@router.get("/types/{name}/schema")
async def get_node_type_schema(name: str):
    """
    获取指定节点类型的输入参数 Schema
    
    Args:
        name: 节点类型名称
        
    Returns:
        JSON Schema 格式的参数定义
    """
    try:
        adapter = get_adapter(name)
        return {
            "inputSchema": adapter.get_schema(),
            "outputSchema": adapter.get_output_schema()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"适配器加载失败: {str(e)}")


@router.get("/names")
async def get_node_names():
    """
    获取所有已注册的节点类型名称
    
    Returns:
        节点类型名称列表
    """
    return get_adapter_names()
