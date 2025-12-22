import type { Node, Edge } from '@xyflow/svelte';

export interface FlowNode extends Node {
  data: NodeData;
}

export interface FlowEdge extends Edge {
  animated?: boolean;
}

export interface NodeData {
  label: string;
  toolName?: string;
  category?: NodeCategory;
  config?: Record<string, unknown>;
  params?: Record<string, any>;
  status?: NodeStatus;
  progress?: number;
  [key: string]: unknown;
}

export type NodeCategory = 'input' | 'tool' | 'output' | 'control';
export type NodeStatus = 'idle' | 'running' | 'completed' | 'error' | 'skipped';

export interface Flow {
  id: string;
  name: string;
  description?: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
  createdAt: string;
  updatedAt: string;
}

export interface NodeDefinition {
  type: string;
  category: NodeCategory;
  label: string;
  description: string;
  icon: string;
  inputs: string[];
  outputs: string[];
  configSchema?: Record<string, SchemaField>;
}

export interface SchemaField {
  type: 'string' | 'number' | 'boolean' | 'select' | 'path' | 'array';
  label?: string;
  description?: string;
  required?: boolean;
  default?: unknown;
  options?: string[];
}
