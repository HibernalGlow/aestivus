/**
 * Movea 节点区块配置
 * 压缩包分类移动工具 - 扫描目录并将压缩包/文件夹移动到对应的二级文件夹
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { Settings, FolderSearch, Package, Play, List } from '@lucide/svelte';

export const MOVEA_BLOCKS: BlockDefinition[] = [
  { id: 'config', title: '配置', icon: Settings, iconClass: 'text-blue-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'scan', title: '扫描', icon: FolderSearch, iconClass: 'text-orange-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'folders', title: '文件夹列表', icon: Package, iconClass: 'text-cyan-500', colSpan: 2, fullHeight: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: List, iconClass: 'text-muted-foreground', colSpan: 1, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const MOVEA_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'config', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'scan', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'folders', x: 0, y: 2, w: 3, h: 4, minW: 2, minH: 2 },
  { id: 'log', x: 3, y: 2, w: 1, h: 4, minW: 1, minH: 1 }
];
