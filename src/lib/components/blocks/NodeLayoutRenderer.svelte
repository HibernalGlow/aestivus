<script lang="ts">
  /**
   * NodeLayoutRenderer - 统一节点布局渲染器
   * 两种模式共用 GridItem[] 结构，全屏用 GridStack，节点用静态 CSS Grid
   * Tab 状态使用 unifiedTabStore 统一管理，两种模式共享
   */
  import type { Snippet } from 'svelte';
  import type { GridItem } from '$lib/components/ui/dashboard-grid';
  import { DashboardGrid, DashboardItem } from '$lib/components/ui/dashboard-grid';
  import { BlockCard, TabBlockCard } from '$lib/components/blocks';
  import { getBlockDefinition, getNodeBlockLayout } from './blockRegistry';
  import {
    getOrCreateNodeConfig,
    updateGridLayout,
    subscribeNodeConfig,
    removeBlocksFromLayout,
    restoreBlocksToLayout,
    type NodeConfig
  } from '$lib/stores/nodeLayoutStore';
  import {
    getTabConfig,
    createTab as createUnifiedTab,
    removeTab as removeUnifiedTab,
    setActiveTab,
    addChild,
    removeChild,
    reorderChildren,
    getUsedBlockIds as getUnifiedUsedBlockIds,
    isTabContainer as checkUnifiedTabContainer,
    getTabState as getUnifiedTabState,
    subscribeTabConfig,
    type UnifiedTabConfig
  } from '$lib/stores/unifiedTabStore';
  import { getSizeMode, type SizeMode } from '$lib/utils/sizeUtils';
  import { onMount } from 'svelte';

  interface Props {
    nodeId: string;
    nodeType: string;
    isFullscreen: boolean;
    /** 全屏模式默认布局 */
    defaultFullscreenLayout?: GridItem[];
    /** 节点模式默认布局 */
    defaultNormalLayout?: GridItem[];
    renderBlock: Snippet<[blockId: string, size: SizeMode]>;
    onConfigChange?: (config: NodeConfig) => void;
  }

  let {
    nodeId,
    nodeType,
    isFullscreen,
    defaultFullscreenLayout = [],
    defaultNormalLayout = [],
    renderBlock,
    onConfigChange
  }: Props = $props();

  // 当前模式
  let mode = $derived(isFullscreen ? 'fullscreen' : 'normal') as 'fullscreen' | 'normal';
  
  // 尺寸模式
  let sizeMode = $derived(getSizeMode(isFullscreen));

  // 生成节点模式默认布局
  function generateNormalLayout(): GridItem[] {
    const layout = getNodeBlockLayout(nodeType);
    if (!layout) return [];
    return layout.blocks
      .filter(b => b.visibleInNormal !== false && !b.isTabContainer)
      .map((b, idx) => ({
        id: b.id,
        x: idx % 2,
        y: Math.floor(idx / 2),
        w: b.colSpan ?? 1,
        h: 1,
        minW: 1,
        minH: 1
      }));
  }

  // 检查模式是否有任何已保存的布局
  function hasSavedLayout(modeState: { gridLayout: GridItem[] }): boolean {
    return modeState.gridLayout.length > 0;
  }

  // 初始化节点配置（使用 nodeType 作为 key）
  function initNodeConfig(): NodeConfig {
    const config = getOrCreateNodeConfig(nodeId, nodeType, defaultFullscreenLayout, defaultNormalLayout);
    const initialTabConfig = getTabConfig(nodeType);
    
    console.log('[NodeLayoutRenderer] 初始化配置:', {
      nodeType,
      mode,
      normalLayout: config.normal.gridLayout.map(i => i.id),
      fullscreenLayout: config.fullscreen.gridLayout.map(i => i.id),
      tabContainers: initialTabConfig.containerIds
    });
    
    // 分别检查每个模式是否需要初始化
    let needsUpdate = false;
    
    // 节点模式：没有保存布局时才初始化（使用节点模式专用的默认布局）
    if (!hasSavedLayout(config.normal)) {
      const normalLayout = defaultNormalLayout.length > 0 ? defaultNormalLayout : generateNormalLayout();
      if (normalLayout.length > 0) {
        console.log('[NodeLayoutRenderer] 初始化节点模式布局:', normalLayout.map(i => ({ id: i.id, w: i.w })));
        updateGridLayout(nodeType, 'normal', normalLayout);
        needsUpdate = true;
      }
    }
    
    // 全屏模式：没有保存布局时才初始化（使用全屏模式专用的默认布局）
    if (!hasSavedLayout(config.fullscreen) && defaultFullscreenLayout.length > 0) {
      console.log('[NodeLayoutRenderer] 初始化全屏模式布局:', defaultFullscreenLayout.map(i => ({ id: i.id, w: i.w })));
      updateGridLayout(nodeType, 'fullscreen', defaultFullscreenLayout);
      needsUpdate = true;
    }
    
    // 如果有更新，重新获取配置
    const finalConfig = needsUpdate 
      ? getOrCreateNodeConfig(nodeId, nodeType, defaultFullscreenLayout, defaultNormalLayout)
      : config;
    
    console.log('[NodeLayoutRenderer] 最终配置:', {
      normalLayoutIds: finalConfig.normal.gridLayout.map(i => i.id),
      fullscreenLayoutIds: finalConfig.fullscreen.gridLayout.map(i => i.id),
      tabContainers: initialTabConfig.containerIds
    });
    
    return finalConfig;
  }

  // 节点配置（布局）
  let nodeConfig = $state<NodeConfig>(initNodeConfig());
  
  // Tab 配置（统一存储，两种模式共享）
  let tabConfig = $state<UnifiedTabConfig>(getTabConfig(nodeType));
  
  // 当 isFullscreen 变化时重新初始化（因为 mode 变了）
  $effect(() => {
    // 触发依赖
    const currentMode = isFullscreen ? 'fullscreen' : 'normal';
    console.log('[NodeLayoutRenderer] mode 变化:', currentMode);
    // 重新获取配置，确保当前模式有正确的布局
    const config = getOrCreateNodeConfig(nodeId, nodeType, defaultFullscreenLayout, defaultNormalLayout);
    if (!hasSavedLayout(config[currentMode])) {
      // 每个模式使用各自的默认布局
      const defaultLayout = currentMode === 'fullscreen' 
        ? defaultFullscreenLayout 
        : (defaultNormalLayout.length > 0 ? defaultNormalLayout : generateNormalLayout());
      if (defaultLayout.length > 0) {
        console.log(`[NodeLayoutRenderer] 初始化 ${currentMode} 模式布局:`, defaultLayout.map(i => ({ id: i.id, w: i.w })));
        updateGridLayout(nodeType, currentMode, defaultLayout);
      }
    }
  });
  
  // 订阅配置变化（使用 nodeType 作为 key）
  onMount(() => {
    // 订阅布局配置变化
    const unsubscribeLayout = subscribeNodeConfig(nodeType, (config) => {
      if (config) {
        nodeConfig = config;
        onConfigChange?.(config);
      }
    });
    
    // 订阅 Tab 配置变化（统一存储）
    const unsubscribeTab = subscribeTabConfig(nodeType, (config) => {
      tabConfig = config;
    });
    
    return () => {
      unsubscribeLayout();
      unsubscribeTab();
    };
  });

  // 当前模式的布局
  let currentLayout = $derived(nodeConfig[mode].gridLayout);

  // DashboardGrid 引用
  let dashboardGrid = $state<{ compact: () => void; applyLayout: (layout: GridItem[]) => void } | undefined>(undefined);
  
  // 获取已使用的 Tab 区块 ID（从统一 Tab 存储获取）
  let usedTabIds = $derived(() => {
    return getUnifiedUsedBlockIds(nodeType);
  });

  // 获取可见区块（过滤掉被合并到 Tab 的）
  let visibleBlocks = $derived(() => {
    const usedIds = usedTabIds();
    const visible = currentLayout.filter(item => !usedIds.includes(item.id));
    console.log('[NodeLayoutRenderer] visibleBlocks:', {
      mode,
      currentLayoutIds: currentLayout.map(i => i.id),
      usedIds,
      visibleIds: visible.map(i => i.id),
      tabContainers: tabConfig.containerIds
    });
    return visible;
  });

  // 处理布局变化（使用 nodeType 作为 key）
  function handleLayoutChange(newLayout: GridItem[]) {
    updateGridLayout(nodeType, mode, newLayout);
  }

  // 处理 Tab 状态变化（使用统一 Tab 存储）
  function handleTabStateChange(tabId: string, state: { activeTab: number; children: string[] }) {
    // 更新活动标签
    setActiveTab(nodeType, tabId, state.activeTab);
    // 如果子区块顺序变化，更新顺序
    const currentState = getUnifiedTabState(nodeType, tabId);
    if (currentState && JSON.stringify(currentState.children) !== JSON.stringify(state.children)) {
      reorderChildren(nodeType, tabId, state.children);
    }
  }

  // 创建 Tab 区块（使用统一 Tab 存储）
  export function createTab(blockIds: string[]): string | null {
    const tabId = createUnifiedTab(nodeType, blockIds);
    if (tabId) {
      // 从布局中移除被合并的区块（保留第一个作为 Tab 容器）
      const otherBlockIds = blockIds.slice(1);
      removeBlocksFromLayout(nodeType, mode, otherBlockIds);
    }
    return tabId;
  }

  // 删除 Tab 区块（使用统一 Tab 存储）
  function handleRemoveTab(tabId: string) {
    // 获取 Tab 容器在布局中的位置
    const tabItem = currentLayout.find(item => item.id === tabId);
    const basePosition = { x: tabItem?.x ?? 0, y: tabItem?.y ?? 0 };
    
    // 从统一存储中删除 Tab，获取需要恢复的子区块
    const childIds = removeUnifiedTab(nodeType, tabId);
    
    // 恢复子区块到布局
    if (childIds.length > 0) {
      restoreBlocksToLayout(nodeType, mode, childIds, basePosition, isFullscreen);
    }
  }

  // 检查区块是否是 Tab 容器（使用统一 Tab 存储）
  function checkIsTabContainer(blockId: string): boolean {
    return checkUnifiedTabContainer(nodeType, blockId);
  }

  // 获取 Tab 状态（使用统一 Tab 存储）
  function getBlockTabState(blockId: string) {
    const state = getUnifiedTabState(nodeType, blockId);
    if (!state) return undefined;
    return { activeTab: state.activeTab, children: state.children };
  }

  // 获取已使用的 Tab 区块 ID
  export function getUsedBlockIds(): string[] {
    return usedTabIds();
  }
  
  // 检查区块是否是 Tab 容器（导出方法）
  export function isTabContainer(blockId: string): boolean {
    return checkIsTabContainer(blockId);
  }

  // 应用尺寸覆盖
  function applyGridItemOverride(item: GridItem): GridItem {
    const override = nodeConfig[mode].sizeOverrides[item.id];
    if (!override) return item;
    return {
      ...item,
      minW: override.minW ?? item.minW,
      minH: override.minH ?? item.minH
    };
  }

  // 整理布局
  export function compact() {
    dashboardGrid?.compact();
  }

  // 重置布局（使用 nodeType 作为 key）
  export function resetLayout() {
    const defaultLayout = isFullscreen ? defaultFullscreenLayout : defaultNormalLayout;
    updateGridLayout(nodeType, mode, defaultLayout);
    if (isFullscreen) dashboardGrid?.applyLayout(defaultLayout);
  }

  // 应用布局预设（使用 nodeType 作为 key）
  export function applyLayout(layout: GridItem[]) {
    updateGridLayout(nodeType, mode, layout);
    if (isFullscreen) dashboardGrid?.applyLayout(layout);
  }

  // 获取当前布局
  export function getCurrentLayout(): GridItem[] {
    return currentLayout;
  }

  // 获取当前配置
  export function getConfig(): NodeConfig {
    return nodeConfig;
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
      onLayoutChange={handleLayoutChange}
    >
      {#each visibleBlocks() as item (item.id)}
        {@const gridItem = applyGridItemOverride(item)}
        <DashboardItem 
          id={gridItem.id} 
          x={gridItem.x} 
          y={gridItem.y} 
          w={gridItem.w} 
          h={gridItem.h} 
          minW={gridItem.minW ?? 1} 
          minH={gridItem.minH ?? 1}
        >
          {#if checkIsTabContainer(gridItem.id)}
            <TabBlockCard
              id={gridItem.id}
              children={getBlockTabState(gridItem.id)?.children ?? []}
              {nodeType}
              isFullscreen={true}
              initialState={getBlockTabState(gridItem.id)}
              onStateChange={(state) => handleTabStateChange(gridItem.id, state)}
              onRemove={() => handleRemoveTab(gridItem.id)}
            >
              {#snippet renderContent(blockId: string)}
                {@render renderBlock(blockId, sizeMode)}
              {/snippet}
            </TabBlockCard>
          {:else}
            {@const blockDef = getBlockDefinition(nodeType, gridItem.id)}
            {#if blockDef}
              <BlockCard 
                id={gridItem.id} 
                title={blockDef.title} 
                icon={blockDef.icon as any} 
                iconClass={blockDef.iconClass} 
                isFullscreen={true} 
                fullHeight={blockDef.fullHeight} 
                hideHeader={blockDef.hideHeader}
              >
                {#snippet children()}
                  {@render renderBlock(gridItem.id, sizeMode)}
                {/snippet}
              </BlockCard>
            {/if}
          {/if}
        </DashboardItem>
      {/each}
    </DashboardGrid>
  </div>
{:else}
  <!-- 节点模式：静态 CSS Grid 布局 -->
  <div class="flex-1 overflow-y-auto p-2">
    <div class="grid grid-cols-2 gap-2" style="grid-auto-rows: minmax(auto, max-content);">
      {#each visibleBlocks() as item (item.id)}
        {@const blockDef = getBlockDefinition(nodeType, item.id)}
        {@const colSpan = item.w >= 2 ? 2 : 1}
        {#if checkIsTabContainer(item.id)}
          <div class={colSpan === 2 ? 'col-span-2' : ''}>
            <TabBlockCard
              id={item.id}
              children={getBlockTabState(item.id)?.children ?? []}
              {nodeType}
              isFullscreen={false}
              initialState={getBlockTabState(item.id)}
              onStateChange={(state) => handleTabStateChange(item.id, state)}
              onRemove={() => handleRemoveTab(item.id)}
            >
              {#snippet renderContent(blockId: string)}
                {@render renderBlock(blockId, sizeMode)}
              {/snippet}
            </TabBlockCard>
          </div>
        {:else if blockDef}
          <BlockCard 
            id={item.id} 
            title={blockDef.title} 
            icon={blockDef.icon as any} 
            iconClass={blockDef.iconClass}
            collapsible={blockDef.collapsible}
            defaultExpanded={blockDef.defaultExpanded ?? true}
            class={colSpan === 2 ? 'col-span-2' : ''}
          >
            {#snippet children()}
              {@render renderBlock(item.id, sizeMode)}
            {/snippet}
          </BlockCard>
        {/if}
      {/each}
    </div>
  </div>
{/if}
