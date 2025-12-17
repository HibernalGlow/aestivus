/**
 * 节点布局状态存储 - 统一管理节点的所有配置
 * 两种模式共用 GridItem[] 结构，节点模式用静态渲染，全屏模式用 GridStack
 * 
 * 注意：Tab 状态已迁移到 unifiedTabStore.ts，此处仅保留布局配置
 */

import { Store } from '@tanstack/store';
import type { GridItem } from '$lib/components/ui/dashboard-grid';

const STORAGE_KEY = 'aestival-node-layouts';

/** 区块尺寸覆盖配置 */
export interface BlockSizeOverride {
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
}

/** 模式布局状态（简化版，Tab 状态已移至 unifiedTabStore） */
export interface ModeLayoutState {
  /** 布局配置 */
  gridLayout: GridItem[];
  /** 尺寸覆盖 */
  sizeOverrides: Record<string, BlockSizeOverride>;
}

/** 旧版模式布局状态（用于迁移） */
interface LegacyModeLayoutState {
  gridLayout: GridItem[];
  tabStates?: Record<string, { activeTab: number; children: string[] }>;
  tabBlocks?: string[];
  sizeOverrides: Record<string, BlockSizeOverride>;
}

/** 节点配置 */
export interface NodeConfig {
  nodeType: string;
  fullscreen: ModeLayoutState;
  normal: ModeLayoutState;
  updatedAt: number;
}

type NodeConfigMap = Map<string, NodeConfig>;

// ============ 默认配置 ============

export function createDefaultModeState(defaultGridLayout: GridItem[] = []): ModeLayoutState {
  return {
    gridLayout: defaultGridLayout,
    sizeOverrides: {}
  };
}

export function createDefaultNodeConfig(
  nodeType: string, 
  defaultFullscreenLayout: GridItem[] = [],
  defaultNormalLayout: GridItem[] = []
): NodeConfig {
  return {
    nodeType,
    fullscreen: createDefaultModeState(defaultFullscreenLayout),
    normal: createDefaultModeState(defaultNormalLayout),
    updatedAt: Date.now()
  };
}

// ============ 存储 ============

function loadFromStorage(): NodeConfigMap {
  if (typeof window === 'undefined') return new Map();
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return new Map();
    const parsed = JSON.parse(stored);
    console.log('[loadFromStorage] 从 localStorage 加载:', parsed);
    // 打印每个 nodeType 的 Tab 状态
    for (const [key, config] of Object.entries(parsed)) {
      const c = config as NodeConfig;
      console.log(`[loadFromStorage] ${key}:`, {
        fullscreen: { tabBlocks: c.fullscreen?.tabBlocks, tabStates: c.fullscreen?.tabStates },
        normal: { tabBlocks: c.normal?.tabBlocks, tabStates: c.normal?.tabStates }
      });
    }
    return new Map(Object.entries(parsed));
  } catch (e) {
    console.error('[nodeLayoutStore] 加载失败:', e);
    return new Map();
  }
}

function saveToStorage(configs: NodeConfigMap): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Object.fromEntries(configs)));
  } catch (e) {
    console.warn('[nodeLayoutStore] 保存失败:', e);
  }
}

export const nodeLayoutStore = new Store<NodeConfigMap>(new Map());

let isHydrated = false;

export function hydrateFromStorage(): void {
  if (isHydrated || typeof window === 'undefined') return;
  isHydrated = true;
  const stored = loadFromStorage();
  if (stored.size > 0) {
    nodeLayoutStore.setState(() => stored);
  }
}

nodeLayoutStore.subscribe(() => {
  if (isHydrated) saveToStorage(nodeLayoutStore.state);
});

// ============ CRUD ============

export function getNodeConfig(nodeId: string): NodeConfig | undefined {
  hydrateFromStorage();
  return nodeLayoutStore.state.get(nodeId);
}

export function setNodeConfig(nodeId: string, config: NodeConfig): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeId, { ...config, updatedAt: Date.now() });
    return next;
  });
}

/** 验证并修复配置结构（兼容旧格式） */
function validateAndFixConfig(config: NodeConfig | { fullscreen?: LegacyModeLayoutState; normal?: LegacyModeLayoutState; nodeType?: string; updatedAt?: number }): NodeConfig {
  // 确保 fullscreen 和 normal 都有完整结构（忽略旧的 tabStates 和 tabBlocks）
  const fixModeState = (state: ModeLayoutState | LegacyModeLayoutState | undefined): ModeLayoutState => {
    if (!state) return createDefaultModeState();
    return {
      gridLayout: Array.isArray(state.gridLayout) ? state.gridLayout : [],
      sizeOverrides: state.sizeOverrides && typeof state.sizeOverrides === 'object' ? state.sizeOverrides : {}
    };
  };
  
  return {
    nodeType: config.nodeType || 'unknown',
    fullscreen: fixModeState(config.fullscreen),
    normal: fixModeState(config.normal),
    updatedAt: config.updatedAt || Date.now()
  };
}

/**
 * 获取或创建节点配置
 * 注意：使用 nodeType 作为 key，而不是 nodeId，这样同类型节点共享布局配置
 */
export function getOrCreateNodeConfig(
  nodeId: string, 
  nodeType: string,
  defaultFullscreenLayout: GridItem[] = [],
  defaultNormalLayout: GridItem[] = []
): NodeConfig {
  hydrateFromStorage();
  // 使用 nodeType 作为 key，而不是 nodeId
  const configKey = nodeType;
  const existing = nodeLayoutStore.state.get(configKey);
  
  if (existing) {
    // 验证并修复现有配置
    const fixed = validateAndFixConfig(existing);
    // 如果配置被修复了，保存修复后的版本
    if (JSON.stringify(fixed) !== JSON.stringify(existing)) {
      setNodeConfigByType(nodeType, fixed);
      return fixed;
    }
    return existing;
  }
  const newConfig = createDefaultNodeConfig(nodeType, defaultFullscreenLayout, defaultNormalLayout);
  setNodeConfigByType(nodeType, newConfig);
  return newConfig;
}

/** 按 nodeType 设置配置 */
function setNodeConfigByType(nodeType: string, config: NodeConfig): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeType, { ...config, updatedAt: Date.now() });
    return next;
  });
}

export function deleteNodeConfig(nodeType: string): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    next.delete(nodeType);
    return next;
  });
}

// ============ 布局操作 ============
// 注意：所有函数使用 nodeType 作为 key，而不是 nodeId

export function updateGridLayout(
  nodeType: string, 
  mode: 'fullscreen' | 'normal',
  gridLayout: GridItem[]
): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType) || createDefaultNodeConfig(nodeType);
    next.set(nodeType, {
      ...current,
      [mode]: { ...current[mode], gridLayout },
      updatedAt: Date.now()
    });
    return next;
  });
}

export function updateSizeOverride(
  nodeType: string, 
  mode: 'fullscreen' | 'normal',
  blockId: string, 
  override: BlockSizeOverride
): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType) || createDefaultNodeConfig(nodeType);
    next.set(nodeType, {
      ...current,
      [mode]: {
        ...current[mode],
        sizeOverrides: { ...current[mode].sizeOverrides, [blockId]: override }
      },
      updatedAt: Date.now()
    });
    return next;
  });
}

// ============ Tab 操作（已迁移到 unifiedTabStore.ts） ============
// 注意：Tab 相关操作请使用 unifiedTabStore 中的函数：
// - createTab, removeTab, setActiveTab
// - addChild, removeChild, reorderChildren
// - getUsedBlockIds, isTabContainer, getTabState

// 以下函数保留用于布局操作中移除/恢复区块

/** 从布局中移除区块（创建 Tab 时调用） */
export function removeBlocksFromLayout(
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  blockIds: string[]
): void {
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType);
    if (!current) return prev;
    
    const modeState = current[mode];
    const newGridLayout = modeState.gridLayout.filter(item => !blockIds.includes(item.id));
    
    next.set(nodeType, {
      ...current,
      [mode]: { ...modeState, gridLayout: newGridLayout },
      updatedAt: Date.now()
    });
    return next;
  });
}

/** 恢复区块到布局（删除 Tab 时调用） */
export function restoreBlocksToLayout(
  nodeType: string,
  mode: 'fullscreen' | 'normal',
  blockIds: string[],
  basePosition: { x: number; y: number },
  isFullscreen: boolean = false
): void {
  if (blockIds.length === 0) return;
  
  nodeLayoutStore.setState((prev) => {
    const next = new Map(prev);
    const current = next.get(nodeType);
    if (!current) return prev;
    
    const modeState = current[mode];
    
    const restoredItems: GridItem[] = blockIds.map((blockId, index) => ({
      id: blockId,
      x: isFullscreen ? basePosition.x + 2 : index % 2,
      y: isFullscreen ? basePosition.y + index * 2 : Math.floor(index / 2) + basePosition.y + 1,
      w: 1,
      h: isFullscreen ? 2 : 1,
      minW: 1,
      minH: 1
    }));
    
    next.set(nodeType, {
      ...current,
      [mode]: {
        ...modeState,
        gridLayout: [...modeState.gridLayout, ...restoredItems]
      },
      updatedAt: Date.now()
    });
    return next;
  });
}

// ============ 订阅 ============

export function subscribeNodeConfig(
  nodeType: string,
  callback: (config: NodeConfig | undefined) => void
): () => void {
  return nodeLayoutStore.subscribe(() => {
    callback(nodeLayoutStore.state.get(nodeType));
  });
}

// ============ 导出/导入 ============

export function exportNodeConfig(nodeType: string): string | null {
  hydrateFromStorage();
  const config = nodeLayoutStore.state.get(nodeType);
  return config ? JSON.stringify(config, null, 2) : null;
}

export function importNodeConfig(nodeType: string, json: string): boolean {
  try {
    setNodeConfigByType(nodeType, JSON.parse(json) as NodeConfig);
    return true;
  } catch {
    return false;
  }
}
