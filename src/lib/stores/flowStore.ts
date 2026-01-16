import { writable, derived } from 'svelte/store';
import type { FlowNode, FlowEdge, Flow } from '$lib/types';

export interface FlowState {
  id: string | null;
  name: string;
  description: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
  isDirty: boolean;
  selectedNodeId: string | null;
  layoutTrigger?: number;
}

const initialState: FlowState = {
  id: null,
  name: '未命名流程',
  description: '',
  nodes: [],
  edges: [],
  isDirty: false,
  selectedNodeId: null
};

function createFlowStore() {
  const { subscribe, set, update } = writable<FlowState>(initialState);

  return {
    subscribe,

    load(flow: Flow) {
      set({
        id: flow.id,
        name: flow.name,
        description: flow.description || '',
        nodes: flow.nodes,
        edges: flow.edges,
        isDirty: false,
        selectedNodeId: null
      });
    },

    setNodes(nodes: FlowNode[]) {
      update(state => ({ ...state, nodes, isDirty: true }));
    },

    setEdges(edges: FlowEdge[]) {
      update(state => ({ ...state, edges, isDirty: true }));
    },

    addNode(node: FlowNode) {
      update(state => ({
        ...state,
        nodes: [...state.nodes, node],
        isDirty: true
      }));
    },

    updateNode(id: string, data: Partial<FlowNode>) {
      update(state => ({
        ...state,
        nodes: state.nodes.map(n => (n.id === id ? { ...n, ...data } : n)),
        isDirty: true
      }));
    },

    duplicateNode(id: string) {
      update(state => {
        const nodeToDuplicate = state.nodes.find(n => n.id === id);
        if (!nodeToDuplicate) return state;

        const newNodeId = `node-${crypto.randomUUID()}`;
        const newNode = {
          ...nodeToDuplicate,
          id: newNodeId,
          position: {
            x: nodeToDuplicate.position.x + 40,
            y: nodeToDuplicate.position.y + 40
          },
          selected: true
        };

        return {
          ...state,
          nodes: [...state.nodes.map(n => ({ ...n, selected: false })), newNode],
          isDirty: true,
          selectedNodeId: newNodeId
        };
      });
    },

    updateNodeData(id: string, data: Partial<FlowNode['data']>) {
      update(state => ({
        ...state,
        nodes: state.nodes.map(n =>
          n.id === id ? { ...n, data: { ...n.data, ...data } } : n
        ),
        isDirty: true
      }));
    },

    removeNode(id: string) {
      update(state => ({
        ...state,
        nodes: state.nodes.filter(n => n.id !== id),
        edges: state.edges.filter(e => e.source !== id && e.target !== id),
        isDirty: true,
        selectedNodeId: state.selectedNodeId === id ? null : state.selectedNodeId
      }));
    },

    addEdge(edge: FlowEdge) {
      update(state => ({
        ...state,
        edges: [...state.edges, edge],
        isDirty: true
      }));
    },

    removeEdge(id: string) {
      update(state => ({
        ...state,
        edges: state.edges.filter(e => e.id !== id),
        isDirty: true
      }));
    },

    selectNode(id: string | null) {
      update(state => ({ ...state, selectedNodeId: id }));
    },

    setName(name: string) {
      update(state => ({ ...state, name, isDirty: true }));
    },

    markSaved() {
      update(state => ({ ...state, isDirty: false }));
    },

    reset() {
      set(initialState);
    },

    triggerLayout() {
      update(state => ({ ...state, layoutTrigger: Date.now() }));
    },

    getState(): FlowState {
      let currentState: FlowState = initialState;
      const unsubscribe = subscribe(s => (currentState = s));
      unsubscribe();
      return currentState;
    },

    toFlow(): Flow {
      const state = this.getState();
      return {
        id: state.id || crypto.randomUUID(),
        name: state.name,
        description: state.description,
        nodes: state.nodes,
        edges: state.edges,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
    }
  };
}

export const flowStore = createFlowStore();

export const selectedNode = derived(flowStore, $flow =>
  $flow.selectedNodeId ? $flow.nodes.find(n => n.id === $flow.selectedNodeId) : null
);
