/**
 * Kavvka 节点区块配置
 * Czkawka 辅助工具 - 处理图片文件夹并生成路径
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { Image, Folder, Play, List, Copy, Search } from '@lucide/svelte';

export const KAVVKA_BLOCKS: BlockDefinition[] = [
  { id: 'source', title: '源路径', icon: Folder, iconClass: 'text-blue-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'scan', title: '扫描设置', icon: Search, iconClass: 'text-orange-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'result', title: '结果', icon: Copy, iconClass: 'text-cyan-500', colSpan: 2, fullHeight: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: List, iconClass: 'text-muted-foreground', colSpan: 1, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const KAVVKA_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'source', x: 0, y: 0, w: 2, h: 2, minW: 2, minH: 1 },
  { id: 'scan', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 0, y: 2, w: 1, h: 3, minW: 1, minH: 2 },
  { id: 'result', x: 1, y: 2, w: 2, h: 3, minW: 2, minH: 2 },
  { id: 'log', x: 3, y: 2, w: 1, h: 3, minW: 1, minH: 1 }
];
