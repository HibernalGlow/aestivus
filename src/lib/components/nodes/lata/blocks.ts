/**
 * Lata 节点区块配置
 * Taskfile 任务启动器
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { ListTodo, Play, FileText, Copy, Terminal } from '@lucide/svelte';

export const LATA_BLOCKS: BlockDefinition[] = [
  { id: 'taskfile', title: 'Taskfile', icon: FileText, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'tasks', title: '任务列表', icon: ListTodo, iconClass: 'text-blue-500', colSpan: 2, fullHeight: true, collapsible: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'terminal', title: '终端', icon: Terminal, iconClass: 'text-green-400', colSpan: 2, fullHeight: true, collapsible: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: Copy, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: false, visibleInFullscreen: true }
];

export const LATA_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'taskfile', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'tasks', x: 0, y: 2, w: 2, h: 4, minW: 1, minH: 2 },
  { id: 'terminal', x: 2, y: 2, w: 2, h: 4, minW: 1, minH: 2 },
  { id: 'log', x: 0, y: 6, w: 4, h: 2, minW: 1, minH: 1 }
];
