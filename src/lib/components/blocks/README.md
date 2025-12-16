# 区块系统编写规范

## 概述

区块系统用于构建节点的 UI，支持两种渲染模式：
- **普通模式**：Bento Grid 布局，紧凑展示
- **全屏模式**：GridStack 可拖拽布局，支持自由调整

## 文件结构

```
src/lib/components/blocks/
├── BlockCard.svelte      # 通用区块卡片容器
├── blockRegistry.ts      # 区块注册表和默认布局
├── index.ts              # 导出入口
└── README.md             # 本文档
```

## 添加新节点的区块

### 1. 在 blockRegistry.ts 中注册区块

```typescript
// 导入图标
import { YourIcon } from '@lucide/svelte';

// 定义区块列表
export const YOUR_NODE_BLOCKS: BlockDefinition[] = [
  {
    id: 'blockId',           // 唯一标识
    title: '区块标题',        // 显示名称
    icon: YourIcon,          // Lucide 图标
    iconClass: 'text-primary', // 图标颜色类
    colSpan: 2,              // 普通模式跨列数 (1 或 2)
    fullHeight: false,       // 是否占满高度
    collapsible: false,      // 是否可折叠
    visibleInNormal: true,   // 普通模式可见
    visibleInFullscreen: true // 全屏模式可见
  }
];

// 定义默认 GridStack 布局
export const YOUR_NODE_DEFAULT_GRID_LAYOUT: GridItem[] = [
  { id: 'blockId', x: 0, y: 0, w: 2, h: 2, minW: 1, minH: 1 }
];

// 注册到 nodeBlockRegistry
export const nodeBlockRegistry: Record<string, NodeBlockLayout> = {
  // ...existing
  yourNode: {
    nodeType: 'yourNode',
    blocks: YOUR_NODE_BLOCKS,
    defaultGridLayout: YOUR_NODE_DEFAULT_GRID_LAYOUT
  }
};
```

### 2. 在节点组件中使用区块

```svelte
<script lang="ts">
  import { BlockCard } from '$lib/components/blocks';
  import { YOUR_NODE_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { DashboardGrid, DashboardItem } from '$lib/components/ui/dashboard-grid';
  
  export let isFullscreenRender = false;
</script>

<!-- 定义区块内容 snippet -->
{#snippet myBlockContent()}
  {#if isFullscreenRender}
    <!-- 全屏模式：更大的字体和间距 -->
    <div class="space-y-3">...</div>
  {:else}
    <!-- 普通模式：紧凑布局 -->
    <div class="text-xs">...</div>
  {/if}
{/snippet}

<!-- 渲染 -->
{#if isFullscreenRender}
  <DashboardGrid ...>
    {@const item = getLayoutItem('blockId')}
    <DashboardItem id="blockId" x={item.x} y={item.y} w={item.w} h={item.h} minW={1} minH={1}>
      <BlockCard id="blockId" title="标题" icon={Icon} iconClass="text-primary" isFullscreen={true}>
        {#snippet children()}{@render myBlockContent()}{/snippet}
      </BlockCard>
    </DashboardItem>
  </DashboardGrid>
{:else}
  <div class="grid grid-cols-2 gap-2">
    <BlockCard id="blockId" title="标题" icon={Icon} iconClass="text-primary" class="col-span-2">
      {#snippet children()}{@render myBlockContent()}{/snippet}
    </BlockCard>
  </div>
{/if}
```

## BlockCard Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| id | string | - | 区块唯一标识 |
| title | string | - | 标题文本 |
| icon | Component | - | Lucide 图标组件 |
| iconClass | string | 'text-muted-foreground' | 图标颜色类 |
| isFullscreen | boolean | false | 是否全屏模式 |
| hideHeader | boolean | false | 隐藏标题栏 |
| compact | boolean | false | 紧凑模式 |
| fullHeight | boolean | false | 占满高度 |
| collapsible | boolean | false | 是否可折叠 |
| class | string | '' | 自定义类名 |

## 样式规范

### 全屏模式
- 使用 `rounded-md` 圆角
- 主题色描边 `border-primary/40`
- 半透明背景 `bg-card/80`
- 毛玻璃效果 `backdrop-blur-sm`
- 较大的字体和间距

### 普通模式
- 使用 `rounded-lg` 圆角
- 默认边框 `border`
- 实色背景 `bg-card`
- 紧凑的字体 `text-xs` 和间距

## 布局配置

### GridItem 属性
- `x, y`: 网格位置
- `w, h`: 宽高（网格单位）
- `minW, minH`: 最小宽高，建议设为 1 允许自由调整

### 普通模式跨列
- `col-span-1`: 单列
- `col-span-2`: 双列（占满宽度）

## 最佳实践

1. **内容自适应**：区块内容应根据 `isFullscreenRender` 调整样式
2. **最小尺寸**：`minW` 和 `minH` 建议设为 1，让用户自由调整
3. **状态共享**：使用 `nodeStateStore` 在普通/全屏模式间共享状态
4. **布局持久化**：通过 `layoutPresets` 保存和切换布局
