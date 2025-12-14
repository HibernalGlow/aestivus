"""
属性测试：无效流程文件容错
**Feature: pywebview-migration, Property 13: 无效流程文件容错**
**Validates: Requirements 10.4**

测试加载无效流程文件时的错误处理：
- 格式无效的 JSON 文件应返回错误而非导致应用崩溃
"""

import pytest
import json
from pathlib import Path
from hypothesis import given, strategies as st, settings
from fastapi import HTTPException
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.flows import FLOWS_DIR, _load_flow
from main import app


# ============ 策略定义 ============

# 无效 JSON 字符串策略
invalid_json_strategy = st.one_of(
    # 不完整的 JSON
    st.just("{"),
    st.just("["),
    st.just('{"name":'),
    st.just('{"nodes": [}'),
    # 完全无效的内容
    st.text(min_size=1, max_size=100).filter(lambda x: not x.strip().startswith("{")),
    # 空内容
    st.just(""),
    # 随机二进制数据（转为字符串）
    st.binary(min_size=1, max_size=50).map(lambda b: b.decode("latin-1", errors="replace")),
)

# 缺少必需字段的 JSON 策略（name 是必需的）
incomplete_json_strategy = st.one_of(
    # 缺少 name（必需字段）
    st.just('{"id": "test", "nodes": [], "edges": []}'),
    # 空对象
    st.just('{}'),
    # 数组而非对象
    st.just('[]'),
    # null
    st.just('null'),
    # 数字
    st.just('123'),
    # 字符串
    st.just('"string"'),
)


# ============ 属性测试 ============

@given(invalid_json_strategy)
@settings(max_examples=30, deadline=None)
def test_invalid_json_does_not_crash(invalid_content):
    """
    **Property 13: 无效流程文件容错**
    
    *For any* 格式无效的 JSON 文件，加载操作 SHALL 返回错误而非导致应用崩溃。
    """
    FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    test_id = "test-invalid-json"
    flow_path = FLOWS_DIR / f"{test_id}.json"
    
    try:
        # 写入无效内容
        with open(flow_path, "w", encoding="utf-8") as f:
            f.write(invalid_content)
        
        # 尝试加载 - 应该抛出异常而非崩溃
        with pytest.raises(Exception):
            _load_flow(test_id)
            
    finally:
        if flow_path.exists():
            flow_path.unlink()


@given(incomplete_json_strategy)
@settings(max_examples=20, deadline=None)
def test_incomplete_json_does_not_crash(incomplete_content):
    """
    测试缺少必需字段的 JSON 不会导致崩溃
    """
    FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    test_id = "test-incomplete-json"
    flow_path = FLOWS_DIR / f"{test_id}.json"
    
    try:
        # 写入不完整的 JSON
        with open(flow_path, "w", encoding="utf-8") as f:
            f.write(incomplete_content)
        
        # 尝试加载 - 应该抛出异常而非崩溃
        with pytest.raises(Exception):
            _load_flow(test_id)
            
    finally:
        if flow_path.exists():
            flow_path.unlink()


def test_nonexistent_flow_returns_404():
    """测试加载不存在的流程返回 404"""
    client = TestClient(app)
    
    response = client.get("/v1/flows/nonexistent-flow-id-12345")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_corrupted_json_via_api():
    """通过 API 测试损坏的 JSON 文件"""
    FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    test_id = "test-corrupted-api"
    flow_path = FLOWS_DIR / f"{test_id}.json"
    
    try:
        # 写入损坏的 JSON
        with open(flow_path, "w", encoding="utf-8") as f:
            f.write('{"id": "test-corrupted-api", "name": "test", invalid}')
        
        client = TestClient(app)
        response = client.get(f"/v1/flows/{test_id}")
        
        # 应该返回 400 错误状态码（无效 JSON）
        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["detail"] or "Failed to load" in response.json()["detail"]
        
    finally:
        if flow_path.exists():
            flow_path.unlink()


def test_wrong_type_fields():
    """测试字段类型错误的 JSON"""
    FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    test_id = "test-wrong-types"
    flow_path = FLOWS_DIR / f"{test_id}.json"
    
    try:
        # 写入类型错误的 JSON
        wrong_type_json = {
            "id": test_id,
            "name": 12345,  # 应该是字符串
            "nodes": "not a list",  # 应该是列表
            "edges": {"wrong": "type"}  # 应该是列表
        }
        
        with open(flow_path, "w", encoding="utf-8") as f:
            json.dump(wrong_type_json, f)
        
        # 尝试加载 - 应该抛出验证错误
        with pytest.raises(Exception):
            _load_flow(test_id)
            
    finally:
        if flow_path.exists():
            flow_path.unlink()


def test_valid_flow_loads_successfully():
    """测试有效的流程文件可以正常加载"""
    FLOWS_DIR.mkdir(parents=True, exist_ok=True)
    test_id = "test-valid-flow"
    flow_path = FLOWS_DIR / f"{test_id}.json"
    
    try:
        valid_flow = {
            "id": test_id,
            "name": "Valid Flow",
            "description": "A valid test flow",
            "nodes": [],
            "edges": [],
            "createdAt": "2024-01-01T00:00:00",
            "updatedAt": "2024-01-01T00:00:00"
        }
        
        with open(flow_path, "w", encoding="utf-8") as f:
            json.dump(valid_flow, f)
        
        # 应该成功加载
        flow = _load_flow(test_id)
        assert flow.id == test_id
        assert flow.name == "Valid Flow"
        
    finally:
        if flow_path.exists():
            flow_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
