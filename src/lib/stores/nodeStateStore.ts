/**
 * 节点状态存储 - 使用 TanStack Store + localStorage 持久化
 * 用于在全屏/普通模式切换时保持节点内部状态
 * 支持页面刷新后恢复状态
 */

import { Store } from '@tanstack/store';

// localStorage key
const STORAGE_KEY = 'aestival-node-states';

// 最大存储大小（字节）- 限制为 2MB
const MAX_STORAGE_SIZE = 2 * 1024 * 1024;

// 节点状态 Map 类型
type NodeStatesMap = Map<string, unknown>;

/**
 * 从 localStorage 加载状态
 */
function loadFromStorage(): NodeStatesMap {
  if (typeof window === 'undefined') return new Map();
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return new Map();
    const parsed = JSON.parse(stored);
    return new Map(Object.entries(parsed));
  } catch {
    return new Map();
  }
}

/**
 * 清理大型数据字段，只保留必要的状态
 */
function cleanStateForStorage(state: unknown): unknown {
  if (state === null || state === undefined) return state;
  if (typeof state !== 'object') return state;
  if (Array.isArray(state)) {
    // 限制数组长度
    if (state.length > 100) {
      return state.slice(0, 100);
    }
    return state.map(cleanStateForStorage);
  }
  
  const cleaned: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(state as Record<string, unknown>)) {
    // 跳过大型数据字段
    if (key === 'scanResult' || key === 'previewData' || key === 'logs' || 
        key === 'output' || key === 'result' || key === 'items' ||
        key === 'fileList' || key === 'archives' || key === 'folders') {
      continue;
    }
    // 跳过过长的字符串
    if (typeof value === 'string' && value.length > 1000) {
      cleaned[key] = value.slice(0, 1000);
      continue;
    }
    cleaned[key] = cleanStateForStorage(value);
  }
  return cleaned;
}

/**
 * 保存状态到 localStorage
 */
function saveToStorage(states: NodeStatesMap): void {
  if (typeof window === 'undefined') return;
  try {
    // 清理每个节点的状态
    const cleanedStates: Record<string, unknown> = {};
    for (const [nodeId, state] of states) {
      cleanedStates[nodeId] = cleanStateForStorage(state);
    }
    
    const json = JSON.stringify(cleanedStates);
    
    // 检查大小
    if (json.length > MAX_STORAGE_SIZE) {
      console.warn('[nodeStateStore] 状态过大，清理旧数据');
      // 只保留最近的 20 个节点
      const entries = Object.entries(cleanedStates);
      const trimmed = Object.fromEntries(entries.slice(-20));
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
      return;
    }
    
    localStorage.setItem(STORAGE_KEY, json);
  } catch (e) {
    console.warn('[nodeStateStore] 保存失败，清理存储:', e);
    // 清理存储
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}
  }
}

// 创建 TanStack Store，从 localStorage 初始化
export const nodeStateStore = new Store<NodeStatesMap>(loadFromStorage());

// 订阅变化，自动保存到 localStorage
nodeStateStore.subscribe(() => {
  saveToStorage(nodeStateStore.state);
});

/**
 * 获取节点状态
 */
export function getNodeState<T>(nodeId: string): T | undefined {
  return nodeStateStore.state.get(nodeId) as T | undefined;
}

/**
 * 设置节点状态（完全覆盖）
 */
export function setNodeState<T>(nodeId: string, state: T): void {
  nodeStateStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeId, state);
    return next;
  });
}

/**
 * 更新节点状态（合并）
 */
export function updateNodeState<T>(nodeId: string, partial: Partial<T>): void {
  nodeStateStore.setState((prev) => {
    const next = new Map(prev);
    const current = (next.get(nodeId) || {}) as T;
    next.set(nodeId, { ...current, ...partial });
    return next;
  });
}

/**
 * 删除节点状态
 */
export function deleteNodeState(nodeId: string): void {
  nodeStateStore.setState((prev) => {
    const next = new Map(prev);
    next.delete(nodeId);
    return next;
  });
}

/**
 * 清空所有状态
 */
export function clearNodeStates(): void {
  nodeStateStore.setState(() => new Map());
}

/**
 * 订阅特定节点的状态变化
 */
export function subscribeNodeState<T>(
  nodeId: string,
  callback: (state: T | undefined) => void
): () => void {
  return nodeStateStore.subscribe(() => {
    callback(nodeStateStore.state.get(nodeId) as T | undefined);
  });
}
