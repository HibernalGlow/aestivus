"""
属性测试：流程序列化 Round-trip
**Feature: pywebview-migration, Property 12: 流程序列化 Round-trip**
**Validates: Requirements 10.2**

测试流程保存和加载的一致性：
- 保存为 JSON 后再加载应恢复完全相同的节点、连接和配置
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from typing import List, Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.flows import Flow, FlowNode, FlowEdge, _save_flow, _load_flow, FLOWS_DIR


# ============ 策略定义 ============

# 简单的字符串策略（避免特殊字符）
simple_text = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
    min_size=1,
    max_size=20
)

# 位置策略
position_strategy = st.fixed_dictionaries({
    "x": st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
    "y": st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)
})

# 简单配置策略
simple_config = st.fixed_dictionaries({
    "path": simple_text,
})


@st.composite
def flow_node_strategy(draw, node_id=None):
    """生成有效的 FlowNode"""
    config = draw(simple_config)
    status = draw(st.sampled_from(["idle", "running", "completed", "error"]))
    
    return FlowNode(
        id=node_id or draw(simple_text),
        type=draw(st.sampled_from(["repacku", "rawfilter", "crashu"])),
        position=draw(position_strategy),
        data={
            "config": config,
            "status": status
        }
    )


@st.composite
def flow_strategy(draw):
    """生成有效的 Flow"""
    # 生成 0-5 个节点
    num_nodes = draw(st.integers(min_value=0, max_value=5))
    node_ids = [f"node_{i}" for i in range(num_nodes)]
    
    nodes = []
    for node_id in node_ids:
        nodes.append(draw(flow_node_strategy(node_id=node_id)))
    
    # 生成边（只在有多个节点时）
    edges = []
    if num_nodes >= 2:
        for i in range(num_nodes):
            for j in range(i + 1, num_nodes):
                if draw(st.booleans()):
                    edges.append(FlowEdge(
                        id=f"edge_{i}_{j}",
                        source=node_ids[i],
                        target=node_ids[j],
                        sourceHandle=None,
                        targetHandle=None,
                        animated=draw(st.booleans())
                    ))
    
    return Flow(
        id=draw(simple_text),
        name=draw(simple_text),
        description=draw(st.text(max_size=100)),
        nodes=nodes,
        edges=edges,
        createdAt="2024-01-01T00:00:00",
        updatedAt="2024-01-01T00:00:00"
    )


# ============ 属性测试 ============

@given(flow_strategy())
@settings(max_examples=50, deadline=None)
def test_flow_serialization_roundtrip(flow):
    """
    **Property 12: 流程序列化 Round-trip**
    
    *For any* 有效的流程状态，保存为 JSON 后再加载 SHALL 恢复完全相同的节点、连接和配置。
    """
    # 确保测试目录存在
    FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # 保存流程
        _save_flow(flow)
        
        # 加载流程
        loaded_flow = _load_flow(flow.id)
        
        # 验证基本属性
        assert loaded_flow.id == flow.id
        assert loaded_flow.name == flow.name
        assert loaded_flow.description == flow.description
        assert loaded_flow.createdAt == flow.createdAt
        assert loaded_flow.updatedAt == flow.updatedAt
        
        # 验证节点数量
        assert len(loaded_flow.nodes) == len(flow.nodes)
        
        # 验证每个节点
        original_nodes = {n.id: n for n in flow.nodes}
        loaded_nodes = {n.id: n for n in loaded_flow.nodes}
        
        for node_id, original_node in original_nodes.items():
            assert node_id in loaded_nodes, f"节点 {node_id} 丢失"
            loaded_node = loaded_nodes[node_id]
            
            assert loaded_node.type == original_node.type
            assert loaded_node.position == original_node.position
            assert loaded_node.data == original_node.data
        
        # 验证边数量
        assert len(loaded_flow.edges) == len(flow.edges)
        
        # 验证每条边
        original_edges = {e.id: e for e in flow.edges}
        loaded_edges = {e.id: e for e in loaded_flow.edges}
        
        for edge_id, original_edge in original_edges.items():
            assert edge_id in loaded_edges, f"边 {edge_id} 丢失"
            loaded_edge = loaded_edges[edge_id]
            
            assert loaded_edge.source == original_edge.source
            assert loaded_edge.target == original_edge.target
            assert loaded_edge.animated == original_edge.animated
            
    finally:
        # 清理测试文件
        flow_path = FLOWS_DIR / f"{flow.id}.json"
        if flow_path.exists():
            flow_path.unlink()


def test_flow_json_structure():
    """测试 JSON 结构正确性"""
    flow = Flow(
        id="test-flow-1",
        name="Test Flow",
        description="A test flow",
        nodes=[
            FlowNode(
                id="node1",
                type="repacku",
                position={"x": 100, "y": 200},
                data={"config": {"path": "/test"}, "status": "idle"}
            )
        ],
        edges=[],
        createdAt="2024-01-01T00:00:00",
        updatedAt="2024-01-01T00:00:00"
    )
    
    FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        _save_flow(flow)
        
        # 直接读取 JSON 文件验证结构
        flow_path = FLOWS_DIR / f"{flow.id}.json"
        with open(flow_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert "id" in data
        assert "name" in data
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
        
    finally:
        flow_path = FLOWS_DIR / f"{flow.id}.json"
        if flow_path.exists():
            flow_path.unlink()


def test_empty_flow_roundtrip():
    """测试空流程的 round-trip"""
    flow = Flow(
        id="empty-flow",
        name="Empty",
        description="",
        nodes=[],
        edges=[],
        createdAt="2024-01-01T00:00:00",
        updatedAt="2024-01-01T00:00:00"
    )
    
    FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        _save_flow(flow)
        loaded = _load_flow(flow.id)
        
        assert loaded.id == flow.id
        assert loaded.nodes == []
        assert loaded.edges == []
        
    finally:
        flow_path = FLOWS_DIR / f"{flow.id}.json"
        if flow_path.exists():
            flow_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
