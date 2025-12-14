"""
属性测试：拓扑执行顺序
**Feature: pywebview-migration, Property 10: 拓扑执行顺序**
**Validates: Requirements 9.3**

测试拓扑排序算法确保节点按正确顺序执行：
- 所有上游节点必须在下游节点之前执行
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import List, Tuple, Set

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.execution import topological_sort, FlowNode, FlowEdge


# ============ 策略定义 ============

@st.composite
def valid_dag_strategy(draw):
    """
    生成有效的有向无环图 (DAG)
    
    返回: (nodes, edges) 元组
    """
    # 生成 1-10 个节点
    num_nodes = draw(st.integers(min_value=1, max_value=10))
    node_ids = [f"node_{i}" for i in range(num_nodes)]
    
    # 创建节点
    nodes = [
        FlowNode(id=node_id, type="repacku", config={"path": f"/test/{node_id}"})
        for node_id in node_ids
    ]
    
    # 生成边（只允许从低索引指向高索引，确保无环）
    edges = []
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            # 随机决定是否添加边
            if draw(st.booleans()):
                edges.append(FlowEdge(source=node_ids[i], target=node_ids[j]))
    
    return nodes, edges


@st.composite
def cyclic_graph_strategy(draw):
    """
    生成包含循环的图
    
    返回: (nodes, edges) 元组
    """
    # 至少需要 2 个节点才能形成循环
    num_nodes = draw(st.integers(min_value=2, max_value=5))
    node_ids = [f"node_{i}" for i in range(num_nodes)]
    
    nodes = [
        FlowNode(id=node_id, type="repacku", config={"path": f"/test/{node_id}"})
        for node_id in node_ids
    ]
    
    # 创建一个简单的循环: node_0 -> node_1 -> ... -> node_n -> node_0
    edges = []
    for i in range(num_nodes):
        next_idx = (i + 1) % num_nodes
        edges.append(FlowEdge(source=node_ids[i], target=node_ids[next_idx]))
    
    return nodes, edges


# ============ 属性测试 ============

@given(valid_dag_strategy())
@settings(max_examples=100)
def test_topological_order_respects_dependencies(dag):
    """
    **Property 10: 拓扑执行顺序**
    
    *For any* 包含多个连接节点的流程执行，节点 SHALL 按拓扑排序顺序执行，
    即所有上游节点完成后才执行下游节点。
    """
    nodes, edges = dag
    
    # 执行拓扑排序
    result = topological_sort(nodes, edges)
    
    # 验证结果包含所有节点
    assert len(result) == len(nodes)
    assert set(result) == {node.id for node in nodes}
    
    # 验证拓扑顺序：对于每条边 (source -> target)，source 必须在 target 之前
    position = {node_id: idx for idx, node_id in enumerate(result)}
    
    for edge in edges:
        source_pos = position[edge.source]
        target_pos = position[edge.target]
        assert source_pos < target_pos, (
            f"拓扑顺序错误: {edge.source} (位置 {source_pos}) "
            f"应该在 {edge.target} (位置 {target_pos}) 之前"
        )


@given(cyclic_graph_strategy())
@settings(max_examples=50)
def test_cyclic_graph_raises_error(cyclic_dag):
    """
    测试循环依赖检测
    
    *For any* 包含循环的图，拓扑排序 SHALL 抛出 ValueError
    """
    nodes, edges = cyclic_dag
    
    with pytest.raises(ValueError, match="循环依赖"):
        topological_sort(nodes, edges)


@given(st.lists(st.text(min_size=1, max_size=10, alphabet="abcdefghij"), min_size=1, max_size=10, unique=True))
@settings(max_examples=50)
def test_single_nodes_no_edges(node_ids):
    """
    测试无边图的拓扑排序
    
    *For any* 没有边的节点集合，拓扑排序 SHALL 返回所有节点（顺序任意）
    """
    nodes = [
        FlowNode(id=node_id, type="repacku", config={"path": f"/test/{node_id}"})
        for node_id in node_ids
    ]
    edges = []
    
    result = topological_sort(nodes, edges)
    
    # 验证结果包含所有节点
    assert len(result) == len(nodes)
    assert set(result) == set(node_ids)


def test_empty_graph():
    """测试空图"""
    result = topological_sort([], [])
    assert result == []


def test_linear_chain():
    """测试线性链: A -> B -> C"""
    nodes = [
        FlowNode(id="A", type="repacku", config={}),
        FlowNode(id="B", type="repacku", config={}),
        FlowNode(id="C", type="repacku", config={}),
    ]
    edges = [
        FlowEdge(source="A", target="B"),
        FlowEdge(source="B", target="C"),
    ]
    
    result = topological_sort(nodes, edges)
    
    assert result == ["A", "B", "C"]


def test_diamond_graph():
    """
    测试菱形图:
        A
       / \
      B   C
       \ /
        D
    """
    nodes = [
        FlowNode(id="A", type="repacku", config={}),
        FlowNode(id="B", type="repacku", config={}),
        FlowNode(id="C", type="repacku", config={}),
        FlowNode(id="D", type="repacku", config={}),
    ]
    edges = [
        FlowEdge(source="A", target="B"),
        FlowEdge(source="A", target="C"),
        FlowEdge(source="B", target="D"),
        FlowEdge(source="C", target="D"),
    ]
    
    result = topological_sort(nodes, edges)
    
    # A 必须第一个，D 必须最后一个
    assert result[0] == "A"
    assert result[-1] == "D"
    # B 和 C 必须在 A 之后，D 之前
    assert result.index("B") > result.index("A")
    assert result.index("C") > result.index("A")
    assert result.index("B") < result.index("D")
    assert result.index("C") < result.index("D")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
