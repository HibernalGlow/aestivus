/**
 * 全屏节点状态管理
 * 用于控制节点的全屏显示
 */
import { writable } from 'svelte/store';

export interface FullscreenNodeState {
  isOpen: boolean;
  nodeType: string | null;
  nodeId: string | null;
  nodeData: Record<string, unknown> | null;
}

const initialState: FullscreenNodeState = {
  isOpen: false,
  nodeType: null,
  nodeId: null,
  nodeData: null
};

function createFullscreenNodeStore() {
  const { subscribe, set, update } = writable<FullscreenNodeState>(initialState);

  return {
    subscribe,
    
    /** 打开全屏节点 */
    open(nodeType: string, nodeId?: string, nodeData?: Record<string, unknown>) {
      set({
        isOpen: true,
        nodeType,
        nodeId: nodeId || `fullscreen-${Date.now()}`,
        nodeData: nodeData || {}
      });
    },
    
    /** 关闭全屏节点 */
    close() {
      set(initialState);
    },
    
    /** 更新节点数据 */
    updateData(data: Partial<Record<string, unknown>>) {
      update(state => ({
        ...state,
        nodeData: { ...state.nodeData, ...data }
      }));
    }
  };
}

export const fullscreenNodeStore = createFullscreenNodeStore();
