/**
 * 布局预设管理
 * 使用后端 SQLModel + SQLite 存储
 */
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import * as storageClient from '$lib/services/storageClient';

// 旧的 localStorage key（用于迁移检测）
const LEGACY_PRESETS_KEY = 'aestival-layout-presets';
const LEGACY_DEFAULT_KEY = 'aestival-default-preset';

/** 布局模式类型 */
export type PresetMode = 'fullscreen' | 'normal';

/** Tab 分组配置（与 nodeLayoutStore 中的 TabGroup 保持一致） */
export interface PresetTabGroup {
  id: string;
  blockIds: string[];
  activeIndex: number;
}

/** 布局预设 */
export interface LayoutPreset {
  id: string;
  name: string;
  nodeType: string;
  layout: GridItem[];
  tabGroups?: PresetTabGroup[];
  createdAt: number;
  isBuiltin?: boolean;
}

/** 内置预设 */
const BUILTIN_PRESETS: LayoutPreset[] = [
  // ========== TrenameNode 预设 ==========
  {
    id: 'trename-default',
    name: '默认布局',
    nodeType: 'trename',
    layout: [
      { id: 'path', x: 0, y: 0, w: 2, h: 2, minW: 2, minH: 2 },
      { id: 'operation', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'stats', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'importExport', x: 0, y: 2, w: 2, h: 1, minW: 2, minH: 1 },
      { id: 'tree', x: 0, y: 3, w: 3, h: 4, minW: 2, minH: 2 },
      { id: 'log', x: 3, y: 2, w: 1, h: 5, minW: 1, minH: 2 }
    ],
    createdAt: 0,
    isBuiltin: true
  },
  {
    id: 'trename-compact',
    name: '紧凑布局',
    nodeType: 'trename',
    layout: [
      { id: 'path', x: 0, y: 0, w: 2, h: 1, minW: 2, minH: 1 },
      { id: 'operation', x: 2, y: 0, w: 1, h: 1, minW: 1, minH: 1 },
      { id: 'stats', x: 3, y: 0, w: 1, h: 1, minW: 1, minH: 1 },
      { id: 'importExport', x: 0, y: 1, w: 2, h: 1, minW: 2, minH: 1 },
      { id: 'tree', x: 0, y: 2, w: 2, h: 3, minW: 2, minH: 2 },
      { id: 'log', x: 2, y: 1, w: 2, h: 4, minW: 1, minH: 2 }
    ],
    createdAt: 0,
    isBuiltin: true
  },
  {
    id: 'trename-tree-focus',
    name: '文件树优先',
    nodeType: 'trename',
    layout: [
      { id: 'tree', x: 0, y: 0, w: 3, h: 6, minW: 2, minH: 2 },
      { id: 'path', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'operation', x: 3, y: 2, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'stats', x: 3, y: 4, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'importExport', x: 0, y: 6, w: 2, h: 1, minW: 2, minH: 1 },
      { id: 'log', x: 2, y: 6, w: 2, h: 1, minW: 1, minH: 1 }
    ],
    createdAt: 0,
    isBuiltin: true
  },
  // ========== RepackuNode 预设 ==========
  {
    id: 'repacku-default',
    name: '默认布局',
    nodeType: 'repacku',
    layout: [
      { id: 'path', x: 0, y: 0, w: 2, h: 3, minW: 2, minH: 2 },
      { id: 'operation', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'stats', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'progress', x: 2, y: 2, w: 2, h: 1, minW: 2, minH: 1 },
      { id: 'tree', x: 0, y: 3, w: 3, h: 4, minW: 2, minH: 2 },
      { id: 'log', x: 3, y: 3, w: 1, h: 4, minW: 1, minH: 2 }
    ],
    createdAt: 0,
    isBuiltin: true
  },
  {
    id: 'repacku-compact',
    name: '紧凑布局',
    nodeType: 'repacku',
    layout: [
      { id: 'path', x: 0, y: 0, w: 2, h: 2, minW: 2, minH: 2 },
      { id: 'operation', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
      { id: 'stats', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
      { id: 'progress', x: 0, y: 2, w: 4, h: 1, minW: 2, minH: 1 },
      { id: 'tree', x: 0, y: 3, w: 2, h: 3, minW: 2, minH: 2 },
      { id: 'log', x: 2, y: 3, w: 2, h: 3, minW: 1, minH: 2 }
    ],
    createdAt: 0,
    isBuiltin: true
  },
  {
    id: 'repacku-tree-focus',
    name: '文件树优先',
    nodeType: 'repacku',
    layout: [
      { id: 'tree', x: 0, y: 0, w: 3, h: 6, minW: 2, minH: 2 },
      { id: 'path', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'operation', x: 3, y: 2, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'stats', x: 3, y: 4, w: 1, h: 2, minW: 1, minH: 2 },
      { id: 'progress', x: 0, y: 6, w: 2, h: 1, minW: 2, minH: 1 },
      { id: 'log', x: 2, y: 6, w: 2, h: 1, minW: 1, minH: 1 }
    ],
    createdAt: 0,
    isBuiltin: true
  }
];

// ============ 内存缓存 ============

let cachedUserPresets: LayoutPreset[] | null = null;
let cachedDefaults: Map<string, { fullscreen?: string; normal?: string }> = new Map();

/** 转换后端格式到前端格式 */
function convertFromBackend(preset: storageClient.LayoutPresetBackend): LayoutPreset {
  return {
    id: preset.id,
    name: preset.name,
    nodeType: preset.nodeType,
    layout: preset.layout,
    tabGroups: preset.tabGroups,
    createdAt: preset.createdAt,
    isBuiltin: preset.isBuiltin
  };
}

// ============ 预设 API ============

/** 获取所有预设（内置 + 用户，异步） */
export async function getAllPresetsAsync(nodeType?: string): Promise<LayoutPreset[]> {
  try {
    const backendPresets = await storageClient.getPresets(nodeType);
    const userPresets = backendPresets.map(convertFromBackend);
    cachedUserPresets = userPresets;
    
    const all = [...BUILTIN_PRESETS, ...userPresets];
    return nodeType ? all.filter(p => p.nodeType === nodeType) : all;
  } catch (error) {
    console.error('[layoutPresets] 获取预设失败:', error);
    // 降级：返回内置预设
    return nodeType ? BUILTIN_PRESETS.filter(p => p.nodeType === nodeType) : [...BUILTIN_PRESETS];
  }
}

/** 获取所有预设（同步，使用缓存） */
export function getAllPresets(nodeType?: string): LayoutPreset[] {
  const userPresets = cachedUserPresets || [];
  const all = [...BUILTIN_PRESETS, ...userPresets];
  return nodeType ? all.filter(p => p.nodeType === nodeType) : all;
}

/** 获取单个预设 */
export function getPreset(id: string): LayoutPreset | undefined {
  // 先查内置
  const builtin = BUILTIN_PRESETS.find(p => p.id === id);
  if (builtin) return builtin;
  
  // 再查缓存
  return cachedUserPresets?.find(p => p.id === id);
}

/** 保存新预设（异步） */
export async function savePresetAsync(
  name: string, 
  nodeType: string, 
  layout: GridItem[], 
  tabGroups?: PresetTabGroup[]
): Promise<LayoutPreset | null> {
  const id = `${nodeType}-${Date.now()}`;
  
  const result = await storageClient.createPreset({
    id,
    name,
    nodeType,
    layout: JSON.parse(JSON.stringify(layout)),
    tabGroups: tabGroups ? JSON.parse(JSON.stringify(tabGroups)) : undefined,
    isBuiltin: false
  });
  
  if (result) {
    // 刷新缓存
    cachedUserPresets = null;
    return convertFromBackend(result);
  }
  
  return null;
}

/** 保存新预设（同步兼容，内部异步） */
export function savePreset(
  name: string, 
  nodeType: string, 
  layout: GridItem[], 
  tabGroups?: PresetTabGroup[]
): LayoutPreset {
  const preset: LayoutPreset = {
    id: `${nodeType}-${Date.now()}`,
    name,
    nodeType,
    layout: JSON.parse(JSON.stringify(layout)),
    tabGroups: tabGroups ? JSON.parse(JSON.stringify(tabGroups)) : undefined,
    createdAt: Date.now()
  };
  
  // 异步保存到后端
  storageClient.createPreset({
    id: preset.id,
    name: preset.name,
    nodeType: preset.nodeType,
    layout: preset.layout,
    tabGroups: preset.tabGroups,
    isBuiltin: false
  }).then(() => {
    cachedUserPresets = null;
  }).catch(console.error);
  
  // 立即更新缓存
  if (cachedUserPresets) {
    cachedUserPresets.push(preset);
  }
  
  return preset;
}

/** 删除用户预设 */
export async function deletePresetAsync(id: string): Promise<boolean> {
  const success = await storageClient.deletePreset(id);
  if (success) {
    cachedUserPresets = null;
  }
  return success;
}

/** 删除用户预设（同步兼容） */
export function deletePreset(id: string): boolean {
  // 异步删除
  storageClient.deletePreset(id).then(() => {
    cachedUserPresets = null;
  }).catch(console.error);
  
  // 立即从缓存移除
  if (cachedUserPresets) {
    const index = cachedUserPresets.findIndex(p => p.id === id);
    if (index !== -1) {
      cachedUserPresets.splice(index, 1);
      return true;
    }
  }
  
  return true;
}

/** 重命名用户预设 */
export function renamePreset(id: string, newName: string): boolean {
  // 异步更新
  storageClient.updatePreset(id, { name: newName }).then(() => {
    cachedUserPresets = null;
  }).catch(console.error);
  
  // 立即更新缓存
  if (cachedUserPresets) {
    const preset = cachedUserPresets.find(p => p.id === id);
    if (preset) {
      preset.name = newName;
      return true;
    }
  }
  
  return true;
}

/** 更新用户预设的布局 */
export function updatePreset(id: string, layout: GridItem[], tabGroups?: PresetTabGroup[]): boolean {
  // 异步更新
  storageClient.updatePreset(id, { 
    layout: JSON.parse(JSON.stringify(layout)),
    tabGroups: tabGroups ? JSON.parse(JSON.stringify(tabGroups)) : undefined
  }).then(() => {
    cachedUserPresets = null;
  }).catch(console.error);
  
  // 立即更新缓存
  if (cachedUserPresets) {
    const preset = cachedUserPresets.find(p => p.id === id);
    if (preset) {
      preset.layout = JSON.parse(JSON.stringify(layout));
      preset.tabGroups = tabGroups ? JSON.parse(JSON.stringify(tabGroups)) : undefined;
      return true;
    }
  }
  
  return true;
}

/** 导出预设为 JSON 字符串 */
export function exportPreset(id: string): string | null {
  const preset = getPreset(id);
  if (!preset) return null;
  return JSON.stringify(preset, null, 2);
}

/** 导入预设 */
export function importPreset(json: string): LayoutPreset | null {
  try {
    const preset = JSON.parse(json) as LayoutPreset;
    if (!preset.name || !preset.nodeType || !Array.isArray(preset.layout)) {
      return null;
    }
    
    // 生成新 ID 避免冲突
    preset.id = `${preset.nodeType}-imported-${Date.now()}`;
    preset.createdAt = Date.now();
    preset.isBuiltin = false;
    
    // 异步保存
    storageClient.createPreset({
      id: preset.id,
      name: preset.name,
      nodeType: preset.nodeType,
      layout: preset.layout,
      tabGroups: preset.tabGroups,
      isBuiltin: false
    }).then(() => {
      cachedUserPresets = null;
    }).catch(console.error);
    
    // 立即更新缓存
    if (cachedUserPresets) {
      cachedUserPresets.push(preset);
    }
    
    return preset;
  } catch {
    return null;
  }
}

// ============ 默认预设 API ============

/** 设置默认预设（指定模式） */
export async function setDefaultPresetAsync(nodeType: string, presetId: string, mode: PresetMode): Promise<void> {
  const current = cachedDefaults.get(nodeType) || {};
  current[mode] = presetId;
  
  await storageClient.setDefaults(nodeType, {
    fullscreenPresetId: current.fullscreen,
    normalPresetId: current.normal
  });
  
  cachedDefaults.set(nodeType, current);
}

/** 设置默认预设（同步兼容） */
export function setDefaultPreset(nodeType: string, presetId: string, mode: PresetMode): void {
  const current = cachedDefaults.get(nodeType) || {};
  current[mode] = presetId;
  cachedDefaults.set(nodeType, current);
  
  // 异步保存
  storageClient.setDefaults(nodeType, {
    fullscreenPresetId: current.fullscreen,
    normalPresetId: current.normal
  }).catch(console.error);
}

/** 取消默认预设（指定模式） */
export function unsetDefaultPreset(nodeType: string, mode: PresetMode): void {
  const current = cachedDefaults.get(nodeType);
  if (current) {
    delete current[mode];
    
    // 异步保存
    storageClient.setDefaults(nodeType, {
      fullscreenPresetId: current.fullscreen || null,
      normalPresetId: current.normal || null
    }).catch(console.error);
  }
}

/** 获取默认预设 ID（指定模式） */
export function getDefaultPresetId(nodeType: string, mode?: PresetMode): string | null {
  const config = cachedDefaults.get(nodeType);
  if (!config) return null;
  
  if (mode) {
    return config[mode] || null;
  }
  
  return config.fullscreen || config.normal || null;
}

/** 获取预设的默认模式列表 */
export function getPresetDefaultModes(nodeType: string, presetId: string): PresetMode[] {
  const config = cachedDefaults.get(nodeType);
  if (!config) return [];
  
  const modes: PresetMode[] = [];
  if (config.fullscreen === presetId) modes.push('fullscreen');
  if (config.normal === presetId) modes.push('normal');
  return modes;
}

/** 获取默认预设 */
export function getDefaultPreset(nodeType: string, mode?: PresetMode): LayoutPreset | null {
  const defaultId = getDefaultPresetId(nodeType, mode);
  if (defaultId) {
    const preset = getPreset(defaultId);
    if (preset) return preset;
  }
  
  // 返回第一个内置预设作为默认
  return BUILTIN_PRESETS.find(p => p.nodeType === nodeType) || null;
}

// ============ 初始化 ============

/** 从后端加载默认预设配置 */
export async function loadDefaultsFromBackend(nodeTypes: string[]): Promise<void> {
  for (const nodeType of nodeTypes) {
    try {
      const defaults = await storageClient.getDefaults(nodeType);
      if (defaults) {
        cachedDefaults.set(nodeType, {
          fullscreen: defaults.fullscreenPresetId || undefined,
          normal: defaults.normalPresetId || undefined
        });
      }
    } catch (error) {
      console.error(`[layoutPresets] 加载 ${nodeType} 默认预设失败:`, error);
    }
  }
}

/** 初始化预设系统（从后端加载） */
export async function initPresets(): Promise<void> {
  try {
    // 加载用户预设
    const backendPresets = await storageClient.getPresets();
    cachedUserPresets = backendPresets.map(convertFromBackend);
    
    // 加载默认预设配置
    const nodeTypes = [...new Set([
      ...BUILTIN_PRESETS.map(p => p.nodeType),
      ...cachedUserPresets.map(p => p.nodeType)
    ])];
    await loadDefaultsFromBackend(nodeTypes);
    
    console.log(`[layoutPresets] 已加载 ${cachedUserPresets.length} 个用户预设`);
  } catch (error) {
    console.error('[layoutPresets] 初始化失败:', error);
  }
}

// ============ 存储管理 ============

/** 获取用户预设数量 */
export function getPresetsInfo(): { count: number; sizeKB: number } {
  return {
    count: cachedUserPresets?.length || 0,
    sizeKB: 0  // 后端存储无需计算大小
  };
}

/** 清理所有用户预设 */
export async function clearAllUserPresets(): Promise<void> {
  if (cachedUserPresets) {
    for (const preset of cachedUserPresets) {
      await storageClient.deletePreset(preset.id);
    }
  }
  cachedUserPresets = [];
  
  // 清理旧的 localStorage
  if (typeof window !== 'undefined') {
    localStorage.removeItem(LEGACY_PRESETS_KEY);
    localStorage.removeItem(LEGACY_DEFAULT_KEY);
  }
  
  console.log('[layoutPresets] 已清理所有用户预设');
}

/** 清理指定节点类型的用户预设 */
export async function clearPresetsForNodeType(nodeType: string): Promise<number> {
  let count = 0;
  
  if (cachedUserPresets) {
    const toDelete = cachedUserPresets.filter(p => p.nodeType === nodeType);
    for (const preset of toDelete) {
      await storageClient.deletePreset(preset.id);
      count++;
    }
    cachedUserPresets = cachedUserPresets.filter(p => p.nodeType !== nodeType);
  }
  
  if (count > 0) {
    console.log(`[layoutPresets] 清理了 ${count} 个 ${nodeType} 预设`);
  }
  
  return count;
}
