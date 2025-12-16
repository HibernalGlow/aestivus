/**
 * 布局预设管理
 * 支持保存、加载、导出布局配置
 */
import type { GridItem } from '$lib/components/ui/dashboard-grid';

// localStorage key
const PRESETS_KEY = 'aestival-layout-presets';

/** 布局预设 */
export interface LayoutPreset {
  id: string;
  name: string;
  nodeType: string;  // 适用的节点类型，如 'trename', 'repacku'
  layout: GridItem[];
  createdAt: number;
  isBuiltin?: boolean;  // 是否为内置预设
}

/** 内置预设 */
const BUILTIN_PRESETS: LayoutPreset[] = [
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
  }
];

/** 从 localStorage 加载用户预设 */
function loadUserPresets(): LayoutPreset[] {
  if (typeof window === 'undefined') return [];
  try {
    const stored = localStorage.getItem(PRESETS_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

/** 保存用户预设到 localStorage */
function saveUserPresets(presets: LayoutPreset[]): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(PRESETS_KEY, JSON.stringify(presets));
  } catch (e) {
    console.warn('[layoutPresets] Failed to save:', e);
  }
}

/** 获取所有预设（内置 + 用户） */
export function getAllPresets(nodeType?: string): LayoutPreset[] {
  const userPresets = loadUserPresets();
  const all = [...BUILTIN_PRESETS, ...userPresets];
  return nodeType ? all.filter(p => p.nodeType === nodeType) : all;
}

/** 获取单个预设 */
export function getPreset(id: string): LayoutPreset | undefined {
  return getAllPresets().find(p => p.id === id);
}

/** 保存新预设 */
export function savePreset(name: string, nodeType: string, layout: GridItem[]): LayoutPreset {
  const preset: LayoutPreset = {
    id: `${nodeType}-${Date.now()}`,
    name,
    nodeType,
    layout: JSON.parse(JSON.stringify(layout)), // 深拷贝
    createdAt: Date.now()
  };
  const userPresets = loadUserPresets();
  userPresets.push(preset);
  saveUserPresets(userPresets);
  return preset;
}

/** 删除用户预设 */
export function deletePreset(id: string): boolean {
  const userPresets = loadUserPresets();
  const index = userPresets.findIndex(p => p.id === id);
  if (index === -1) return false;
  userPresets.splice(index, 1);
  saveUserPresets(userPresets);
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
    
    const userPresets = loadUserPresets();
    userPresets.push(preset);
    saveUserPresets(userPresets);
    return preset;
  } catch {
    return null;
  }
}
