/**
 * Mvz 节点区块配置
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { Package, Play, FileText, BarChart3, Copy, List } from '@lucide/svelte';

export const MVZ_BLOCKS: BlockDefinition[] = [
  {
    id: 'input',
    title: '输入',
    icon: FileText,
    iconClass: 'text-blue-500',
    colSpan: 1,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'files',
    title: '文件列表',
    icon: List,
    iconClass: 'text-cyan-500',
    colSpan: 1,
    fullHeight: true,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'operation',
    title: '操作',
    icon: Play,
    iconClass: 'text-green-500',
    colSpan: 2,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'stats',
    title: '统计',
    icon: BarChart3,
    iconClass: 'text-yellow-500',
    colSpan: 2,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'results',
    title: '结果',
    icon: Package,
    iconClass: 'text-purple-500',
    colSpan: 2,
    fullHeight: true,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'log',
    title: '日志',
    icon: Copy,
    iconClass: 'text-muted-foreground',
    colSpan: 2,
    collapsible: true,
    visibleInNormal: true,
    visibleInFullscreen: true
  }
];

export const MVZ_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'input', x: 0, y: 0, w: 1, h: 2, minW: 1, minH: 2 },
  { id: 'files', x: 1, y: 0, w: 1, h: 3, minW: 1, minH: 2 },
  { id: 'operation', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'stats', x: 2, y: 2, w: 2, h: 1, minW: 1, minH: 1 },
  { id: 'results', x: 0, y: 3, w: 4, h: 3, minW: 1, minH: 2 },
  { id: 'log', x: 0, y: 6, w: 4, h: 2, minW: 1, minH: 1 }
];
