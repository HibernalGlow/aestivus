/**
 * UnifiedTabStore - 统一 Tab 状态管理
 * 
 * 核心功能：
 * 1. Tab 配置存储在节点类型级别，节点模式和全屏模式共享
 * 2. 带版本号的 JSON 序列化，支持数据迁移
 * 3. 防抖持久化（500ms）
 * 4. 边界情况优雅降级
 */

import { Store } from '@tanstack/store';

// ============ 常量 ============

/** Tab 状态版本号，用于数据迁移 */
export const TAB_STATE_VERSION = 1;

/** localStorage 存储键 */
const STORAGE_KEY = 'aestival-unified-tabs';

/** 持久化防抖延迟（毫秒） */
const PERSIST_DEBOUNCE_MS = 500;

// ============ 类型定义 ============

/** 单个 Tab 容器的状态 */
export interface TabContainerState {
  /** Tab 容器 ID（通常是第一个子区块的 ID） */
  id: string;
  /** 子区块 ID 列表 */
  children: string[];
  /** 当前活动标签索引 */
  activeTab: number;
  /** 创建时间戳 */
  createdAt: number;
  /** 最后更新时间戳 */
  updatedAt: number;
}

/** 节点的统一 Tab 配置 */
export interface UnifiedTabConfig {
  /** 版本号 */
  version: number;
  /** Tab 容器映射：tabId -> TabContainerState */
  containers: Record<string, TabContainerState>;
  /** Tab 容器 ID 列表（保持顺序） */
  containerIds: string[];
}

/** Store 状态：nodeType -> UnifiedTabConfig */
type TabStoreState = Map<string, UnifiedTabConfig>;

// ============ 验证函数 ============

/** 验证单个 Tab 容器状态 */
export function validateTabContainerState(state: unknown): state is TabContainerState {
  if (!state || typeof state !== 'object') return false;
  const s = state as Record<string, unknown>;
  
  return (
    typeof s.id === 'string' &&
    Array.isArray(s.children) &&
    s.children.every((c: unknown) => typeof c === 'string') &&
    typeof s.activeTab === 'number' &&
    typeof s.createdAt === 'number' &&
    typeof s.updatedAt === 'number'
  );
}

/** 验证 Tab 配置结构 */
export function validateTabConfig(config: unknown): config is UnifiedTabConfig {
  if (!config || typeof config !== 'object') return false;
  const c = config as Record<string, unknown>;
  
  if (typeof c.version !== 'number') return false;
  if (!c.containers || typeof c.containers !== 'object') return false;
  if (!Array.isArray(c.containerIds)) return false;
  
  for (const state of Object.values(c.containers as Record<string, unknown>)) {
    if (!validateTabContainerState(state)) return false;
  }
  
  return true;
}

// ============ 序列化/反序列化 ============

/** 创建默认 Tab 配置 */
export function createDefaultTabConfig(): UnifiedTabConfig {
  return {
    version: TAB_STATE_VERSION,
    containers: {},
    containerIds: []
  };
}

/** 序列化 Tab 配置为 JSON 字符串 */
export function serializeTabConfig(config: UnifiedTabConfig): string {
  return JSON.stringify(config);
}

/** 反序列化 JSON 字符串为 Tab 配置 */
export function deserializeTabConfig(json: string): UnifiedTabConfig {
  try {
    const parsed = JSON.parse(json);
    if (validateTabConfig(parsed)) {
      return parsed;
    }
    console.warn('[UnifiedTabStore] 配置验证失败，使用默认配置');
    return createDefaultTabConfig();
  } catch (e) {
    console.error('[UnifiedTabStore] 反序列化失败:', e);
    return createDefaultTabConfig();
  }
}

// ============ 边界处理 ============

/** 清理 Tab 状态（过滤无效 ID、去重、修正 activeTab） */
export function sanitizeTabState(
  state: TabContainerState, 
  validBlockIds?: Set<string>
): TabContainerState {
  // 过滤无效 ID（如果提供了有效 ID 集合）
  let children = validBlockIds 
    ? state.children.filter(id => validBlockIds.has(id))
    : state.children;
  
  // 去重（保留第一次出现）
  children = [...new Set(children)];
  
  // 修正 activeTab
  const activeTab = children.length > 0 && state.activeTab >= children.length 
    ? 0 
    : state.activeTab;
  
  return {
    ...state,
    children,
    activeTab,
    updatedAt: Date.now()
  };
}

// ============ 持久化 ============

/** 从 localStorage 安全加载 */
function safeLoadFromStorage(): TabStoreState {
  if (typeof window === 'undefined') return new Map();
  
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return new Map();
    
    const parsed = JSON.parse(stored) as Record<string, unknown>;
    const result = new Map<string, UnifiedTabConfig>();
    
    for (const [nodeType, config] of Object.entries(parsed)) {
      if (validateTabConfig(config)) {
        result.set(nodeType, config);
      } else {
        console.warn(`[UnifiedTabStore] 节点 ${nodeType} 配置无效，跳过`);
      }
    }
    
    return result;
  } catch (e) {
    console.warn('[UnifiedTabStore] 加载失败，使用默认配置:', e);
    return new Map();
  }
}

/** 安全保存到 localStorage */
function safeSaveToStorage(configs: TabStoreState): void {
  if (typeof window === 'undefined') return;
  
  try {
    const obj = Object.fromEntries(configs);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
  } catch (e) {
    if (e instanceof DOMException && e.name === 'QuotaExceededError') {
      console.warn('[UnifiedTabStore] localStorage 配额已满，仅保留内存状态');
    } else {
      console.error('[UnifiedTabStore] 保存失败:', e);
    }
  }
}

// ============ Store 实现 ============

/** 创建 Store 实例 */
const tabStore = new Store<TabStoreState>(new Map());

let isHydrated = false;
let persistTimer: ReturnType<typeof setTimeout> | null = null;

/** 从 localStorage 恢复状态 */
export function hydrateTabStore(): void {
  if (isHydrated || typeof window === 'undefined') return;
  isHydrated = true;
  
  const stored = safeLoadFromStorage();
  if (stored.size > 0) {
    tabStore.setState(() => stored);
  }
}

/** 防抖持久化 */
function schedulePersist(): void {
  if (persistTimer) clearTimeout(persistTimer);
  persistTimer = setTimeout(() => {
    safeSaveToStorage(tabStore.state);
    persistTimer = null;
  }, PERSIST_DEBOUNCE_MS);
}

// 订阅变化并持久化
tabStore.subscribe(() => {
  if (isHydrated) schedulePersist();
});

// ============ API 实现 ============

/** 获取节点的 Tab 配置 */
export function getTabConfig(nodeType: string): UnifiedTabConfig {
  hydrateTabStore();
  return tabStore.state.get(nodeType) ?? createDefaultTabConfig();
}

/** 设置节点的 Tab 配置 */
function setTabConfig(nodeType: string, config: UnifiedTabConfig): void {
  tabStore.setState((prev) => {
    const next = new Map(prev);
    next.set(nodeType, config);
    return next;
  });
}

/** 创建 Tab 容器 */
export function createTab(nodeType: string, blockIds: string[]): string | null {
  if (blockIds.length < 2) {
    console.warn('[UnifiedTabStore] 创建 Tab 需要至少 2 个区块');
    return null;
  }
  
  hydrateTabStore();
  const config = getTabConfig(nodeType);
  
  // 检查是否有区块已在其他 Tab 中
  const usedIds = getUsedBlockIds(nodeType);
  const conflicts = blockIds.filter(id => usedIds.includes(id));
  if (conflicts.length > 0) {
    console.warn('[UnifiedTabStore] 区块已在其他 Tab 中:', conflicts);
    return null;
  }
  
  const tabId = blockIds[0];
  const now = Date.now();
  
  const newContainer: TabContainerState = {
    id: tabId,
    children: blockIds,
    activeTab: 0,
    createdAt: now,
    updatedAt: now
  };
  
  const newConfig: UnifiedTabConfig = {
    ...config,
    containers: { ...config.containers, [tabId]: newContainer },
    containerIds: [...config.containerIds, tabId]
  };
  
  setTabConfig(nodeType, newConfig);
  console.log('[UnifiedTabStore] 创建 Tab:', { nodeType, tabId, children: blockIds });
  
  return tabId;
}

/** 删除 Tab 容器，返回子区块 ID 列表（不含第一个） */
export function removeTab(nodeType: string, tabId: string): string[] {
  hydrateTabStore();
  const config = getTabConfig(nodeType);
  const container = config.containers[tabId];
  
  if (!container) {
    console.warn('[UnifiedTabStore] Tab 不存在:', tabId);
    return [];
  }
  
  const childIds = container.children.slice(1); // 不含第一个（Tab 容器本身）
  
  const newContainers = { ...config.containers };
  delete newContainers[tabId];
  
  const newConfig: UnifiedTabConfig = {
    ...config,
    containers: newContainers,
    containerIds: config.containerIds.filter(id => id !== tabId)
  };
  
  setTabConfig(nodeType, newConfig);
  console.log('[UnifiedTabStore] 删除 Tab:', { nodeType, tabId, restoredChildren: childIds });
  
  return childIds;
}

/** 设置活动标签 */
export function setActiveTab(nodeType: string, tabId: string, index: number): void {
  hydrateTabStore();
  const config = getTabConfig(nodeType);
  const container = config.containers[tabId];
  
  if (!container) return;
  
  // 处理越界
  const safeIndex = index >= container.children.length ? 0 : Math.max(0, index);
  
  const newConfig: UnifiedTabConfig = {
    ...config,
    containers: {
      ...config.containers,
      [tabId]: { ...container, activeTab: safeIndex, updatedAt: Date.now() }
    }
  };
  
  setTabConfig(nodeType, newConfig);
}

/** 添加子区块到 Tab 容器 */
export function addChild(nodeType: string, tabId: string, blockId: string): void {
  hydrateTabStore();
  const config = getTabConfig(nodeType);
  const container = config.containers[tabId];
  
  if (!container) return;
  if (container.children.includes(blockId)) return;
  
  const newConfig: UnifiedTabConfig = {
    ...config,
    containers: {
      ...config.containers,
      [tabId]: {
        ...container,
        children: [...container.children, blockId],
        updatedAt: Date.now()
      }
    }
  };
  
  setTabConfig(nodeType, newConfig);
}

/** 从 Tab 容器移除子区块 */
export function removeChild(nodeType: string, tabId: string, blockId: string): void {
  hydrateTabStore();
  const config = getTabConfig(nodeType);
  const container = config.containers[tabId];
  
  if (!container) return;
  
  const newChildren = container.children.filter(id => id !== blockId);
  
  // 如果只剩一个或没有子区块，删除整个 Tab 容器
  if (newChildren.length < 2) {
    removeTab(nodeType, tabId);
    return;
  }
  
  // 修正 activeTab
  const activeTab = container.activeTab >= newChildren.length 
    ? newChildren.length - 1 
    : container.activeTab;
  
  const newConfig: UnifiedTabConfig = {
    ...config,
    containers: {
      ...config.containers,
      [tabId]: {
        ...container,
        children: newChildren,
        activeTab,
        updatedAt: Date.now()
      }
    }
  };
  
  setTabConfig(nodeType, newConfig);
}

/** 重排序子区块 */
export function reorderChildren(nodeType: string, tabId: string, newOrder: string[]): void {
  hydrateTabStore();
  const config = getTabConfig(nodeType);
  const container = config.containers[tabId];
  
  if (!container) return;
  
  // 找到当前活动区块的 ID
  const activeBlockId = container.children[container.activeTab];
  
  // 更新顺序后，找到活动区块的新索引
  const newActiveTab = newOrder.indexOf(activeBlockId);
  
  const newConfig: UnifiedTabConfig = {
    ...config,
    containers: {
      ...config.containers,
      [tabId]: {
        ...container,
        children: newOrder,
        activeTab: newActiveTab >= 0 ? newActiveTab : 0,
        updatedAt: Date.now()
      }
    }
  };
  
  setTabConfig(nodeType, newConfig);
}

/** 获取所有被 Tab 使用的区块 ID */
export function getUsedBlockIds(nodeType: string): string[] {
  hydrateTabStore();
  const config = getTabConfig(nodeType);
  const ids: string[] = [];
  
  for (const container of Object.values(config.containers)) {
    // 添加除第一个（Tab 容器本身）外的所有子区块
    ids.push(...container.children.slice(1));
  }
  
  return ids;
}

/** 检查区块是否是 Tab 容器 */
export function isTabContainer(nodeType: string, blockId: string): boolean {
  hydrateTabStore();
  const config = getTabConfig(nodeType);
  return config.containerIds.includes(blockId);
}

/** 获取 Tab 容器状态 */
export function getTabState(nodeType: string, tabId: string): TabContainerState | undefined {
  hydrateTabStore();
  const config = getTabConfig(nodeType);
  return config.containers[tabId];
}

/** 订阅配置变化 */
export function subscribeTabConfig(
  nodeType: string, 
  callback: (config: UnifiedTabConfig) => void
): () => void {
  return tabStore.subscribe(() => {
    callback(getTabConfig(nodeType));
  });
}

/** 立即持久化（用于测试或关键操作） */
export function flushPersist(): void {
  if (persistTimer) {
    clearTimeout(persistTimer);
    persistTimer = null;
  }
  safeSaveToStorage(tabStore.state);
}

// ============ 导出 Store（用于调试） ============

export { tabStore };


// ============ 数据迁移 ============

/** 旧版 ModeLayoutState 中的 Tab 状态 */
interface OldTabBlockState {
  activeTab: number;
  children: string[];
}

/** 旧版 ModeLayoutState */
interface OldModeLayoutState {
  gridLayout: unknown[];
  tabStates: Record<string, OldTabBlockState>;
  tabBlocks: string[];
  sizeOverrides: Record<string, unknown>;
}

/** 旧版 NodeConfig */
interface OldNodeConfig {
  nodeType: string;
  fullscreen: OldModeLayoutState;
  normal: OldModeLayoutState;
  updatedAt: number;
}

/** 从旧格式（V0）迁移到新格式 */
export function migrateFromV0(oldConfig: OldNodeConfig): UnifiedTabConfig {
  const mergedContainers: Record<string, TabContainerState> = {};
  const mergedIds: string[] = [];
  const now = Date.now();
  
  // 优先使用 fullscreen 的 Tab 配置
  if (oldConfig.fullscreen?.tabStates) {
    for (const [id, state] of Object.entries(oldConfig.fullscreen.tabStates)) {
      if (state && Array.isArray(state.children) && state.children.length >= 2) {
        mergedContainers[id] = {
          id,
          children: state.children,
          activeTab: typeof state.activeTab === 'number' ? state.activeTab : 0,
          createdAt: now,
          updatedAt: now
        };
        mergedIds.push(id);
      }
    }
  }
  
  // 补充 normal 中独有的 Tab
  if (oldConfig.normal?.tabStates) {
    for (const [id, state] of Object.entries(oldConfig.normal.tabStates)) {
      if (!mergedContainers[id] && state && Array.isArray(state.children) && state.children.length >= 2) {
        mergedContainers[id] = {
          id,
          children: state.children,
          activeTab: typeof state.activeTab === 'number' ? state.activeTab : 0,
          createdAt: now,
          updatedAt: now
        };
        mergedIds.push(id);
      }
    }
  }
  
  return {
    version: TAB_STATE_VERSION,
    containers: mergedContainers,
    containerIds: mergedIds
  };
}

/** 检测并执行必要的迁移 */
export function migrateIfNeeded(data: unknown): TabStoreState {
  if (!data || typeof data !== 'object') return new Map();
  
  const result = new Map<string, UnifiedTabConfig>();
  
  for (const [nodeType, config] of Object.entries(data as Record<string, unknown>)) {
    // 检查是否是新格式（有 version 字段）
    if (config && typeof config === 'object' && 'version' in config) {
      if (validateTabConfig(config)) {
        result.set(nodeType, config);
      }
    } else {
      // 旧格式，需要迁移
      console.log(`[UnifiedTabStore] 迁移节点 ${nodeType} 的 Tab 配置`);
      const migrated = migrateFromV0(config as OldNodeConfig);
      if (migrated.containerIds.length > 0) {
        result.set(nodeType, migrated);
      }
    }
  }
  
  return result;
}

/** 从旧版 nodeLayoutStore 迁移数据 */
export function migrateFromNodeLayoutStore(): void {
  if (typeof window === 'undefined') return;
  
  try {
    const oldStorageKey = 'aestival-node-layouts';
    const stored = localStorage.getItem(oldStorageKey);
    if (!stored) return;
    
    const parsed = JSON.parse(stored) as Record<string, OldNodeConfig>;
    let hasMigrated = false;
    
    for (const [nodeType, oldConfig] of Object.entries(parsed)) {
      // 检查是否有旧的 Tab 数据需要迁移
      const hasOldTabs = 
        (oldConfig.fullscreen?.tabBlocks?.length > 0) ||
        (oldConfig.normal?.tabBlocks?.length > 0);
      
      if (hasOldTabs) {
        const existingConfig = getTabConfig(nodeType);
        // 只有当新 store 中没有数据时才迁移
        if (existingConfig.containerIds.length === 0) {
          const migrated = migrateFromV0(oldConfig);
          if (migrated.containerIds.length > 0) {
            setTabConfig(nodeType, migrated);
            hasMigrated = true;
            console.log(`[UnifiedTabStore] 已迁移 ${nodeType} 的 Tab 配置:`, migrated);
          }
        }
      }
    }
    
    if (hasMigrated) {
      flushPersist();
    }
  } catch (e) {
    console.warn('[UnifiedTabStore] 迁移失败:', e);
  }
}
