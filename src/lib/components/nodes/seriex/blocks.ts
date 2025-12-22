/**
 * Seriex 节点区块配置
 * 漫画压缩包系列提取工具 - 自动识别并整理同一系列的漫画压缩包
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { Settings, Sliders, Play, List, Terminal } from '@lucide/svelte';

export const SERIEX_BLOCKS: BlockDefinition[] = [
  { id: 'config', title: '配置', icon: Settings, iconClass: 'text-blue-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'similarity', title: '相似度', icon: Sliders, iconClass: 'text-purple-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'action', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'plan', title: '计划', icon: List, iconClass: 'text-cyan-500', colSpan: 2, fullHeight: true, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: Terminal, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const SERIEX_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'config', x: 0, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'similarity', x: 1, y: 0, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'action', x: 0, y: 2, w: 2, h: 1, minW: 1, minH: 1 },
  { id: 'plan', x: 2, y: 0, w: 2, h: 3, minW: 2, minH: 2 },
  { id: 'log', x: 0, y: 3, w: 4, h: 1, minW: 1, minH: 1 }
];
