<script lang="ts">
  /**
   * TabGroupCard - Tab 分组卡片组件
   * 
   * 虚拟分组模式：区块始终在 gridLayout 中，这里只负责渲染和切换
   * 使用 CSS transform 实现平滑的 Tab 切换动画
   */
  import type { Snippet, Component } from 'svelte';
  import type { TabGroup } from '$lib/stores/nodeLayoutStore';
  import { getBlockDefinition } from './blockRegistry';
  import { X, GripVertical, Ungroup } from '@lucide/svelte';
  import { flip } from 'svelte/animate';
  import { dndzone } from 'svelte-dnd-action';
  import { settingsManager } from '$lib/settings/settingsManager';
  import { onMount, tick } from 'svelte';

  interface Props {
    /** Tab 分组配置 */
    group: TabGroup;
    /** 节点类型 */
    nodeType: string;
    /** 是否全屏模式 */
    isFullscreen?: boolean;
    /** 切换活动区块 */
    onSwitch: (index: number) => void;
    /** 解散分组 */
    onDissolve: () => void;
    /** 从分组移除区块 */
    onRemoveBlock?: (blockId: string) => void;
    /** 重排序区块 */
    onReorder?: (newOrder: string[]) => void;
    /** 渲染区块内容 */
    renderContent: Snippet<[string]>;
    class?: string;
  }

  let { 
    group, 
    nodeType, 
    isFullscreen = false, 
    onSwitch, 
    onDissolve, 
    onRemoveBlock,
    onReorder,
    renderContent, 
    class: className = '' 
  }: Props = $props();

  let editMode = $state(false);
  let tabsContainer: HTMLDivElement | null = $state(null);
  let indicatorStyle = $state('');

  // 获取面板设置（透明度和模糊）
  let panelSettings = $state(settingsManager.getSettings().panels);
  
  // 计算卡片样式 - 与 BlockCard 一致
  let cardStyle = $derived(
    `background: color-mix(in srgb, var(--card) ${panelSettings.topToolbarOpacity * 0.4}%, transparent); backdrop-filter: blur(${panelSettings.topToolbarBlur}px);`
  );

  // 更新指示器位置
  async function updateIndicator() {
    await tick();
    if (!tabsContainer) return;
    const buttons = tabsContainer.querySelectorAll('.tab-btn');
    const activeBtn = buttons[group.activeIndex] as HTMLElement;
    if (activeBtn) {
      const containerRect = tabsContainer.getBoundingClientRect();
      const btnRect = activeBtn.getBoundingClientRect();
      const left = btnRect.left - containerRect.left;
      indicatorStyle = `width: ${btnRect.width}px; transform: translateX(${left}px);`;
    }
  }

  onMount(() => {
    // 监听设置变化
    settingsManager.addListener((s) => {
      panelSettings = s.panels;
    });
    updateIndicator();
  });

  // 监听 activeIndex 变化更新指示器
  $effect(() => {
    group.activeIndex;
    updateIndicator();
  });

  // 获取区块定义
  let blockDefs = $derived(
    group.blockIds.map(id => ({
      id,
      def: getBlockDefinition(nodeType, id)
    })).filter(item => item.def !== undefined)
  );

  // 当前活动区块 ID
  let activeBlockId = $derived(group.blockIds[group.activeIndex] ?? group.blockIds[0] ?? '');

  // 拖拽项
  let dndItems = $derived(blockDefs.map((item, i) => ({ id: item.id, def: item.def!, index: i })));

  function handleDndConsider(e: CustomEvent<{ items: typeof dndItems }>) {
    // 临时更新用于视觉反馈
  }

  function handleDndFinalize(e: CustomEvent<{ items: typeof dndItems }>) {
    const newOrder = e.detail.items.map(item => item.id);
    onReorder?.(newOrder);
  }
</script>

<div 
  class="tab-group-card flex-1 flex flex-col {isFullscreen ? 'border-2 border-primary/60 rounded-md shadow-md' : 'rounded-lg border shadow-sm'} {className}"
  style={cardStyle}
>
  <!-- 标签栏 - 居中布局，左右对称 -->
  <div class="tab-bar drag-handle flex items-center justify-center {isFullscreen ? 'p-1.5 border-b bg-muted/30' : 'p-1'} shrink-0 cursor-move">
    <!-- 中心容器：切换按钮 | 凹槽分隔 | 操作按钮 -->
    <div class="flex items-center gap-1 bg-muted/40 rounded-lg px-1 py-0.5">
      <!-- 左侧：切换按钮 -->
      {#if editMode && blockDefs.length > 0}
        <!-- 编辑模式：可拖拽排序和移除 -->
        <div 
          class="flex items-center gap-0.5 overflow-x-auto" 
          use:dndzone={{ items: dndItems, flipDurationMs: 200, type: 'tab-group-items' }} 
          onconsider={handleDndConsider} 
          onfinalize={handleDndFinalize}
        >
          {#each dndItems as item (item.id)}
            {@const Icon = item.def.icon as Component | undefined}
            <div 
              class="tab-item-edit flex items-center gap-1 px-1.5 py-1 rounded-md text-sm font-medium bg-muted/50 border border-dashed cursor-move" 
              animate:flip={{ duration: 200 }}
            >
              <GripVertical class="w-3 h-3 text-muted-foreground" />
              {#if Icon}<Icon class="w-3.5 h-3.5 {item.def.iconClass}" />{/if}
              {#if onRemoveBlock && blockDefs.length > 2}
                <button 
                  type="button" 
                  class="p-0.5 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive" 
                  onclick={() => onRemoveBlock(item.id)}
                  title="从分组移除"
                >
                  <X class="w-3 h-3" />
                </button>
              {/if}
            </div>
          {/each}
        </div>
      {:else}
        <!-- 普通模式：带滑动指示器的切换按钮 -->
        <div class="relative flex items-center gap-0.5 overflow-x-auto" bind:this={tabsContainer}>
          <!-- 滑动指示器背景 -->
          <div 
            class="tab-indicator absolute top-0 h-full rounded-md bg-primary/20 ring-1 ring-primary/40 shadow-sm pointer-events-none"
            style={indicatorStyle}
          ></div>
          {#each blockDefs as item, index (item.id)}
            {@const Icon = item.def?.icon as Component | undefined}
            <button 
              type="button" 
              class="tab-btn relative z-[1] flex items-center justify-center p-1.5 rounded-md" 
              onclick={() => onSwitch(index)} 
              title={item.def?.title}
            >
              {#if Icon}<Icon class="w-4 h-4 {item.def?.iconClass}" />{/if}
            </button>
          {/each}
        </div>
      {/if}

      <!-- 凹槽分隔线 -->
      <div class="w-px h-5 bg-border/60 mx-1"></div>

      <!-- 右侧：操作按钮 -->
      <div class="flex items-center gap-0.5">
        {#if blockDefs.length > 0}
          <button 
            type="button" 
            class="p-1.5 rounded-md transition-all {editMode ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}" 
            onclick={() => editMode = !editMode} 
            title={editMode ? '完成编辑' : '编辑标签'}
          >
            <GripVertical class="w-3.5 h-3.5" />
          </button>
        {/if}
        <button 
          type="button" 
          class="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all" 
          onclick={onDissolve} 
          title="解散分组"
        >
          <Ungroup class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  </div>

  <!-- 内容区域 -->
  <div class="tab-content flex-1 min-h-0 overflow-auto {isFullscreen ? 'p-2' : 'p-2'}">
    <div class="h-full">
      {#if activeBlockId}
        {@render renderContent(activeBlockId)}
      {:else}
        <div class="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
          <span class="text-sm">无可用区块</span>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .tab-bar::-webkit-scrollbar { display: none; }
  .tab-bar { scrollbar-width: none; -ms-overflow-style: none; }
  .tab-item-edit { user-select: none; }
  /* 滑动指示器动画 */
  .tab-indicator {
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }
</style>
