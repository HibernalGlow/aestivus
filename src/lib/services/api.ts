import type { Flow } from '$lib/types';

const API_BASE = 'http://localhost:8009/v1';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    },
    ...options
  });
  
  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
  }
  
  return res.json();
}

export const api = {
  // 流程管理
  async getFlows(): Promise<Flow[]> {
    return request('/flows');
  },

  async getFlow(id: string): Promise<Flow> {
    return request(`/flows/${id}`);
  },

  async createFlow(flow: Partial<Flow>): Promise<Flow> {
    return request('/flows', {
      method: 'POST',
      body: JSON.stringify(flow)
    });
  },

  async updateFlow(id: string, flow: Partial<Flow>): Promise<Flow> {
    return request(`/flows/${id}`, {
      method: 'PUT',
      body: JSON.stringify(flow)
    });
  },

  async deleteFlow(id: string): Promise<void> {
    await request(`/flows/${id}`, { method: 'DELETE' });
  },

  // 任务执行
  async executeFlow(flowId: string, inputs?: Record<string, unknown>): Promise<{ taskId: string }> {
    return request('/tasks/execute', {
      method: 'POST',
      body: JSON.stringify({ flowId, inputs })
    });
  },

  async getTask(taskId: string): Promise<unknown> {
    return request(`/tasks/${taskId}`);
  },

  async cancelTask(taskId: string): Promise<void> {
    await request(`/tasks/${taskId}/cancel`, { method: 'POST' });
  },

  // 工具管理
  async getTools(): Promise<unknown[]> {
    return request('/tools');
  },

  async getToolSchema(toolName: string): Promise<unknown> {
    return request(`/tools/${toolName}/schema`);
  },

  async getToolDefaults(toolName: string): Promise<{ parameters: Record<string, unknown> }> {
    return request(`/tools/${toolName}/defaults`);
  },

  async updateToolDefaults(toolName: string, parameters: Record<string, unknown>): Promise<void> {
    await request(`/tools/${toolName}/defaults`, {
      method: 'PUT',
      body: JSON.stringify({ parameters })
    });
  },

  async getToolPresets(toolName: string): Promise<unknown[]> {
    return request(`/tools/${toolName}/presets`);
  },

  async createPreset(data: {
    name: string;
    description: string;
    tool_name: string;
    parameters: Record<string, unknown>;
  }): Promise<void> {
    await request('/tools/presets', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async getLastParams(toolName: string): Promise<{ parameters: Record<string, unknown> | null }> {
    return request(`/tools/${toolName}/last-params`);
  },

  // 系统功能
  async readClipboard(): Promise<string> {
    const data = await request<{ content: string }>('/system/clipboard');
    return data.content;
  },

  async health(): Promise<{ status: string }> {
    return request('/health');
  }
};
