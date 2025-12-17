<script lang="ts">
  /**
   * NodeLayoutRenderer - 统一节点布局渲染器
   * 处理节点模式和全屏模式的布局切换、Tab 管理、状态持久化
   * 节点组件只需提供内容 snippets，无需关心布局逻辑
   */
  import type { Snippet } from 'svelte';
  import type { GridItem } from '$lib/components/ui/dashboard-grid';
  import { DashboardGrid, DashboardItem } from '$lib/components/ui/dashboard-grid';
  import { BlockCard, TabBlockCard } from '$lib/components/blocks';
  import { 
    getBlockDefinition, 
    getNodeBlockLayout
  } from './blockRegistry';
  import {
    getOrCreateLayoutState,
    updateFullscreenGridLayout,
    updateTabState,
    createTabBlock,
    removeTabBlock,
    subscribeNodeLayoutState,
    type NodeLayoutState
  } from '$lib/stores/nodeLayoutStore';
  import { getSizeMode, type SizeMode } from '$lib/utils/sizeUtils';
  import { onMount } from 'svelte';

  interface Props {
    /** 节点 ID */
    nodeId: string;
    /** 节点类型（用于获取区块定义） */
    nodeType: string;
    /** 是否全屏模式 */
    isFullscreen: boolean;
    /** 默认 GridStack 布局（首次渲染时使用） */
    defaultGridLayout?: GridItem[];
    /** 区块内容渲染器 */
    renderBlock: Snippet<[blockId: string, size: SizeMode]>;
    /** 布局变化回调（可选） */
    onLayoutChange?: (state: NodeLayoutState) => void;
  }

  let {
    nodeId,
    nodeType,
    isFullscreen,
    defaultGridLayout = [],
    renderBlock,
    onLayoutChange
  }: Props = $props();

  // 当前模式
  let mode = $derived(isFullscreen ? 'fullscreen' : 'normal') as 'fullscreen' | 'normal';
  
  // 尺寸模式
  let sizeMode = $derived(getSizeMode(isFullscreen));

  // 布局状态 - 使用响应式订阅
  // 注意：初始值使用空状态，onMount 中会正确初始化
  let layoutState = $state<NodeLayoutState>(getOrCreateLayoutState(nodeId, defaultGridLayout));
  
  // 订阅 store 变化，保持 layoutState 同步
  // 使用 $effect 确保响应式追踪 nodeId 和 defaultGridLayout
  $effect(() => {
    // 初始化时确保状态存在
    layoutState = getOrCreateLayoutState(nodeId, defaultGridLayout);
  });
  
  onMount(() => {
    // 订阅变化 - 使用闭包捕获当前 nodeId
    const currentNodeId = nodeId;
    const unsubscribe = subscribeNodeLayoutState(currentNodeId, (state) => {
      if (state) {
        layoutState = state;
        onLayoutChange?.(state);
      }
    });
    
    return unsubscribe;
  });



  // GridStack 布局（仅全屏模式）
  let gridLayout = $derived(layoutState.fullscreen.gridLayout);

  // DashboardGrid 引用
  let dashboardGrid = $state<{ compact: () => void; applyLayout: (layout: GridItem[]) => void } | undefined>(undefined);

  // 获取区块布局配置
  let blockLayout = $derived(getNodeBlockLayout(nodeType));
  
  // 获取已使用的 Tab 区块 ID（从 layoutState 读取）
  let usedTabIds = $derived(() => {
    const ids: string[] = [];
    for (const tabState of Object.values(layoutState[mode].tabStates)) {
      ids.push(...tabState.children.slice(1));
    }
    return ids;
  });

  // 获取可见区块列表（根据模式过滤）
  let visibleBlocks = $derived(() => {
    if (!blockLayout) return [];
    const usedIds = usedTabIds();
    return blockLayout.blocks.filter(b => {
      // 过滤掉已被合并到 Tab 中的区块（作为子区块）
      if (usedIds.includes(b.id)) return false;
      
      // 根据模式过滤
      if (isFullscreen) {
        return b.visibleInFullscreen !== false;
      } else {
        return b.visibleInNormal !== false;
      }
    });
  });

  // 处理 GridStack 布局变化
  function handleGridLayoutChange(newLayout: GridItem[]) {
    updateFullscreenGridLayout(nodeId, newLayout);
    // layoutState 会通过订阅自动更新
  }

  // 处理 Tab 状态变化
  function handleTabStateChange(tabId: string, state: { activeTab: number; children: string[] }) {
    updateTabState(nodeId, mode, tabId, state);
    // layoutState 会通过订阅自动更新
  }

  // 创建 Tab 区块
  export function createTab(blockIds: string[]) {
    createTabBlock(nodeId, mode, blockIds);
    
    // 全屏模式下，从 gridLayout 中移除被合并的区块（保留第一个）
    if (isFullscreen && blockIds.length > 1) {
      const otherBlockIds = blockIds.slice(1);
      const newLayout = gridLayout.filter(item => !otherBlockIds.includes(item.id));
      updateFullscreenGridLayout(nodeId, newLayout);
    }
    // layoutState 会通过订阅自动更新
  }

  // 删除 Tab 区块
  function handleRemoveTab(tabId: string) {
    const childIds = removeTabBlock(nodeId, mode, tabId);
    
    // 全屏模式下，恢复被隐藏的区块到布局中
    if (isFullscreen && childIds.length > 0) {
      const tabItem = gridLayout.find(item => item.id === tabId);
      const baseY = tabItem?.y ?? 0;
      const baseX = (tabItem?.x ?? 0) + (tabItem?.w ?? 2);
      
      const restoredItems: GridItem[] = childIds.map((childId, index) => ({
        id: childId,
        x: baseX,
        y: baseY + index * 2,
        w: 1,
        h: 2,
        minW: 1,
        minH: 1
      }));
      
      updateFullscreenGridLayout(nodeId, [...gridLayout, ...restoredItems]);
    }
    // layoutState 会通过订阅自动更新
  }

  // 检查区块是否是 Tab 容器（从 layoutState 读取，确保响应式）
  function checkIsTabContainer(blockId: string): boolean {
    return layoutState[mode].tabBlocks.includes(blockId);
  }

  // 获取 Tab 状态（从 layoutState 读取，确保响应式）
  function getBlockTabState(blockId: string) {
    return layoutState[mode].tabStates[blockId];
  }

  // 获取已使用的 Tab 区块 ID（从 layoutState 读取，确保响应式）
  export function getUsedBlockIds(): string[] {
    const ids: string[] = [];
    for (const tabState of Object.values(layoutState[mode].tabStates)) {
      ids.push(...tabState.children.slice(1));
    }
    return ids;
  }

  // 整理布局（全屏模式）
  export function compact() {
    dashboardGrid?.compact();
  }

  // 重置布局（全屏模式）
  export function resetLayout() {
    updateFullscreenGridLayout(nodeId, defaultGridLayout);
    dashboardGrid?.applyLayout(defaultGridLayout);
    // layoutState 会通过订阅自动更新
  }

  // 应用布局预设
  export function applyLayout(layout: GridItem[]) {
    updateFullscreenGridLayout(nodeId, layout);
    dashboardGrid?.applyLayout(layout);
    // layoutState 会通过订阅自动更新
  }

  // 获取当前布局
  export function getCurrentLayout(): GridItem[] {
    return gridLayout;
  }
</script>

{#if isFullscreen}
  <!-- 全屏模式：GridStack 布局 -->
  <div class="h-full overflow-hidden">
    <DashboardGrid 
      bind:this={dashboardGrid} 
      columns={4} 
      cellHeight={80} 
      margin={12} 
      showToolbar={false} 
      onLayoutChange={handleGridLayoutChange}
    >
      {#each gridLayout as item (item.id)}
        <DashboardItem 
          id={item.id} 
          x={item.x} 
          y={item.y} 
          w={item.w} 
          h={item.h} 
          minW={item.minW ?? 1} 
          minH={item.minH ?? 1}
        >
          {#if checkIsTabContainer(item.id)}
            <!-- Tab 容器模式 -->
            <TabBlockCard
              id={item.id}
              children={getBlockTabState(item.id)?.children ?? []}
              {nodeType}
              isFullscreen={true}
              initialState={getBlockTabState(item.id)}
              onStateChange={(state) => handleTabStateChange(item.id, state)}
              onRemove={() => handleRemoveTab(item.id)}
            >
              {#snippet renderContent(blockId: string)}
                {@render renderBlock(blockId, sizeMode)}
              {/snippet}
            </TabBlockCard>
          {:else}
            <!-- 普通区块模式 -->
            {@const blockDef = getBlockDefinition(nodeType, item.id)}
            {#if blockDef}
              <BlockCard 
                id={item.id} 
                title={blockDef.title} 
                icon={blockDef.icon as any} 
                iconClass={blockDef.iconClass} 
                isFullscreen={true} 
                fullHeight={blockDef.fullHeight} 
                hideHeader={blockDef.hideHeader}
              >
                {#snippet children()}
                  {@render renderBlock(item.id, sizeMode)}
                {/snippet}
              </BlockCard>
            {/if}
          {/if}
        </DashboardItem>
      {/each}
    </DashboardGrid>
  </div>
{:else}
  <!-- 节点模式：BentoGrid 布局 -->
  <div class="flex-1 overflow-y-auto p-2">
    <div class="grid grid-cols-2 gap-2" style="grid-auto-rows: minmax(auto, max-content);">
      {#each visibleBlocks() as block (block.id)}
        {#if checkIsTabContainer(block.id)}
          <!-- Tab 容器模式 -->
          <div class="col-span-{block.colSpan ?? 1}">
            <TabBlockCard
              id={block.id}
              children={getBlockTabState(block.id)?.children ?? []}
              {nodeType}
              isFullscreen={false}
              initialState={getBlockTabState(block.id)}
              onStateChange={(state) => handleTabStateChange(block.id, state)}
              onRemove={() => handleRemoveTab(block.id)}
            >
              {#snippet renderContent(blockId: string)}
                {@render renderBlock(blockId, sizeMode)}
              {/snippet}
            </TabBlockCard>
          </div>
        {:else}
          <!-- 普通区块模式 -->
          <BlockCard 
            id={block.id} 
            title={block.title} 
            icon={block.icon as any} 
            iconClass={block.iconClass}
            collapsible={block.collapsible}
            defaultExpanded={block.defaultExpanded ?? true}
            class="col-span-{block.colSpan ?? 1}"
          >
            {#snippet children()}
              {@render renderBlock(block.id, sizeMode)}
            {/snippet}
          </BlockCard>
        {/if}
      {/each}
    </div>
  </div>
{/if}
