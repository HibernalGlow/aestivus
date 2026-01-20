<script lang="ts">
  /**
   * TabGroupCard - Tab 分组卡片组件
   * 
   * 虚拟分组模式：区块始终在 gridLayout 中，这里只负责渲染和切换
   * 使用 svelte-motion 实现平滑的 Tab 切换动画
   */
  import type { Snippet, Component } from 'svelte';
  import type { TabGroup } from '$lib/stores/nodeLayoutStore';
  import { getBlockDefinition } from './blockRegistry';
  import { X, GripVertical, Ungroup, ChevronLeft, ChevronRight, ChevronUp, ChevronDown, Plus, Minus, ArrowUp, ArrowDown, ArrowLeft, ArrowRight } from '@lucide/svelte';
  import { flip } from 'svelte/animate';
  import { dndzone } from 'svelte-dnd-action';
  import { settingsManager } from '$lib/settings/settingsManager';
  import { onMount } from 'svelte';
  import { Motion, AnimateSharedLayout } from 'svelte-motion';

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
    /** 是否启用区块尺寸编辑模式 */
    sizeEditMode?: boolean;
    /** 当前 X 位置（全屏模式） */
    currentX?: number;
    /** 当前 Y 位置（全屏模式） */
    currentY?: number;
    /** 当前宽度 */
    currentW?: number;
    /** 当前高度 */
    currentH?: number;
    /** X 位置变化回调（全屏模式） */
    onXChange?: (delta: number) => void;
    /** Y 位置变化回调（全屏模式） */
    onYChange?: (delta: number) => void;
    /** 宽度变化回调 */
    onWidthChange?: (delta: number) => void;
    /** 高度变化回调 */
    onHeightChange?: (delta: number) => void;
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
    class: className = '',
    sizeEditMode = false,
    currentX = 0,
    currentY = 0,
    currentW = 1,
    currentH = 1,
    onXChange,
    onYChange,
    onWidthChange,
    onHeightChange
  }: Props = $props();

  let editMode = $state(false);

  // 获取面板设置（透明度和模糊）
  let panelSettings = $state(settingsManager.getSettings().panels);
  
  // 计算卡片样式 - 与 BlockCard 一致
  let cardStyle = $derived(
    `background: color-mix(in srgb, var(--card) ${panelSettings.topToolbarOpacity * 0.4}%, transparent); backdrop-filter: blur(${panelSettings.topToolbarBlur}px);`
  );

  onMount(() => {
    // 监听设置变化
    settingsManager.addListener((s) => {
      panelSettings = s.panels;
    });
  });

  // ========== 长按检测和直接编辑功能 ==========
  let longPressTimer: ReturnType<typeof setTimeout> | null = null;
  const LONG_PRESS_DELAY = 500; // 长按阈值 500ms
  
  // 编辑模式状态
  let editingPosition = $state(false);
  let editingSize = $state(false);
  let tempX = $state('');
  let tempY = $state('');
  let tempW = $state('');
  let tempH = $state('');

  // 创建长按处理函数
  function createLongPressHandler(
    normalAction: () => void,
    longPressAction: () => void
  ) {
    let isLongPress = false;
    
    return {
      onMouseDown: () => {
        isLongPress = false;
        longPressTimer = setTimeout(() => {
          isLongPress = true;
          longPressAction();
        }, LONG_PRESS_DELAY);
      },
      onMouseUp: () => {
        if (longPressTimer) {
          clearTimeout(longPressTimer);
          longPressTimer = null;
        }
        if (!isLongPress) {
          normalAction();
        }
      },
      onMouseLeave: () => {
        if (longPressTimer) {
          clearTimeout(longPressTimer);
          longPressTimer = null;
        }
      }
    };
  }

  // 位置编辑相关
  function startEditPosition() {
    tempX = String(currentX);
    tempY = String(currentY);
    editingPosition = true;
  }

  function confirmEditPosition() {
    const newX = parseInt(tempX) || 0;
    const newY = parseInt(tempY) || 0;
    const deltaX = newX - currentX;
    const deltaY = newY - currentY;
    if (deltaX !== 0 && onXChange) onXChange(deltaX);
    if (deltaY !== 0 && onYChange) onYChange(deltaY);
    editingPosition = false;
  }

  function cancelEditPosition() {
    editingPosition = false;
  }

  // 尺寸编辑相关
  function startEditSize() {
    tempW = String(currentW);
    tempH = String(currentH);
    editingSize = true;
  }

  function confirmEditSize() {
    const newW = Math.max(1, Math.min(isFullscreen ? 4 : 2, parseInt(tempW) || 1));
    const newH = Math.max(1, Math.min(isFullscreen ? 6 : 4, parseInt(tempH) || 1));
    const deltaW = newW - currentW;
    const deltaH = newH - currentH;
    if (deltaW !== 0 && onWidthChange) onWidthChange(deltaW);
    if (deltaH !== 0 && onHeightChange) onHeightChange(deltaH);
    editingSize = false;
  }

  function cancelEditSize() {
    editingSize = false;
  }

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
  class="tab-group-card h-full flex flex-col overflow-hidden {isFullscreen ? 'border-2 border-primary/60 rounded-md shadow-md' : 'rounded-lg border shadow-sm'} {className}"
  style={cardStyle}
>
  <!-- 标签栏 - 居中布局，左右对称 -->
  <div class="tab-bar flex items-center justify-center {isFullscreen ? 'p-1.5 border-b bg-muted/30 drag-handle cursor-move' : 'p-1'} shrink-0">
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
        <!-- 普通模式：带动画的切换按钮 -->
        <div class="relative flex items-center gap-0.5 overflow-x-auto">
          <AnimateSharedLayout>
            {#each blockDefs as item, index (item.id)}
              {@const isActive = index === group.activeIndex}
              {@const Icon = item.def?.icon as Component | undefined}
              <button 
                type="button" 
                class="tab-item relative z-[1] flex items-center justify-center p-1.5 rounded-md" 
                onclick={() => onSwitch(index)} 
                title={item.def?.title}
              >
                {#if isActive}
                  <Motion
                    layoutId="active-tab-bg"
                    transition={{ duration: 0.2, type: 'spring', stiffness: 300, damping: 30 }}
                    let:motion
                  >
                    <div
                      use:motion
                      class="absolute inset-0 rounded-md bg-primary/20 ring-1 ring-primary/40 shadow-sm"
                    ></div>
                  </Motion>
                {/if}
                {#if Icon}<Icon class="relative w-4 h-4 {item.def?.iconClass}" />{/if}
              </button>
            {/each}
          </AnimateSharedLayout>
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
      
      <!-- 尺寸编辑按钮移除 - 改用覆盖层 -->
    </div>
  </div>

  <!-- 内容区域 -->
  <div class="tab-content flex-1 min-h-0 overflow-hidden {isFullscreen ? 'p-2' : 'p-2'}">
    <div class="h-full overflow-hidden">
      {#if activeBlockId}
        {@render renderContent(activeBlockId)}
      {:else}
        <div class="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
          <span class="text-sm">无可用区块</span>
        </div>
      {/if}
    </div>
  </div>
  
  <!-- 编辑模式：尺寸调整控制器覆盖层 -->
  {#if sizeEditMode && onWidthChange}
    {@const maxW = isFullscreen ? 4 : 2}
    {@const maxH = isFullscreen ? 6 : 4}
    {@const sizeUpHandler = onHeightChange ? createLongPressHandler(() => onHeightChange(-1), () => onHeightChange(-(currentH - 1))) : null}
    {@const sizeDownHandler = onHeightChange ? createLongPressHandler(() => onHeightChange(1), () => onHeightChange(maxH - currentH)) : null}
    {@const sizeLeftHandler = createLongPressHandler(() => onWidthChange(-1), () => onWidthChange(-(currentW - 1)))}
    {@const sizeRightHandler = createLongPressHandler(() => onWidthChange(1), () => onWidthChange(maxW - currentW))}
    <div class="absolute inset-0 z-50 pointer-events-none flex flex-col items-center justify-center p-2">
      <!-- 半透明背景 -->
      <div class="absolute inset-0 bg-primary/5 backdrop-blur-[2px] pointer-events-auto rounded-lg"></div>
      
      <!-- 调整控制面板 -->
      <div class="relative pointer-events-auto bg-card/95 backdrop-blur-sm border-2 border-primary rounded-lg shadow-xl p-3 max-w-full">
        <div class="flex gap-4">
          <!-- 左侧：位置调整（十字方向键，仅全屏模式） -->
          {#if isFullscreen && onXChange && onYChange}
            {@const upHandler = createLongPressHandler(() => onYChange(-1), () => onYChange(-currentY))}
            {@const downHandler = createLongPressHandler(() => onYChange(1), () => onYChange(10))}
            {@const leftHandler = createLongPressHandler(() => onXChange(-1), () => onXChange(-currentX))}
            {@const rightHandler = createLongPressHandler(() => onXChange(1), () => onXChange(4 - currentW - currentX))}
            <div class="flex flex-col items-center gap-1">
              <span class="text-xs font-medium text-muted-foreground mb-1">位置</span>
              <div class="grid grid-cols-3 gap-0.5">
                <!-- 空 -->
                <div class="w-6 h-6"></div>
                <!-- 上 -->
                <button
                  type="button"
                  class="w-6 h-6 rounded-md bg-muted hover:bg-primary hover:text-primary-foreground transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
                  onmousedown={upHandler.onMouseDown}
                  onmouseup={upHandler.onMouseUp}
                  onmouseleave={upHandler.onMouseLeave}
                  disabled={currentY <= 0}
                  title="上移 (长按跳到顶部)"
                >
                  <ArrowUp class="w-3 h-3" />
                </button>
                <!-- 空 -->
                <div class="w-6 h-6"></div>
                <!-- 左 -->
                <button
                  type="button"
                  class="w-6 h-6 rounded-md bg-muted hover:bg-primary hover:text-primary-foreground transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
                  onmousedown={leftHandler.onMouseDown}
                  onmouseup={leftHandler.onMouseUp}
                  onmouseleave={leftHandler.onMouseLeave}
                  disabled={currentX <= 0}
                  title="左移 (长按跳到最左)"
                >
                  <ArrowLeft class="w-3 h-3" />
                </button>
                <!-- 中心（显示坐标/编辑） -->
                {#if editingPosition}
                  <div class="w-12 h-6 flex items-center justify-center gap-0.5 col-span-1">
                    <input
                      type="number"
                      bind:value={tempX}
                      class="w-5 h-5 text-[9px] text-center bg-muted border border-primary rounded p-0"
                      min="0"
                      max={4 - currentW}
                      onkeydown={(e) => e.key === 'Enter' && confirmEditPosition()}
                    />
                    <input
                      type="number"
                      bind:value={tempY}
                      class="w-5 h-5 text-[9px] text-center bg-muted border border-primary rounded p-0"
                      min="0"
                      onkeydown={(e) => e.key === 'Enter' && confirmEditPosition()}
                      onblur={confirmEditPosition}
                    />
                  </div>
                {:else}
                  <button
                    type="button"
                    class="w-6 h-6 flex items-center justify-center text-[9px] font-mono text-muted-foreground hover:bg-muted rounded cursor-pointer"
                    onclick={startEditPosition}
                    title="点击编辑坐标"
                  >
                    {currentX},{currentY}
                  </button>
                {/if}
                <!-- 右 -->
                <button
                  type="button"
                  class="w-6 h-6 rounded-md bg-muted hover:bg-primary hover:text-primary-foreground transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
                  onmousedown={rightHandler.onMouseDown}
                  onmouseup={rightHandler.onMouseUp}
                  onmouseleave={rightHandler.onMouseLeave}
                  disabled={currentX >= (4 - currentW)}
                  title="右移 (长按跳到最右)"
                >
                  <ArrowRight class="w-3 h-3" />
                </button>
                <!-- 空 -->
                <div class="w-6 h-6"></div>
                <!-- 下 -->
                <button
                  type="button"
                  class="w-6 h-6 rounded-md bg-muted hover:bg-primary hover:text-primary-foreground transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
                  onmousedown={downHandler.onMouseDown}
                  onmouseup={downHandler.onMouseUp}
                  onmouseleave={downHandler.onMouseLeave}
                  title="下移 (长按跳到更下方)"
                >
                  <ArrowDown class="w-3 h-3" />
                </button>
                <!-- 空 -->
                <div class="w-6 h-6"></div>
              </div>
            </div>
            <!-- 分隔线 -->
            <div class="w-px bg-border/60 self-stretch"></div>
          {/if}
          
          <!-- 右侧：尺寸调整（十字方向键风格） -->
          <div class="flex flex-col items-center gap-1">
            <span class="text-xs font-medium text-muted-foreground mb-1">尺寸</span>
            <div class="grid grid-cols-3 gap-0.5">
              <!-- 空 -->
              <div class="w-6 h-6"></div>
              <!-- 上：减小高度 -->
              {#if onHeightChange && sizeUpHandler}
                <button
                  type="button"
                  class="w-6 h-6 rounded-md bg-muted hover:bg-primary hover:text-primary-foreground transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
                  onmousedown={sizeUpHandler.onMouseDown}
                  onmouseup={sizeUpHandler.onMouseUp}
                  onmouseleave={sizeUpHandler.onMouseLeave}
                  disabled={currentH <= 1}
                  title="减小高度 (长按到最小)"
                >
                  <ArrowUp class="w-3 h-3" />
                </button>
              {:else}
                <div class="w-6 h-6"></div>
              {/if}
              <!-- 空 -->
              <div class="w-6 h-6"></div>
              <!-- 左：减小宽度 -->
              <button
                type="button"
                class="w-6 h-6 rounded-md bg-muted hover:bg-primary hover:text-primary-foreground transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
                onmousedown={sizeLeftHandler.onMouseDown}
                onmouseup={sizeLeftHandler.onMouseUp}
                onmouseleave={sizeLeftHandler.onMouseLeave}
                disabled={currentW <= 1}
                title="减小宽度 (长按到最小)"
              >
                <ArrowLeft class="w-3 h-3" />
              </button>
              <!-- 中心（显示尺寸/编辑） -->
              {#if editingSize}
                <div class="w-12 h-6 flex items-center justify-center gap-0.5 col-span-1">
                  <input
                    type="number"
                    bind:value={tempW}
                    class="w-5 h-5 text-[9px] text-center bg-muted border border-primary rounded p-0"
                    min="1"
                    max={maxW}
                    onkeydown={(e) => e.key === 'Enter' && confirmEditSize()}
                  />
                  <input
                    type="number"
                    bind:value={tempH}
                    class="w-5 h-5 text-[9px] text-center bg-muted border border-primary rounded p-0"
                    min="1"
                    max={maxH}
                    onkeydown={(e) => e.key === 'Enter' && confirmEditSize()}
                    onblur={confirmEditSize}
                  />
                </div>
              {:else}
                <button
                  type="button"
                  class="w-6 h-6 flex items-center justify-center text-[9px] font-mono text-muted-foreground hover:bg-muted rounded cursor-pointer"
                  onclick={startEditSize}
                  title="点击编辑尺寸"
                >
                  {currentW}×{currentH}
                </button>
              {/if}
              <!-- 右：增加宽度 -->
              <button
                type="button"
                class="w-6 h-6 rounded-md bg-muted hover:bg-primary hover:text-primary-foreground transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
                onmousedown={sizeRightHandler.onMouseDown}
                onmouseup={sizeRightHandler.onMouseUp}
                onmouseleave={sizeRightHandler.onMouseLeave}
                disabled={currentW >= maxW}
                title="增大宽度 (长按到最大)"
              >
                <ArrowRight class="w-3 h-3" />
              </button>
              <!-- 空 -->
              <div class="w-6 h-6"></div>
              <!-- 下：增加高度 -->
              {#if onHeightChange && sizeDownHandler}
                <button
                  type="button"
                  class="w-6 h-6 rounded-md bg-muted hover:bg-primary hover:text-primary-foreground transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
                  onmousedown={sizeDownHandler.onMouseDown}
                  onmouseup={sizeDownHandler.onMouseUp}
                  onmouseleave={sizeDownHandler.onMouseLeave}
                  disabled={currentH >= maxH}
                  title="增大高度 (长按到最大)"
                >
                  <ArrowDown class="w-3 h-3" />
                </button>
              {:else}
                <div class="w-6 h-6"></div>
              {/if}
              <!-- 空 -->
              <div class="w-6 h-6"></div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 四角调整指示器 -->
      <div class="absolute top-0 left-0 w-2.5 h-2.5 border-t-2 border-l-2 border-primary rounded-tl pointer-events-none"></div>
      <div class="absolute top-0 right-0 w-2.5 h-2.5 border-t-2 border-r-2 border-primary rounded-tr pointer-events-none"></div>
      <div class="absolute bottom-0 left-0 w-2.5 h-2.5 border-b-2 border-l-2 border-primary rounded-bl pointer-events-none"></div>
      <div class="absolute bottom-0 right-0 w-2.5 h-2.5 border-b-2 border-r-2 border-primary rounded-br pointer-events-none"></div>
    </div>
  {/if}
</div>

<style>
  .tab-bar::-webkit-scrollbar { height: 4px; }
  .tab-bar::-webkit-scrollbar-track { background: transparent; }
  .tab-bar::-webkit-scrollbar-thumb { background: hsl(var(--muted-foreground) / 0.3); border-radius: 2px; }
  .tab-item-edit { user-select: none; }

  /* 隐藏数字输入框的调节箭头 */
  input::-webkit-outer-spin-button,
  input::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }
  input[type="number"] {
    -moz-appearance: textfield;
    appearance: textfield;
  }
</style>
