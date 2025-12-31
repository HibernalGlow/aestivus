/**
 * WeiboSpider 节点区块配置
 * 微博爬虫工具 - 爬取指定用户的微博数据、图片、视频
 */
import type { BlockDefinition } from '$lib/components/blocks/blockRegistry';
import type { GridItem } from '$lib/components/ui/dashboard-grid';
import { Settings, Users, Download, Play, List, Cookie, FolderOutput } from '@lucide/svelte';

export const WEIBOSPIDER_BLOCKS: BlockDefinition[] = [
  { id: 'users', title: '用户列表', icon: Users, iconClass: 'text-blue-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'config', title: '爬取配置', icon: Settings, iconClass: 'text-orange-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'cookie', title: 'Cookie', icon: Cookie, iconClass: 'text-yellow-500', colSpan: 2, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'output', title: '输出设置', icon: FolderOutput, iconClass: 'text-cyan-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'operation', title: '操作', icon: Play, iconClass: 'text-green-500', colSpan: 1, visibleInNormal: true, visibleInFullscreen: true },
  { id: 'log', title: '日志', icon: List, iconClass: 'text-muted-foreground', colSpan: 2, collapsible: true, visibleInNormal: true, visibleInFullscreen: true }
];

export const WEIBOSPIDER_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'users', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'config', x: 2, y: 0, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'cookie', x: 0, y: 2, w: 2, h: 2, minW: 1, minH: 1 },
  { id: 'output', x: 2, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'operation', x: 3, y: 2, w: 1, h: 2, minW: 1, minH: 1 },
  { id: 'log', x: 0, y: 4, w: 4, h: 2, minW: 1, minH: 1 }
];
