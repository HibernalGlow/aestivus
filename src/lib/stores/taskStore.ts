import { writable, derived } from 'svelte/store';
import type { TaskStatus, NodeExecutionStatus, LogEntry } from '$lib/types';

export interface TaskState {
  taskId: string | null;
  status: TaskStatus;
  nodeStatuses: Record<string, NodeExecutionStatus>;
  logs: LogEntry[];
}

const initialState: TaskState = {
  taskId: null,
  status: 'idle',
  nodeStatuses: {},
  logs: []
};

function createTaskStore() {
  const { subscribe, set, update } = writable<TaskState>(initialState);

  return {
    subscribe,

    startTask(taskId: string) {
      set({
        taskId,
        status: 'running',
        nodeStatuses: {},
        logs: []
      });
    },

    updateNodeStatus(nodeId: string, status: Partial<NodeExecutionStatus>) {
      update(state => ({
        ...state,
        nodeStatuses: {
          ...state.nodeStatuses,
          [nodeId]: {
            ...state.nodeStatuses[nodeId],
            nodeId,
            ...status
          } as NodeExecutionStatus
        }
      }));
    },

    addLog(log: LogEntry) {
      update(state => ({
        ...state,
        logs: [...state.logs, log]
      }));
    },

    addLogs(logs: LogEntry[]) {
      update(state => ({
        ...state,
        logs: [...state.logs, ...logs]
      }));
    },

    setStatus(status: TaskStatus) {
      update(state => ({ ...state, status }));
    },

    complete(success: boolean, error?: string) {
      update(state => ({
        ...state,
        status: success ? 'completed' : 'failed',
        logs: error
          ? [
              ...state.logs,
              {
                timestamp: new Date().toISOString(),
                nodeId: 'system',
                type: 'error' as const,
                content: error
              }
            ]
          : state.logs
      }));
    },

    cancel() {
      update(state => ({ ...state, status: 'cancelled' }));
    },

    reset() {
      set(initialState);
    }
  };
}

export const taskStore = createTaskStore();

export const isRunning = derived(taskStore, $task => $task.status === 'running');

export const recentLogs = derived(taskStore, $task => $task.logs.slice(-100));
