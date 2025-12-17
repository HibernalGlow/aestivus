/**
 * 节点布局状态存储 - 管理节点模式和全屏模式的独立布局状态
 * 包括 GridStack 布局、Tab 状态等
 * 复用 nodeStateStore 的存储机制
 */

import { Store } from '@tanstack/store';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import type { TabBlockState } from '$lib/components/blocks/blockRegistry';

// localStorage key
const STORAGE_KEY = 'aestival-node-layouts';

/** 单模式布局状态 */
export interface ModeLayoutState {
  /** Tab 区块状态 */
  tabStates: Record<string, TabBlockState>;
  /** 哪些区块是 Tab 容器 */
  tabBlocks: string[];
}

/** 完整节点布局状态 */
export interface NodeLayoutState {
  /** 全屏模式布局 */
  fullscreen: ModeLayoutState & {
    /** GridStack 布局配置 */
    gridLayout: GridItem[];
  };
  /** 节点模式布局 */
  normal: ModeLayoutState;
}

/** 布局状态 Map 类型 */
type LayoutStatesMap = Map<string, NodeLayoutState>;

/** 创建默认的模式布局状态 */
export function createDefaultModeState(): ModeLayoutState {
  return {
    tabStates: {},
    tabBlocks: []
  };
}

/** 创建默认的节点布局状态 */
export function createDefaultLayoutState(defaultGridLayout: GridItem[] = []): NodeLayoutState {
  return {
    fullscreen: {
      ...createDefaultModeState(),
      gridLayout: defaultGridLayout
    },
    normal: createDefaultModeState()
  };
}

/**
 * 从 localStorage 加载状态
 */
function loadFromStorage(): LayoutStatesMap {
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
 * 保存状态到 localStorage
 */
function saveToStorage(states: LayoutStatesMap): void {
  if (typeof window === 'undefined') return;
  try {
    const obj = Object.fromEntries(states);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
  } catch (e) {
    console.warn('[nodeLayoutStore] Failed to save to localStorage:', e);
  }
}

// 创建 TanStack Store
export const nodeLayoutStore = new Store<LayoutStatesMap>(loadFromStorage());

// 订阅变化，自动保存到 localStorage
nodeLayoutStore.subscribe(() => {
  saveToStorage(nodeLayoutStore.state);
});

/**
 * 获取节点布局状态
 */
export function getNodeLayoutState(nodeId: string): NodeLayoutState | undefined {
  return nodeLayoutStore.state.get(nodeId);
}

/**
 * 设置节点布局状态（完全覆盖）
 */
export function setNodeLayoutState(nodeId: string, state: NodeLayoutState): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeId, state);
    return next;
  });
}

/**
 * 获取或创建节点布局状态
 */
export function getOrCreateLayoutState(nodeId: string, defaultGridLayout: GridItem[] = []): NodeLayoutState {
  const existing = getNodeLayoutState(nodeId);
  if (existing) return existing;
  
  const newState = createDefaultLayoutState(defaultGridLayout);
  setNodeLayoutState(nodeId, newState);
  return newState;
}

/**
 * 更新指定模式的布局状态
 */
export function updateModeState(
  nodeId: string,
  mode: 'fullscreen' | 'normal',
  update: Partial<ModeLayoutState>
): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId) || createDefaultLayoutState();
    
    next.set(nodeId, {
      ...current,
      [mode]: {
        ...current[mode],
        ...update
      }
    });
    
    return next;
  });
}

/**
 * 更新全屏模式的 GridStack 布局
 */
export function updateFullscreenGridLayout(nodeId: string, gridLayout: GridItem[]): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId) || createDefaultLayoutState();
    
    next.set(nodeId, {
      ...current,
      fullscreen: {
        ...current.fullscreen,
        gridLayout
      }
    });
    
    return next;
  });
}

/**
 * 更新 Tab 状态
 */
export function updateTabState(
  nodeId: string,
  mode: 'fullscreen' | 'normal',
  tabId: string,
  state: TabBlockState
): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId) || createDefaultLayoutState();
    
    next.set(nodeId, {
      ...current,
      [mode]: {
        ...current[mode],
        tabStates: {
          ...current[mode].tabStates,
          [tabId]: state
        }
      }
    });
    
    return next;
  });
}

/**
 * 创建 Tab 区块（合并多个区块）
 * @param nodeId 节点 ID
 * @param mode 模式
 * @param blockIds 要合并的区块 ID 列表（第一个作为 Tab 容器）
 */
export function createTabBlock(
  nodeId: string,
  mode: 'fullscreen' | 'normal',
  blockIds: string[]
): void {
  if (blockIds.length < 2) return;
  
  const tabId = blockIds[0];
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId) || createDefaultLayoutState();
    const modeState = current[mode];
    
    next.set(nodeId, {
      ...current,
      [mode]: {
        ...modeState,
        tabBlocks: [...modeState.tabBlocks, tabId],
        tabStates: {
          ...modeState.tabStates,
          [tabId]: { activeTab: 0, children: blockIds }
        }
      }
    });
    
    return next;
  });
}

/**
 * 删除 Tab 区块（恢复为独立区块）
 */
export function removeTabBlock(
  nodeId: string,
  mode: 'fullscreen' | 'normal',
  tabId: string
): string[] {
  let childIds: string[] = [];
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeId);
    if (!current) return prev;
    
    const modeState = current[mode];
    const tabState = modeState.tabStates[tabId];
    
    if (tabState) {
      childIds = tabState.children.slice(1); // 除第一个外的子区块
    }
    
    const newTabStates = { ...modeState.tabStates };
    delete newTabStates[tabId];
    
    next.set(nodeId, {
      ...current,
      [mode]: {
        ...modeState,
        tabBlocks: modeState.tabBlocks.filter(id => id !== tabId),
        tabStates: newTabStates
      }
    });
    
    return next;
  });
  
  return childIds;
}

/**
 * 检查区块是否是 Tab 容器
 */
export function isTabContainer(
  nodeId: string,
  mode: 'fullscreen' | 'normal',
  blockId: string
): boolean {
  const state = getNodeLayoutState(nodeId);
  if (!state) return false;
  return state[mode].tabBlocks.includes(blockId);
}

/**
 * 获取 Tab 状态
 */
export function getTabState(
  nodeId: string,
  mode: 'fullscreen' | 'normal',
  tabId: string
): TabBlockState | undefined {
  const state = getNodeLayoutState(nodeId);
  if (!state) return undefined;
  return state[mode].tabStates[tabId];
}

/**
 * 获取已在 Tab 中使用的区块 ID（作为子区块，不包括 Tab 容器本身）
 */
export function getUsedTabBlockIds(
  nodeId: string,
  mode: 'fullscreen' | 'normal'
): string[] {
  const state = getNodeLayoutState(nodeId);
  if (!state) return [];
  
  const ids: string[] = [];
  for (const tabState of Object.values(state[mode].tabStates)) {
    // 跳过第一个（它是 Tab 容器本身）
    ids.push(...tabState.children.slice(1));
  }
  return ids;
}

/**
 * 删除节点布局状态
 */
export function deleteNodeLayoutState(nodeId: string): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.delete(nodeId);
    return next;
  });
}

/**
 * 订阅节点布局状态变化
 */
export function subscribeNodeLayoutState(
  nodeId: string,
  callback: (state: NodeLayoutState | undefined) => void
): () => void {
  return nodeLayoutStore.subscribe(() => {
    callback(nodeLayoutStore.state.get(nodeId));
  });
}
