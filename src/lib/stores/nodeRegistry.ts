import type { NodeDefinition } from '$lib/types';

export const NODE_DEFINITIONS: NodeDefinition[] = [
  // 输入节点
  {
    type: 'clipboard_input',
    category: 'input',
    label: '剪贴板',
    description: '读取系统剪贴板内容',
    icon: 'Clipboard',
    inputs: [],
    outputs: ['text']
  },
  {
    type: 'folder_input',
    category: 'input',
    label: '文件夹',
    description: '选择文件夹路径',
    icon: 'Folder',
    inputs: [],
    outputs: ['path'],
    configSchema: {
      path: { type: 'path', label: '路径', required: true }
    }
  },
  {
    type: 'path_input',
    category: 'input',
    label: '路径输入',
    description: '手动输入或拖拽路径',
    icon: 'FileInput',
    inputs: [],
    outputs: ['path'],
    configSchema: {
      path: { type: 'string', label: '路径', required: true }
    }
  },

  // 工具节点
  {
    type: 'tool_repacku',
    category: 'tool',
    label: 'Repacku',
    description: '文件重打包工具',
    icon: 'Package',
    inputs: ['path'],
    outputs: ['path']
  },
  {
    type: 'tool_samea',
    category: 'tool',
    label: 'Samea',
    description: '相似文件分析',
    icon: 'Search',
    inputs: ['path'],
    outputs: ['path', 'report'],
    configSchema: {
      threshold: { type: 'number', label: '相似度阈值', default: 0.9 },
      method: { type: 'select', label: '比较方法', options: ['hash', 'pixel'], default: 'hash' }
    }
  },
  {
    type: 'tool_crashu',
    category: 'tool',
    label: 'Crashu',
    description: '崩溃文件处理',
    icon: 'AlertTriangle',
    inputs: ['path'],
    outputs: ['path']
  },
  {
    type: 'tool_migratef',
    category: 'tool',
    label: 'Migratef',
    description: '文件迁移工具',
    icon: 'FolderSync',
    inputs: ['path'],
    outputs: ['path'],
    configSchema: {
      target: { type: 'path', label: '目标路径', required: true },
      mode: { type: 'select', label: '模式', options: ['copy', 'move'], default: 'move' },
      existing_dir: { type: 'select', label: '已存在处理', options: ['skip', 'merge', 'replace'], default: 'merge' }
    }
  },
  {
    type: 'tool_nameu',
    category: 'tool',
    label: 'Nameu',
    description: '文件命名工具',
    icon: 'FileText',
    inputs: ['path'],
    outputs: ['path']
  },
  {
    type: 'tool_formatv',
    category: 'tool',
    label: 'Formatv',
    description: '视频格式化',
    icon: 'Video',
    inputs: ['path'],
    outputs: ['path']
  },

  // 输出节点
  {
    type: 'log_output',
    category: 'output',
    label: '日志输出',
    description: '输出到日志面板',
    icon: 'Terminal',
    inputs: ['any'],
    outputs: []
  }
];

export function getNodeDefinition(type: string): NodeDefinition | undefined {
  return NODE_DEFINITIONS.find(d => d.type === type);
}

export function getNodesByCategory(category: string): NodeDefinition[] {
  return NODE_DEFINITIONS.filter(d => d.category === category);
}
