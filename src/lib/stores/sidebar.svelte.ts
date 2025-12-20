/**
 * 侧边栏状态管理
 * 支持左右侧边栏，每个侧边栏可以渲染一个节点
 */
import { writable } from 'svelte/store';

export interface SidebarState {
  // 左侧边栏
  leftOpen: boolean;
  leftPinned: boolean;
  leftWidth: number;
  leftNodeType: string | null;  // 当前显示的节点类型
  leftNodeId: string | null;    // 节点实例 ID（用于状态持久化）
  
  // 右侧边栏
  rightOpen: boolean;
  rightPinned: boolean;
  rightWidth: number;
  rightNodeType: string | null;
  rightNodeId: string | null;
}

const STORAGE_KEY = 'aestivus_sidebar_state';

function loadState(): SidebarState {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return JSON.parse(saved);
  } catch (e) { console.warn('加载侧边栏状态失败:', e); }
  return {
    leftOpen: true,
    leftPinned: true,
    leftWidth: 240,
    leftNodeType: 'node_palette',  // 默认显示节点面板
    leftNodeId: 'sidebar-left-palette',
    rightOpen: false,
    rightPinned: false,
    rightWidth: 300,
    rightNodeType: null,
    rightNodeId: null
  };
}

function createSidebarStore() {
  const initial = loadState();
  const { subscribe, set, update } = writable<SidebarState>(initial);

  // 自动保存
  subscribe(state => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) { console.warn('保存侧边栏状态失败:', e); }
  });

  return {
    subscribe,
    
    // 左侧边栏
    toggleLeftOpen: () => update(s => ({ ...s, leftOpen: !s.leftOpen })),
    setLeftOpen: (open: boolean) => update(s => ({ ...s, leftOpen: open })),
    toggleLeftPin: () => update(s => ({ ...s, leftPinned: !s.leftPinned, leftOpen: true })),
    setLeftWidth: (width: number) => update(s => ({ ...s, leftWidth: Math.max(180, Math.min(500, width)) })),
    setLeftNode: (nodeType: string | null, nodeId?: string) => update(s => ({
      ...s,
      leftNodeType: nodeType,
      leftNodeId: nodeId || (nodeType ? `sidebar-left-${nodeType}` : null)
    })),
    
    // 右侧边栏
    toggleRightOpen: () => update(s => ({ ...s, rightOpen: !s.rightOpen })),
    setRightOpen: (open: boolean) => update(s => ({ ...s, rightOpen: open })),
    toggleRightPin: () => update(s => ({ ...s, rightPinned: !s.rightPinned, rightOpen: true })),
    setRightWidth: (width: number) => update(s => ({ ...s, rightWidth: Math.max(200, Math.min(600, width)) })),
    setRightNode: (nodeType: string | null, nodeId?: string) => update(s => ({
      ...s,
      rightNodeType: nodeType,
      rightNodeId: nodeId || (nodeType ? `sidebar-right-${nodeType}` : null),
      rightOpen: nodeType ? true : s.rightOpen
    })),
    
    reset: () => set(loadState())
  };
}

export const sidebarStore = createSidebarStore();
