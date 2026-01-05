/**
 * Cleanf 节点区块配置
 * 文件清理工具 - 删除空文件夹和备份文件
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { FolderOpen, Settings, Play, FileText, ScrollText } from '@lucide/svelte';

export const CLEANF_BLOCKS: BlockDefinition[] = [
  { id: 'source', title: '路径来源', icon: FolderOpen, iconClass: 'text-primary', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'presets', title: '清理预设', icon: Settings, iconClass: 'text-orange-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'options', title: '选项', icon: Settings, iconClass: 'text-blue-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'result', title: '结果', icon: FileText, iconClass: 'text-cyan-500', colSpan: 2, fullHeight: true, collapsible: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: ScrollText, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const CLEANF_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'source', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'presets', x: 2, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'options', x: 3, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 0, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'result', x: 1, y: 2, w: 1, h: 4, minW: 1, minH: 2 },
  { id: 'log', x: 2, y: 2, w: 2, h: 4, minW: 1, minH: 1 }
];
