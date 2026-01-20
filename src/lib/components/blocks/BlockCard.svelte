<script lang="ts">
  /**
   * BlockCard - 通用区块卡片容器（Bento Grid 风格 + Magic Card 效果）
   * 支持普通模式（Bento Grid）和全屏模式（GridStack）
   * 特性：鼠标跟随聚光灯、悬停动画、精致阴影、暗色模式优化
   */
  import { ChevronDown, ChevronRight, ArrowRight, ArrowUp, ArrowDown, ArrowLeft, Plus, Minus, Move } from '@lucide/svelte';
  import { slide } from 'svelte/transition';
  import { settingsManager } from '$lib/settings/settingsManager';
  import { onMount } from 'svelte';
  import type { Snippet } from 'svelte';

  interface Props {
    /** 区块 ID（用于布局持久化等场景） */
    id: string;
    /** 标题 */
    title: string;
    /** Lucide 图标组件 */
    icon?: typeof ChevronDown;
    /** 图标颜色类 */
    iconClass?: string;
    /** 是否可折叠 */
    collapsible?: boolean;
    /** 默认展开状态 */
    defaultExpanded?: boolean;
    /** 是否全屏模式（自动启用 fullHeight） */
    isFullscreen?: boolean;
    /** 隐藏标题栏 */
    hideHeader?: boolean;
    /** 紧凑模式 */
    compact?: boolean;
    /** 占满高度（isFullscreen 时自动为 true） */
    fullHeight?: boolean;
    /** 自定义类名 */
    class?: string;
    /** 内容 */
    children: Snippet;
    /** 标题栏额外内容 */
    headerExtra?: Snippet;
    /** 折叠时显示的迷你内容（摘要信息） */
    miniContent?: Snippet;
    /** Bento 风格：背景组件 */
    background?: Snippet;
    /** Bento 风格：描述文字 */
    description?: string;
    /** Bento 风格：CTA 链接 */
    href?: string;
    /** Bento 风格：CTA 文字 */
    cta?: string;
    /** 启用 Bento 悬停动画 */
    bentoHover?: boolean;
    /** Magic Card：渐变光圈大小（自适应卡片尺寸） */
    magicGradientSize?: number;
    /** Magic Card：渐变颜色（默认使用主题 primary 色） */
    magicGradientColor?: string;
    /** Magic Card：渐变透明度 */
    magicGradientOpacity?: number;
    /** 是否启用尺寸编辑模式 */
    editMode?: boolean;
    /** 当前 X 位置（全屏模式） */
    currentX?: number;
    /** 当前 Y 位置（全屏模式） */
    currentY?: number;
    /** 当前宽度（grid 列数） */
    currentW?: number;
    /** 当前高度（grid 行数） */
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
    id: _id,
    title,
    icon: Icon,
    iconClass = 'text-muted-foreground',
    collapsible = false,
    defaultExpanded = true,
    isFullscreen = false,
    hideHeader = false,
    compact = false,
    fullHeight: fullHeightProp = false,
    class: className = '',
    children,
    headerExtra,
    miniContent,
    background,
    description,
    href,
    cta,
    bentoHover = false,
    magicGradientSize,
    magicGradientColor = "hsl(var(--primary) / 0.4)",
    magicGradientOpacity = 0.8,
    editMode = false,
    currentX = 0,
    currentY = 0,
    currentW = 1,
    currentH = 1,
    onXChange,
    onYChange,
    onWidthChange,
    onHeightChange,
  }: Props = $props();

  // isFullscreen 自动启用 fullHeight
  let fullHeight = $derived(fullHeightProp || isFullscreen);
  
  let isExpanded = $state(true);
  
  // 响应 defaultExpanded 变化
  $effect(() => {
    isExpanded = defaultExpanded;
  });

  // 获取面板设置（透明度和模糊）
  let panelSettings = $state(settingsManager.getSettings().panels);
  
  // 计算卡片样式 - 使用 color-mix 实现带颜色的透明效果
  let cardStyle = $derived(
    `background: color-mix(in srgb, var(--card) ${panelSettings.topToolbarOpacity * 0.4}%, transparent); backdrop-filter: blur(${panelSettings.topToolbarBlur}px);`
  );

  // ========== Magic Card 鼠标跟随效果 ==========
  let cardRef: HTMLDivElement | undefined = $state();
  let mouseX = $state(0);
  let mouseY = $state(0);
  let isHovering = $state(false);
  let cardWidth = $state(200);
  let cardHeight = $state(200);

  // 自适应渐变大小：基于卡片对角线长度
  let adaptiveGradientSize = $derived(
    magicGradientSize ?? Math.max(cardWidth, cardHeight) * 0.8
  );

  // 计算渐变背景样式
  let gradientStyle = $derived(
    `radial-gradient(${adaptiveGradientSize}px circle at ${mouseX}px ${mouseY}px, ${magicGradientColor}, transparent 100%)`
  );

  function handleMouseMove(e: MouseEvent) {
    if (!cardRef) return;
    const rect = cardRef.getBoundingClientRect();
    mouseX = e.clientX - rect.left;
    mouseY = e.clientY - rect.top;
  }

  function handleMouseEnter() {
    isHovering = true;
    if (cardRef) {
      cardWidth = cardRef.offsetWidth;
      cardHeight = cardRef.offsetHeight;
    }
  }

  function handleMouseLeave() {
    isHovering = false;
  }

  onMount(() => {
    settingsManager.addListener((s) => {
      panelSettings = s.panels;
    });
    // 初始化卡片尺寸
    if (cardRef) {
      cardWidth = cardRef.offsetWidth;
      cardHeight = cardRef.offsetHeight;
    }
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

  function toggleExpanded() {
    if (collapsible) isExpanded = !isExpanded;
  }
</script>

<div 
  bind:this={cardRef}
  onmousemove={handleMouseMove}
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  class="block-card group relative overflow-hidden rounded-xl
    {isFullscreen ? 'h-full flex flex-col' : ''} 
    {fullHeight ? 'h-full flex flex-col' : ''} 
    {bentoHover ? 'bento-card' : ''}
    {className}"
  style={cardStyle}
>
  <!-- Bento 背景层 -->
  {#if background}
    <div class="absolute inset-0 z-0 overflow-hidden">
      {@render background()}
    </div>
  {/if}
  
  <!-- 悬停遮罩层 -->
  <div class="pointer-events-none absolute inset-0 z-[1] transition-all duration-300 group-hover:bg-black/[.03] dark:group-hover:bg-neutral-800/10"></div>
  
  <!-- Magic Card 渐变光效层 -->
  <div
    class="magic-glow pointer-events-none absolute -inset-px rounded-xl z-[2]"
    style="--glow-bg: {gradientStyle}; --glow-opacity: {isHovering ? magicGradientOpacity : 0};"
  ></div>
  
  <!-- 标题栏 -->
  {#if !hideHeader}
    <div 
      class="relative z-10 flex items-center justify-between shrink-0 transition-all duration-300
        {compact ? 'px-2 py-1' : (isFullscreen ? 'p-3 border-b border-border/50' : 'p-3')}
        {bentoHover ? 'group-hover:-translate-y-1' : ''}"
    >
      <button
        type="button"
        class="flex items-center gap-1.5 text-left"
        onclick={toggleExpanded}
        disabled={!collapsible}
      >
        {#if collapsible}
          {#if isExpanded}
            <ChevronDown class="h-3 w-3 text-muted-foreground transition-transform duration-300" />
          {:else}
            <ChevronRight class="h-3 w-3 text-muted-foreground transition-transform duration-300" />
          {/if}
        {/if}
        
        {#if Icon}
          <Icon class="w-4 h-4 origin-left transition-all duration-300 ease-in-out {iconClass}
            {bentoHover ? 'group-hover:scale-90' : ''}" />
        {/if}
        
        <span class="transition-colors duration-300 {isFullscreen ? 'font-semibold text-foreground' : 'text-xs font-semibold text-foreground/90'}">{title}</span>
      </button>
      
      {#if headerExtra}
        <div class="flex items-center gap-1">
          {@render headerExtra()}
        </div>
      {/if}
    </div>
  {/if}
  
  <!-- Bento 描述文字 -->
  {#if description && !hideHeader}
    <p class="relative z-10 px-3 pb-2 text-sm text-muted-foreground transition-all duration-300
      {bentoHover ? 'group-hover:-translate-y-1' : ''}">
      {description}
    </p>
  {/if}
  
  <!-- 内容区 -->
  {#if isExpanded || hideHeader}
    <div 
      class="relative z-10 transition-all duration-300 {hideHeader ? '' : (compact ? 'px-2 pb-2' : 'px-3 pb-3')} {fullHeight ? 'flex-1 min-h-0 flex flex-col overflow-hidden' : ''} {bentoHover ? 'group-hover:-translate-y-1' : ''}"
      transition:slide={{ duration: 150 }}
    >
      {@render children()}
    </div>
  {:else if miniContent}
    <div class="relative z-10 px-3 pb-2 text-sm text-muted-foreground">
      {@render miniContent()}
    </div>
  {/if}
  
  <!-- Bento CTA 按钮（悬停显示） -->
  {#if cta && href && bentoHover}
    <div class="pointer-events-none absolute bottom-0 left-0 right-0 z-10 flex translate-y-10 transform-gpu flex-row items-center p-3 opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100">
      <a 
        {href} 
        class="pointer-events-auto inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium text-foreground/80 hover:text-foreground hover:bg-muted/50 transition-colors"
      >
        {cta}
        <ArrowRight class="h-4 w-4" />
      </a>
    </div>
  {/if}
  
  <!-- 编辑模式：尺寸调整控制器覆盖层 -->
  {#if editMode && onWidthChange}
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
  /* Magic Card 渐变光效 */
  .magic-glow {
    background: var(--glow-bg);
    opacity: var(--glow-opacity);
    transition: opacity 0.3s ease;
  }
  
  /* Bento 卡片样式 - 精致阴影和边框 */
  .bento-card {
    /* 亮色模式 */
    box-shadow: 
      0 0 0 1px rgba(0, 0, 0, 0.03),
      0 2px 4px rgba(0, 0, 0, 0.05),
      0 12px 24px rgba(0, 0, 0, 0.05);
    border: 1px solid transparent;
  }
  
  /* 暗色模式 */
  :global(.dark) .bento-card {
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 -20px 80px -20px rgba(255, 255, 255, 0.12) inset;
  }
  
  /* 普通卡片保持原有边框 */
  .block-card:not(.bento-card) {
    border: 1px solid hsl(var(--border));
  }
  
  /* 全屏模式特殊边框 */
  .block-card:not(.bento-card).h-full {
    border-color: hsl(var(--primary) / 0.4);
  }

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
