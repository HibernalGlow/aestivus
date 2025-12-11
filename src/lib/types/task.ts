export type TaskStatus = 'idle' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Task {
  id: string;
  flowId: string;
  status: TaskStatus;
  nodeStatuses: Record<string, NodeExecutionStatus>;
  startedAt?: string;
  completedAt?: string;
  error?: string;
}

export interface NodeExecutionStatus {
  nodeId: string;
  status: 'pending' | 'running' | 'completed' | 'error' | 'skipped';
  progress?: number;
  startTime?: string;
  endTime?: string;
  output?: unknown;
  error?: string;
}

export interface LogEntry {
  timestamp: string;
  nodeId: string;
  type: 'stdout' | 'stderr' | 'info' | 'error';
  content: string;
}

export interface TaskEvent {
  type: 'task_started' | 'task_progress' | 'task_output' | 'task_completed' | 'task_error' | 'node_status';
  taskId: string;
  nodeId?: string;
  data: {
    status?: string;
    progress?: number;
    output?: string;
    error?: string;
    result?: unknown;
    timestamp: string;
  };
}
