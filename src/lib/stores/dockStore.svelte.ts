/**
 * Dock 状态管理
 * 管理浮动 Dock 栏的项目、全屏节点切换
 */
import { writable, get } from 'svelte/store';
import type { NodeDefinition } from '$lib/types';

export interface DockItem {
  id: string;           // 唯一标识
  nodeId: string;       // 对应的 flow 节点 ID
  nodeType: string;     // 节点类型
  label: string;        // 显示名称
  icon: string;         // 图标名称
  isActive: boolean;    // 是否当前激活（全屏显示）
}

export interface DockState {
  items: DockItem[];
  activeItemId: string | null;  // 当前全屏显示的项目
  position: 'bottom' | 'left' | 'right';  // dock 位置
  autoHide: boolean;    // 是否自动隐藏
  visible: boolean;     // 当前是否可见
}

const STORAGE_KEY = 'aestivus_dock_state';

function loadState(): DockState {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      return { ...getDefaultState(), ...parsed };
    }
  } catch (e) {
    console.warn('加载 Dock 状态失败:', e);
  }
  return getDefaultState();
}

function getDefaultState(): DockState {
  return {
    items: [],
    activeItemId: null,
    position: 'bottom',
    autoHide: false,
    visible: true
  };
}

function createDockStore() {
  const initial = loadState();
  const { subscribe, set, update } = writable<DockState>(initial);

  // 自动保存
  subscribe(state => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      console.warn('保存 Dock 状态失败:', e);
    }
  });

  return {
    subscribe,

    /** 添加项目到 Dock */
    addItem(nodeId: string, nodeType: string, label: string, icon: string) {
      update(s => {
        // 检查是否已存在
        if (s.items.some(item => item.nodeId === nodeId)) {
          return s;
        }
        const newItem: DockItem = {
          id: `dock-${Date.now()}`,
          nodeId,
          nodeType,
          label,
          icon,
          isActive: false
        };
        return { ...s, items: [...s.items, newItem] };
      });
    },

    /** 从 Dock 移除项目 */
    removeItem(nodeId: string) {
      update(s => {
        const newItems = s.items.filter(item => item.nodeId !== nodeId);
        const newActiveId = s.activeItemId === nodeId ? null : s.activeItemId;
        return { ...s, items: newItems, activeItemId: newActiveId };
      });
    },

    /** 激活项目（全屏显示） */
    activateItem(nodeId: string) {
      update(s => {
        const items = s.items.map(item => ({
          ...item,
          isActive: item.nodeId === nodeId
        }));
        return { ...s, items, activeItemId: nodeId };
      });
    },

    /** 关闭当前激活的项目 */
    deactivate() {
      update(s => {
        const items = s.items.map(item => ({ ...item, isActive: false }));
        return { ...s, items, activeItemId: null };
      });
    },

    /** 切换到下一个项目 */
    nextItem() {
      update(s => {
        if (s.items.length === 0) return s;
        const currentIndex = s.items.findIndex(item => item.nodeId === s.activeItemId);
        const nextIndex = (currentIndex + 1) % s.items.length;
        const nextItem = s.items[nextIndex];
        const items = s.items.map(item => ({
          ...item,
          isActive: item.nodeId === nextItem.nodeId
        }));
        return { ...s, items, activeItemId: nextItem.nodeId };
      });
    },

    /** 切换到上一个项目 */
    prevItem() {
      update(s => {
        if (s.items.length === 0) return s;
        const currentIndex = s.items.findIndex(item => item.nodeId === s.activeItemId);
        const prevIndex = currentIndex <= 0 ? s.items.length - 1 : currentIndex - 1;
        const prevItem = s.items[prevIndex];
        const items = s.items.map(item => ({
          ...item,
          isActive: item.nodeId === prevItem.nodeId
        }));
        return { ...s, items, activeItemId: prevItem.nodeId };
      });
    },

    /** 检查节点是否在 Dock 中 */
    hasItem(nodeId: string): boolean {
      const state = get({ subscribe });
      return state.items.some(item => item.nodeId === nodeId);
    },

    /** 设置 Dock 位置 */
    setPosition(position: 'bottom' | 'left' | 'right') {
      update(s => ({ ...s, position }));
    },

    /** 切换自动隐藏 */
    toggleAutoHide() {
      update(s => ({ ...s, autoHide: !s.autoHide }));
    },

    /** 设置可见性 */
    setVisible(visible: boolean) {
      update(s => ({ ...s, visible }));
    },

    /** 重置 */
    reset() {
      set(getDefaultState());
    }
  };
}

export const dockStore = createDockStore();
