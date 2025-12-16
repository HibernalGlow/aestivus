<script lang="ts">
  /**
   * TabBlockCard - Tab 容器区块组件
   * 将多个子区块集成在一起，通过标签页切换显示
   * 标签栏替代子区块的标题栏，节省界面空间
   */
  import type { Snippet, Component } from 'svelte';
  import { getTabBlockChildren, type BlockDefinition, type TabBlockState } from './blockRegistry';

  interface Props {
    /** 区块 ID */
    id: string;
    /** 子区块 ID 列表 */
    children: string[];
    /** 节点类型（用于从注册表获取区块定义） */
    nodeType: string;
    /** 是否全屏模式 */
    isFullscreen?: boolean;
    /** 初始活动标签索引 */
    defaultActiveTab?: number;
    /** 标签切换回调 */
    onTabChange?: (index: number) => void;
    /** 状态变化回调（用于持久化） */
    onStateChange?: (state: TabBlockState) => void;
    /** 初始状态（从持久化恢复） */
    initialState?: TabBlockState;
    /** 子区块内容渲染器 */
    renderContent: Snippet<[string]>;
    /** 自定义类名 */
    class?: string;
  }

  let {
    id,
    children: childIds,
    nodeType,
    isFullscreen = false,
    defaultActiveTab = 0,
    onTabChange,
    onStateChange,
    initialState,
    renderContent,
    class: className = ''
  }: Props = $props();

  // 从初始状态恢复或使用默认值
  let activeTab = $state(initialState?.activeTab ?? defaultActiveTab);

  // 从注册表获取有效的子区块定义
  let childBlocks: BlockDefinition[] = $derived(
    getTabBlockChildren(nodeType, childIds)
  );

  // 当前活动的子区块 ID
  let activeBlockId = $derived(
    childBlocks[activeTab]?.id ?? childBlocks[0]?.id ?? ''
  );

  // 切换标签
  function switchTab(index: number) {
    if (index >= 0 && index < childBlocks.length) {
      activeTab = index;
      onTabChange?.(index);
      saveState();
    }
  }

  // 保存状态
  function saveState() {
    onStateChange?.({
      activeTab,
      children: childIds
    });
  }

  // 获取当前状态（供外部使用）
  export function getState(): TabBlockState {
    return {
      activeTab,
      children: childIds
    };
  }

  // 确保 activeTab 在有效范围内
  $effect(() => {
    if (activeTab >= childBlocks.length && childBlocks.length > 0) {
      activeTab = 0;
      saveState();
    }
  });
</script>

<div 
  class="tab-block-card h-full flex flex-col {isFullscreen ? 'border border-primary/40 rounded-md bg-card/80 backdrop-blur-sm' : 'bg-card rounded-lg border shadow-sm'} {className}"
>
  <!-- 标签栏 -->
  {#if childBlocks.length > 0}
    <div class="tab-bar flex items-center gap-0.5 {isFullscreen ? 'p-1.5 border-b bg-muted/30' : 'p-1'} shrink-0 overflow-x-auto">
      {#each childBlocks as block, index}
        {@const isActive = index === activeTab}
        {@const Icon = block.icon as Component | undefined}
        <button
          type="button"
          class="tab-item flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm font-medium transition-all whitespace-nowrap
            {isActive 
              ? 'bg-primary text-primary-foreground shadow-sm' 
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}"
          onclick={() => switchTab(index)}
        >
          {#if Icon}
            <Icon class="w-3.5 h-3.5 {isActive ? '' : block.iconClass}" />
          {/if}
          <span class="{isFullscreen ? 'text-sm' : 'text-xs'}">{block.title}</span>
        </button>
      {/each}
    </div>
  {/if}
  
  <!-- 内容区 -->
  <div class="tab-content flex-1 min-h-0 overflow-auto {isFullscreen ? 'p-2' : 'p-2'}">
    {#if activeBlockId}
      {@render renderContent(activeBlockId)}
    {:else}
      <div class="flex items-center justify-center h-full text-muted-foreground text-sm">
        暂无内容
      </div>
    {/if}
  </div>
</div>

<style>
  .tab-bar::-webkit-scrollbar {
    height: 4px;
  }
  
  .tab-bar::-webkit-scrollbar-track {
    background: transparent;
  }
  
  .tab-bar::-webkit-scrollbar-thumb {
    background: hsl(var(--muted-foreground) / 0.3);
    border-radius: 2px;
  }
</style>
