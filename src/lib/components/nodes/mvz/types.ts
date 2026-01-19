/**
 * Mvz 节点共享类型定义
 */

/** 操作类型 */
export type MvzAction = 'delete' | 'extract' | 'move' | 'rename';

/** 操作结果 */
export interface OperationResult {
  archive: string;
  success: boolean;
  message: string;
  files?: string[];
  count: number;
  output?: string;
  renames?: Array<{ old: string; new: string }>;
}

/** 预览信息 */
export interface PreviewInfo {
  archive: string;
  files?: string[];
  output?: string;
  count: number;
  operation?: string;
  renames?: Array<{ old: string; new: string }>;
}

/** 节点状态（用于持久化） */
export interface MvzNodeState {
  phase: 'idle' | 'processing' | 'completed' | 'error';
  progress: number;
  action: MvzAction;
  files: string[]; // 输入文件列表（archive//internal 格式）
  output: string;
  near: boolean;
  autoDir: boolean;
  flatten: boolean;
  pattern: string;
  replacement: string;
  dryRun: boolean;
  logs: string[];
  // 结果
  totalFiles: number;
  totalArchives: number;
  successCount: number;
  failedCount: number;
  results: OperationResult[];
  preview: PreviewInfo[];
}
