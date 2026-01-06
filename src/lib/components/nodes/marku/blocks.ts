/**
 * Marku 节点区块配置
 * Markdown 模块化处理工具箱
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FolderOpen, Settings, Play, FileText, ScrollText, Code, Clipboard, List, Diff, Undo2 } from '@lucide/svelte';

export const MARKU_BLOCKS: BlockDefinition[] = [
  { id: 'source', title: '输入来源', icon: FolderOpen, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'module', title: '处理模块', icon: List, iconClass: 'text-purple-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'config', title: 'Step 配置', icon: Settings, iconClass: 'text-orange-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'options', title: '选项', icon: Settings, iconClass: 'text-blue-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'diff', title: 'Diff 预览', icon: Diff, iconClass: 'text-yellow-500', colSpan: 2, fullHeight: true, collapsible: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: ScrollText, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const MARKU_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'source', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'module', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'config', x: 0, y: 2, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'options', x: 2, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'diff', x: 0, y: 5, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'log', x: 2, y: 4, w: 2, h: 4, minW: 1, minH: 1 }
];

// 可用的 marku 模块列表
export const MARKU_MODULES = [
  { id: 'markt', name: 'markt', desc: '标题 ↔ 列表互转' },
  { id: 'consecutive_header', name: 'consecutive_header', desc: '连续标题处理' },
  { id: 'content_dedup', name: 'content_dedup', desc: '内容去重' },
  { id: 'html2sy_table', name: 'html2sy_table', desc: 'HTML 表格转 Markdown' },
  { id: 'title_convert', name: 'title_convert', desc: '标题格式规范化' },
  { id: 'content_replace', name: 'content_replace', desc: '内容替换' },
  { id: 'single_orderlist_remover', name: 'single_orderlist_remover', desc: '单项列表移除' },
  { id: 'image_path_replacer', name: 'image_path_replacer', desc: '图片路径替换' },
  { id: 't2list', name: 't2list', desc: '表格转列表' }
];

// markt 模块的配置字段
export const MARKT_CONFIG_FIELDS = [
  { key: 'mode', label: '模式', type: 'select', options: ['h2l', 'l2h'], default: 'h2l' },
  { key: 'bullet', label: '列表标记', type: 'select', options: ['- ', '* ', '+ '], default: '- ' },
  { key: 'ordered', label: '有序列表', type: 'boolean', default: false },
  { key: 'indent', label: '缩进空格', type: 'number', default: 4 },
  { key: 'max_heading', label: '最大标题级别', type: 'number', default: 6 },
  { key: 'start_level', label: '起始标题级别 (l2h)', type: 'number', default: 1 },
  { key: 'max_level', label: '最大级别 (l2h)', type: 'number', default: 6 }
];

// 通用配置字段（所有模块共享）
export const COMMON_CONFIG_FIELDS = [
  { key: 'recursive', label: '递归处理', type: 'boolean', default: false },
  { key: 'verbose', label: '详细输出', type: 'boolean', default: true }
];
