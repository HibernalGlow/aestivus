<script lang="ts">
  /**
   * 浮动节点面板 - 可拖拽的节点选择器
   */
  import { getNodesByCategory } from '$lib/stores/nodeRegistry';
  import { flowStore } from '$lib/stores';
  import { fullscreenNodeStore } from '$lib/stores/fullscreenNode.svelte';
  import {
    Clipboard, Folder, FileInput, Package, Search, AlertTriangle,
    FolderSync, FileText, Video, Terminal, GripHorizontal, ChevronDown, ChevronRight,
    Maximize2
  } from '@lucide/svelte';
  import { settingsManager } from '$lib/settings/settingsManager';
  import { onMount } from 'svelte';

  // 获取面板设置
  let panelSettings = $state(settingsManager.getSettings().panels);
  
  // 计算侧边栏样式 - 使用 color-mix 实现带颜色的透明效果
  let sidebarStyle = $derived(
    `background: color-mix(in srgb, var(--card) ${panelSettings.sidebarOpacity}%, transparent); backdrop-filter: blur(${panelSettings.sidebarBlur}px);`
  );

  onMount(() => {
    // 监听设置变化
    settingsManager.addListener((s) => {
      panelSettings = s.panels;
    });
  });

  const icons: Record<string, typeof Clipboard> = {
    Clipboard, Folder, FileInput, Package, Search, AlertTriangle,
    FolderSync, FileText, Video, Terminal
  };

  const categories = [
    { id: 'input', label: '输入', color: 'text-green-600' },
    { id: 'tool', label: '工具', color: 'text-blue-600' },
    { id: 'output', label: '输出', color: 'text-amber-600' }
  ];

  // 拖拽和调整大小状态
  let isDragging = $state(false);
  let isResizing = $state(false);
  let position = $state({ x: 20, y: 100 });
  let size = $state({ width: 180, height: 320 });
  let dragOffset = { x: 0, y: 0 };
  let resizeStart = { x: 0, y: 0, width: 0, height: 0 };
  let collapsed = $state(false);
  let expandedCategories = $state<Record<string, boolean>>({ input: true, tool: true, output: true });

  let nodeIdCounter = 1;

  // 拖拽移动
  function onMouseDown(e: MouseEvent) {
    if ((e.target as HTMLElement).closest('button')) return;
    if ((e.target as HTMLElement).closest('.resize-handle')) return;
    isDragging = true;
    dragOffset = { x: e.clientX - position.x, y: e.clientY - position.y };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }

  function onMouseMove(e: MouseEvent) {
    if (isDragging) {
      position = { x: e.clientX - dragOffset.x, y: e.clientY - dragOffset.y };
    } else if (isResizing) {
      const newWidth = Math.max(140, Math.min(400, resizeStart.width + (e.clientX - resizeStart.x)));
      const newHeight = Math.max(150, Math.min(600, resizeStart.height + (e.clientY - resizeStart.y)));
      size = { width: newWidth, height: newHeight };
    }
  }

  function onMouseUp() {
    isDragging = false;
    isResizing = false;
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
  }

  // 调整大小
  function onResizeStart(e: MouseEvent) {
    e.stopPropagation();
    isResizing = true;
    resizeStart = { x: e.clientX, y: e.clientY, width: size.width, height: size.height };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }

  function addNode(type: string, label: string) {
    const node = {
      id: `node-${nodeIdCounter++}-${Date.now()}`,
      type,
      position: { x: 300 + Math.random() * 100, y: 200 + Math.random() * 100 },
      data: { label, status: 'idle' as const }
    };
    flowStore.addNode(node);
  }

  function openFullscreen(type: string) {
    fullscreenNodeStore.open(type);
  }

  function onDragStart(event: DragEvent, type: string, label: string) {
    if (event.dataTransfer) {
      event.dataTransfer.setData('application/json', JSON.stringify({ type, label }));
      event.dataTransfer.effectAllowed = 'move';
    }
  }

  function toggleCategory(id: string) {
    expandedCategories[id] = !expandedCategories[id];
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="fixed z-50 select-none"
  style="left: {position.x}px; top: {position.y}px; width: {size.width}px;"
  onmousedown={onMouseDown}
>
  <!-- 内层面板容器 -->
  <div class="rounded-2xl shadow-xl overflow-hidden" style={sidebarStyle}>
  <!-- 标题栏 - iOS 风格 -->
  <div class="flex items-center justify-between px-3 py-2.5 cursor-move">
    <div class="flex items-center gap-2">
      <!-- 六个点拖拽指示器 (2x3) -->
      <div class="grid grid-cols-2 gap-0.5">
        <div class="w-1 h-1 rounded-full bg-muted-foreground/40"></div>
        <div class="w-1 h-1 rounded-full bg-muted-foreground/40"></div>
        <div class="w-1 h-1 rounded-full bg-muted-foreground/40"></div>
        <div class="w-1 h-1 rounded-full bg-muted-foreground/40"></div>
        <div class="w-1 h-1 rounded-full bg-muted-foreground/40"></div>
        <div class="w-1 h-1 rounded-full bg-muted-foreground/40"></div>
      </div>
      <span class="text-sm font-medium">节点</span>
    </div>
    <button
      class="p-1 rounded-lg hover:bg-muted/50 transition-colors"
      onclick={() => collapsed = !collapsed}
    >
      {#if collapsed}
        <ChevronRight class="w-4 h-4" />
      {:else}
        <ChevronDown class="w-4 h-4" />
      {/if}
    </button>
  </div>

  <!-- 节点列表 -->
  {#if !collapsed}
    <div class="overflow-y-auto p-2 space-y-2 scrollbar-hide" style="max-height: {size.height - 44}px;">
      {#each categories as category}
        {@const nodes = getNodesByCategory(category.id)}
        {#if nodes.length > 0}
          <div>
            <button
              class="w-full flex items-center gap-1 text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1 hover:text-foreground"
              onclick={() => toggleCategory(category.id)}
            >
              {#if expandedCategories[category.id]}
                <ChevronDown class="w-3 h-3" />
              {:else}
                <ChevronRight class="w-3 h-3" />
              {/if}
              {category.label}
            </button>
            {#if expandedCategories[category.id]}
              <div class="space-y-0.5 ml-1">
                {#each nodes as nodeDef}
                  {@const Icon = icons[nodeDef.icon] || Terminal}
                  <div class="flex items-center gap-1 group">
                    <button
                      class="flex-1 flex items-center gap-2 px-2 py-1.5 rounded text-left hover:bg-muted transition-colors cursor-grab active:cursor-grabbing text-sm"
                      draggable="true"
                      onclick={() => addNode(nodeDef.type, nodeDef.label)}
                      ondragstart={(e) => onDragStart(e, nodeDef.type, nodeDef.label)}
                    >
                      <Icon class="w-3.5 h-3.5 {category.color}" />
                      <span class="truncate">{nodeDef.label}</span>
                    </button>
                    <!-- 全屏打开按钮 -->
                    <button
                      class="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-muted transition-all"
                      onclick={() => openFullscreen(nodeDef.type)}
                      title="全屏打开"
                    >
                      <Maximize2 class="w-3 h-3 text-muted-foreground" />
                    </button>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
      {/each}
    </div>
    
  {/if}
  </div>
  
  <!-- 调整大小把手 - iOS 风格弯曲回旋镖形状 -->
  {#if !collapsed}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div 
      class="resize-handle absolute bottom-0 right-0 w-5 h-5 cursor-se-resize flex items-center justify-center opacity-50 hover:opacity-100 transition-all"
      onmousedown={onResizeStart}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" class="text-muted-foreground">
        <!-- iOS 风格弯曲回旋镖把手 -->
        <path d="M14 2C14 8.627 8.627 14 2 14" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" fill="none"/>
      </svg>
    </div>
  {/if}
</div>
