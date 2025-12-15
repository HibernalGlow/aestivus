/**
 * 节点状态存储 - 使用 TanStack Store
 * 用于在全屏/普通模式切换时保持节点内部状态
 */

import { Store } from '@tanstack/store';

// 节点状态 Map 类型
type NodeStatesMap = Map<string, unknown>;

// 创建 TanStack Store
export const nodeStateStore = new Store<NodeStatesMap>(new Map());

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
