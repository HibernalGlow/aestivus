"""
存储 API 属性测试
使用 Hypothesis 进行属性测试，验证 CRUD 操作的正确性

Property 1: Layout CRUD Round-Trip
Property 4: Preset CRUD Round-Trip  
Property 6: Default Preset Round-Trip
"""

import pytest
from hypothesis import given, strategies as st, settings
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
import json
import tempfile
import os

# 设置测试数据库路径
os.environ["AESTIVUS_TEST_DB"] = "true"

from main import app
from db.database import engine

client = TestClient(app)


# ========== 测试数据生成策略 ==========

# 节点类型策略
node_type_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
    min_size=1,
    max_size=20
).filter(lambda x: x.strip() != '')

# GridItem 策略
grid_item_strategy = st.fixed_dictionaries({
    "id": st.text(min_size=1, max_size=20),
    "x": st.integers(min_value=0, max_value=10),
    "y": st.integers(min_value=0, max_value=10),
    "w": st.integers(min_value=1, max_value=4),
    "h": st.integers(min_value=1, max_value=4),
})

# NodeConfig 策略
node_config_strategy = st.fixed_dictionaries({
    "nodeType": node_type_strategy,
    "fullscreen": st.fixed_dictionaries({
        "gridLayout": st.lists(grid_item_strategy, min_size=0, max_size=5),
        "sizeOverrides": st.dictionaries(st.text(min_size=1, max_size=10), st.fixed_dictionaries({})),
        "tabGroups": st.just([]),
    }),
    "normal": st.fixed_dictionaries({
        "gridLayout": st.lists(grid_item_strategy, min_size=0, max_size=5),
        "sizeOverrides": st.dictionaries(st.text(min_size=1, max_size=10), st.fixed_dictionaries({})),
        "tabGroups": st.just([]),
    }),
    "updatedAt": st.floats(min_value=0, max_value=2000000000000),
})

# 预设 ID 策略
preset_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
    min_size=5,
    max_size=30
).filter(lambda x: x.strip() != '')


# ========== Fixtures ==========

@pytest.fixture(autouse=True)
def setup_test_db():
    """每个测试前重置数据库"""
    # 清空所有表
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    # 测试后清理
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


# ========== Property 1: Layout CRUD Round-Trip ==========
# Feature: backend-database-storage, Property 1: Layout CRUD Round-Trip
# Validates: Requirements 2.1, 2.2

@given(node_type=node_type_strategy, config=node_config_strategy)
@settings(max_examples=100)
def test_layout_crud_round_trip(node_type: str, config: dict):
    """
    Property 1: Layout CRUD Round-Trip
    
    *For any* valid node_type and NodeConfig, saving a layout via PUT 
    then retrieving via GET SHALL return an equivalent config object.
    
    **Validates: Requirements 2.1, 2.2**
    """
    # PUT 保存布局
    response = client.put(
        f"/v1/storage/layouts/{node_type}",
        json={"config": config}
    )
    assert response.status_code == 200
    assert response.json()["success"] == True
    
    # GET 获取布局
    response = client.get(f"/v1/storage/layouts/{node_type}")
    assert response.status_code == 200
    
    retrieved = response.json()
    assert retrieved is not None
    
    # 验证数据一致性
    assert retrieved["nodeType"] == config["nodeType"]
    assert retrieved["fullscreen"]["gridLayout"] == config["fullscreen"]["gridLayout"]
    assert retrieved["normal"]["gridLayout"] == config["normal"]["gridLayout"]


# ========== Property 2: Layout Delete Removes Data ==========
# Feature: backend-database-storage, Property 2: Layout Delete Removes Data
# Validates: Requirements 2.3, 2.5

@given(node_type=node_type_strategy, config=node_config_strategy)
@settings(max_examples=100)
def test_layout_delete_removes_data(node_type: str, config: dict):
    """
    Property 2: Layout Delete Removes Data
    
    *For any* node_type that has been saved, after DELETE 
    the GET request SHALL return null.
    
    **Validates: Requirements 2.3, 2.5**
    """
    # 先保存
    client.put(f"/v1/storage/layouts/{node_type}", json={"config": config})
    
    # 删除
    response = client.delete(f"/v1/storage/layouts/{node_type}")
    assert response.status_code == 200
    assert response.json()["success"] == True
    
    # 验证已删除
    response = client.get(f"/v1/storage/layouts/{node_type}")
    assert response.status_code == 200
    assert response.json() is None


# ========== Property 3: Layout List Contains All Saved Types ==========
# Feature: backend-database-storage, Property 3: Layout List Contains All Saved Types
# Validates: Requirements 2.4

@given(node_types=st.lists(node_type_strategy, min_size=1, max_size=5, unique=True))
@settings(max_examples=50)
def test_layout_list_contains_all_saved(node_types: list):
    """
    Property 3: Layout List Contains All Saved Types
    
    *For any* set of saved layouts, GET /storage/layouts 
    SHALL return a list containing all saved node_types.
    
    **Validates: Requirements 2.4**
    """
    # 保存多个布局
    for node_type in node_types:
        config = {"nodeType": node_type, "fullscreen": {"gridLayout": [], "sizeOverrides": {}, "tabGroups": []}, "normal": {"gridLayout": [], "sizeOverrides": {}, "tabGroups": []}, "updatedAt": 0}
        client.put(f"/v1/storage/layouts/{node_type}", json={"config": config})
    
    # 获取列表
    response = client.get("/v1/storage/layouts")
    assert response.status_code == 200
    
    saved_types = response.json()
    
    # 验证所有保存的类型都在列表中
    for node_type in node_types:
        assert node_type in saved_types


# ========== Property 4: Preset CRUD Round-Trip ==========
# Feature: backend-database-storage, Property 4: Preset CRUD Round-Trip
# Validates: Requirements 3.1, 3.2, 3.3

@given(
    preset_id=preset_id_strategy,
    name=st.text(min_size=1, max_size=20),
    node_type=node_type_strategy,
    layout=st.lists(grid_item_strategy, min_size=1, max_size=3)
)
@settings(max_examples=100)
def test_preset_crud_round_trip(preset_id: str, name: str, node_type: str, layout: list):
    """
    Property 4: Preset CRUD Round-Trip
    
    *For any* valid LayoutPreset, creating via POST then retrieving 
    via GET SHALL return an equivalent preset object.
    
    **Validates: Requirements 3.1, 3.2, 3.3**
    """
    # POST 创建预设
    preset_data = {
        "id": preset_id,
        "name": name,
        "node_type": node_type,
        "layout": layout,
        "is_builtin": False
    }
    
    response = client.post("/v1/storage/presets", json=preset_data)
    assert response.status_code == 200
    
    created = response.json()
    assert created["id"] == preset_id
    assert created["name"] == name
    
    # GET 获取预设列表
    response = client.get(f"/v1/storage/presets?node_type={node_type}")
    assert response.status_code == 200
    
    presets = response.json()
    found = next((p for p in presets if p["id"] == preset_id), None)
    
    assert found is not None
    assert found["name"] == name
    assert found["layout"] == layout


# ========== Property 5: Preset Delete Removes From List ==========
# Feature: backend-database-storage, Property 5: Preset Delete Removes From List
# Validates: Requirements 3.4

@given(
    preset_id=preset_id_strategy,
    name=st.text(min_size=1, max_size=20),
    node_type=node_type_strategy
)
@settings(max_examples=100)
def test_preset_delete_removes_from_list(preset_id: str, name: str, node_type: str):
    """
    Property 5: Preset Delete Removes From List
    
    *For any* preset that has been created, after DELETE 
    the preset SHALL not appear in the list.
    
    **Validates: Requirements 3.4**
    """
    # 创建预设
    preset_data = {
        "id": preset_id,
        "name": name,
        "node_type": node_type,
        "layout": [{"id": "test", "x": 0, "y": 0, "w": 1, "h": 1}],
        "is_builtin": False
    }
    client.post("/v1/storage/presets", json=preset_data)
    
    # 删除预设
    response = client.delete(f"/v1/storage/presets/{preset_id}")
    assert response.status_code == 200
    
    # 验证不在列表中
    response = client.get("/v1/storage/presets")
    presets = response.json()
    
    found = next((p for p in presets if p["id"] == preset_id), None)
    assert found is None


# ========== Property 6: Default Preset Round-Trip ==========
# Feature: backend-database-storage, Property 6: Default Preset Round-Trip
# Validates: Requirements 3.5, 3.6

@given(
    node_type=node_type_strategy,
    fullscreen_id=st.one_of(st.none(), preset_id_strategy),
    normal_id=st.one_of(st.none(), preset_id_strategy)
)
@settings(max_examples=100)
def test_default_preset_round_trip(node_type: str, fullscreen_id, normal_id):
    """
    Property 6: Default Preset Round-Trip
    
    *For any* node_type and default preset configuration, 
    setting via PUT then retrieving via GET SHALL return the same configuration.
    
    **Validates: Requirements 3.5, 3.6**
    """
    # PUT 设置默认预设
    defaults_data = {
        "fullscreen_preset_id": fullscreen_id,
        "normal_preset_id": normal_id
    }
    
    response = client.put(f"/v1/storage/defaults/{node_type}", json=defaults_data)
    assert response.status_code == 200
    
    # GET 获取默认预设
    response = client.get(f"/v1/storage/defaults/{node_type}")
    assert response.status_code == 200
    
    retrieved = response.json()
    assert retrieved is not None
    assert retrieved["fullscreenPresetId"] == fullscreen_id
    assert retrieved["normalPresetId"] == normal_id


# ========== 边界情况测试 ==========

def test_get_nonexistent_layout_returns_null():
    """测试获取不存在的布局返回 null"""
    response = client.get("/v1/storage/layouts/nonexistent-node-type")
    assert response.status_code == 200
    assert response.json() is None


def test_delete_nonexistent_layout_succeeds():
    """测试删除不存在的布局也返回成功（幂等）"""
    response = client.delete("/v1/storage/layouts/nonexistent-node-type")
    assert response.status_code == 200
    assert response.json()["success"] == True


def test_get_nonexistent_defaults_returns_null():
    """测试获取不存在的默认预设返回 null"""
    response = client.get("/v1/storage/defaults/nonexistent-node-type")
    assert response.status_code == 200
    assert response.json() is None
