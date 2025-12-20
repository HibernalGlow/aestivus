/**
 * Findz 节点区块配置
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FolderOpen, FolderTree, Play, Copy, Filter, BarChart3 } from '@lucide/svelte';

export const FINDZ_BLOCKS: BlockDefinition[] = [
  {
    id: 'path',
    title: '搜索路径',
    icon: FolderOpen,
    iconClass: 'text-primary',
    colSpan: 2,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'filter',
    title: 'WHERE 过滤',
    icon: Filter,
    iconClass: 'text-blue-500',
    colSpan: 2,
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
    id: 'tree',
    title: '文件列表',
    icon: FolderTree,
    iconClass: 'text-blue-500',
    colSpan: 2,
    fullHeight: true,
    visibleInNormal: true,
    visibleInFullscreen: true
  },
  {
    id: 'analysis',
    title: '分组分析',
    icon: BarChart3,
    iconClass: 'text-orange-500',
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

export const FINDZ_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'path', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'filter', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 0, y: 2, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'stats', x: 2, y: 2, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'tree', x: 0, y: 4, w: 2, h: 4, minW: 1, minH: 2 },
  { id: 'analysis', x: 2, y: 4, w: 2, h: 4, minW: 1, minH: 2 },
  { id: 'log', x: 0, y: 8, w: 4, h: 2, minW: 1, minH: 1 }
];
