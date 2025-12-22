/**
 * Encodeb 节点区块配置
 * 文件名编码修复工具
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FileText, Settings, Play, List, Folder } from '@lucide/svelte';

export const ENCODEB_BLOCKS: BlockDefinition[] = [
  { id: 'source', title: '源路径', icon: Folder, iconClass: 'text-blue-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'encoding', title: '编码设置', icon: Settings, iconClass: 'text-orange-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'preview', title: '预览', icon: List, iconClass: 'text-cyan-500', colSpan: 2, fullHeight: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: FileText, iconClass: 'text-muted-foreground', colSpan: 1, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const ENCODEB_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'source', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'encoding', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 0, y: 2, w: 1, h: 3, minW: 1, minH: 2 },
  { id: 'preview', x: 1, y: 2, w: 2, h: 3, minW: 1, minH: 2 },
  { id: 'log', x: 3, y: 2, w: 1, h: 3, minW: 1, minH: 1 }
];
