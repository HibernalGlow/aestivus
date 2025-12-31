/**
 * 节点状态管理 - 使用 Svelte 5 runes 实现响应式共享状态
 * 
 * 核心思想：
 * - 每个 nodeId 对应一个共享的响应式状态对象
 * - 节点模式和全屏模式的组件实例共享同一个状态对象
 * - 状态变化自动同步，无需手动订阅
 * 
 * 用法：
 * ```ts
 * // 在组件中定义状态接口
 * interface MyState {
 *   phase: 'idle' | 'running';
 *   count: number;
 * }
 * 
 * // 获取共享状态（两个实例获取同一个对象）
 * const state = getNodeState<MyState>(nodeId, { phase: 'idle', count: 0 });
 * 
 * // 直接读写属性，自动同步到另一个实例
 * state.phase = 'running';
 * state.count++;
 * ```
 */

// 存储所有节点的共享状态（使用 $state 使整个对象响应式）
const nodeStates: Record<string, object> = $state({});

// localStorage key
const STORAGE_KEY = 'aestival-node-states-v2';

// 最大存储大小（字节）
const MAX_STORAGE_SIZE = 2 * 1024 * 1024;

/**
 * 从 localStorage 加载状态
 */
function loadFromStorage(): Record<string, object> {
  if (typeof window === 'undefined') return {};
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return {};
    return JSON.parse(stored);
  } catch {
    return {};
  }
}

/**
 * 清理大型数据字段，只保留必要的状态
 */
function cleanStateForStorage(state: unknown): unknown {
  if (state === null || state === undefined) return state;
  if (typeof state !== 'object') return state;
  if (Array.isArray(state)) {
    if (state.length > 100) return state.slice(0, 100);
    return state.map(cleanStateForStorage);
  }
  
  const cleaned: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(state as Record<string, unknown>)) {
    // 跳过大型数据字段和临时字段
    if (key.startsWith('_') || 
        key === 'scanResult' || key === 'previewData' || 
        key === 'output' || key === 'result' || key === 'items' ||
        key === 'fileList' || key === 'archives' || key === 'folders' ||
        key === 'netHistory' || key === 'cpuHistory' || key === 'ws' ||
        key === 'abortController' || key === 'layoutRenderer') {
      continue;
    }
    // logs 只保留最近 30 条
    if (key === 'logs' && Array.isArray(value)) {
      cleaned[key] = value.slice(-30);
      continue;
    }
    // 跳过过长的字符串
    if (typeof value === 'string' && value.length > 1000) {
      cleaned[key] = value.slice(0, 1000);
      continue;
    }
    // 跳过函数
    if (typeof value === 'function') continue;
    
    cleaned[key] = cleanStateForStorage(value);
  }
  return cleaned;
}

/**
 * 保存所有状态到 localStorage（防抖）
 */
let saveTimer: ReturnType<typeof setTimeout> | null = null;

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    if (typeof window === 'undefined') return;
    try {
      const toSave: Record<string, unknown> = {};
      for (const nodeId of Object.keys(nodeStates)) {
        toSave[nodeId] = cleanStateForStorage(JSON.parse(JSON.stringify(nodeStates[nodeId])));
      }
      
      const json = JSON.stringify(toSave);
      if (json.length > MAX_STORAGE_SIZE) {
        // 只保留最近 20 个节点
        const entries = Object.entries(toSave);
        const trimmed = Object.fromEntries(entries.slice(-20));
        localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
      } else {
        localStorage.setItem(STORAGE_KEY, json);
      }
    } catch (e) {
      console.warn('[nodeState] 保存失败:', e);
    }
  }, 500);
}

// 初始化标记
let initialized = false;

function ensureInitialized() {
  if (initialized || typeof window === 'undefined') return;
  initialized = true;
  
  const stored = loadFromStorage();
  for (const [nodeId, data] of Object.entries(stored)) {
    if (!(nodeId in nodeStates) && data && typeof data === 'object') {
      nodeStates[nodeId] = data as object;
    }
  }
}

/**
 * 获取或创建节点的共享响应式状态
 * 
 * 重要：返回的是同一个响应式对象，两个组件实例共享
 * 
 * @param nodeId 节点 ID
 * @param defaultState 默认状态（首次创建时使用）
 * @returns 共享的响应式状态对象
 */
export function getNodeState<T extends object>(nodeId: string, defaultState: T): T {
  ensureInitialized();
  
  if (!(nodeId in nodeStates)) {
    // 创建新的响应式状态，合并已保存的数据和默认值
    const saved = loadFromStorage()[nodeId] as Partial<T> | undefined;
    const merged = { ...defaultState, ...saved };
    nodeStates[nodeId] = merged;
  }
  
  return nodeStates[nodeId] as T;
}

/**
 * 更新节点状态（合并）并触发保存
 */
export function updateNodeState<T extends object>(nodeId: string, partial: Partial<T>): void {
  if (nodeId in nodeStates) {
    Object.assign(nodeStates[nodeId], partial);
    scheduleSave();
  }
}

/**
 * 强制保存当前节点状态
 */
export function saveNodeState(_nodeId: string): void {
  scheduleSave();
}

/**
 * 删除节点状态
 */
export function deleteNodeState(nodeId: string): void {
  delete nodeStates[nodeId];
  scheduleSave();
}

/**
 * 清空所有状态
 */
export function clearAllNodeStates(): void {
  for (const key of Object.keys(nodeStates)) {
    delete nodeStates[key];
  }
  if (typeof window !== 'undefined') {
    localStorage.removeItem(STORAGE_KEY);
  }
}

