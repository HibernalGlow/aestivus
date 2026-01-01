<script lang="ts">
  /**
   * Dock - macOS 风格浮动 Dock 栏
   * 支持拖拽添加、点击全屏、多项目切换
   */
  import { dockStore, type DockItem } from '$lib/stores/dockStore.svelte';
  import { fullscreenNodeStore } from '$lib/stores/fullscreenNode.svelte';
  import { flowStore } from '$lib/stores';
  import { useMotionValue } from 'svelte-motion';
  import DockIcon from './DockIcon.svelte';
  import { X, ChevronLeft, ChevronRight, Settings, Minus } from '@lucide/svelte';
  import { flip } from 'svelte/animate';
  import { fade, fly } from 'svelte/transition';

  interface Props {
    class?: string;
  }

  let { class: className = '' }: Props = $props();

  // 鼠标位置（用于图标放大动画）
  let mouseX = useMotionValue(Infinity);

  // Dock 容器引用
  let dockRef = $state<HTMLDivElement | null>(null);

  // 拖拽状态
  let isDragOver = $state(false);

  // 右键菜单状态
  let contextMenu = $state<{ x: number; y: number; item: DockItem } | null>(null);

  // 处理鼠标移动
  function handleMouseMove(e: MouseEvent) {
    mouseX.set(e.clientX);
  }

  // 鼠标离开时重置
  function handleMouseLeave() {
    mouseX.set(Infinity);
  }

  // 点击图标 - 全屏显示
  function handleItemClick(item: DockItem) {
    if ($dockStore.activeItemId === item.nodeId) {
      // 已激活则关闭
      dockStore.deactivate();
      fullscreenNodeStore.close();
    } else {
      // 激活并全屏显示
      dockStore.activateItem(item.nodeId);
      fullscreenNodeStore.open(item.nodeId);
    }
  }

  // 右键菜单
  function handleContextMenu(e: MouseEvent, item: DockItem) {
    e.preventDefault();
    contextMenu = { x: e.clientX, y: e.clientY, item };
  }

  // 关闭右键菜单
  function closeContextMenu() {
    contextMenu = null;
  }

  // 从 Dock 移除
  function removeFromDock(item: DockItem) {
    dockStore.removeItem(item.nodeId);
    closeContextMenu();
  }

  // 处理拖拽进入
  function handleDragEnter(e: DragEvent) {
    e.preventDefault();
    isDragOver = true;
  }

  // 处理拖拽离开
  function handleDragLeave(e: DragEvent) {
    // 确保是离开 dock 区域
    const rect = dockRef?.getBoundingClientRect();
    if (rect && (e.clientX < rect.left || e.clientX > rect.right || 
        e.clientY < rect.top || e.clientY > rect.bottom)) {
      isDragOver = false;
    }
  }

  // 处理拖拽悬停
  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
  }

  // 处理放置
  function handleDrop(e: DragEvent) {
    e.preventDefault();
    isDragOver = false;

    const data = e.dataTransfer?.getData('application/json');
    if (!data) return;

    try {
      const { type, label, nodeId, icon } = JSON.parse(data);
      if (type && nodeId) {
        // 检查节点是否已存在于 flow 中，如果不存在则创建
        const existingNode = $flowStore.nodes.find(n => n.id === nodeId);
        if (!existingNode) {
          // 创建隐藏的节点（不在画布上显示位置）
          flowStore.addNode({
            id: nodeId,
            type,
            position: { x: -9999, y: -9999 },  // 放在画布外
            data: { label: label || type, status: 'idle' as const },
            hidden: true
          });
        }
        dockStore.addItem(nodeId, type, label || type, icon || 'Box');
      }
    } catch (err) {
      console.warn('Dock 放置数据解析失败:', err);
    }
  }

  // 键盘快捷键
  function handleKeyDown(e: KeyboardEvent) {
    if (!$dockStore.activeItemId) return;
    
    if (e.key === 'ArrowLeft' || (e.key === 'Tab' && e.shiftKey)) {
      e.preventDefault();
      dockStore.prevItem();
      const state = $dockStore;
      if (state.activeItemId) {
        fullscreenNodeStore.open(state.activeItemId);
      }
    } else if (e.key === 'ArrowRight' || (e.key === 'Tab' && !e.shiftKey)) {
      e.preventDefault();
      dockStore.nextItem();
      const state = $dockStore;
      if (state.activeItemId) {
        fullscreenNodeStore.open(state.activeItemId);
      }
    }
  }

  // 点击外部关闭右键菜单
  function handleWindowClick() {
    if (contextMenu) {
      closeContextMenu();
    }
  }
</script>

<svelte:window onkeydown={handleKeyDown} onclick={handleWindowClick} />

<!-- Dock 容器 -->
{#if $dockStore.items.length > 0 || isDragOver}
  <!-- svelte-ignore a11y_interactive_supports_focus -->
  <div
    bind:this={dockRef}
    class="fixed bottom-4 left-1/2 -translate-x-1/2 z-[60] {className}"
    onmousemove={handleMouseMove}
    onmouseleave={handleMouseLeave}
    ondragenter={handleDragEnter}
    ondragleave={handleDragLeave}
    ondragover={handleDragOver}
    ondrop={handleDrop}
    role="toolbar"
    aria-label="Dock"
    transition:fly={{ y: 100, duration: 300 }}
  >
    <div 
      class="flex items-end gap-2 px-3 py-2 rounded-2xl border shadow-2xl transition-all duration-200
        {isDragOver ? 'ring-2 ring-primary bg-primary/10' : 'bg-card/80'}"
      style="backdrop-filter: blur(16px);"
    >
      <!-- 导航按钮 -->
      {#if $dockStore.items.length > 1 && $dockStore.activeItemId}
        <button
          class="p-2 rounded-lg hover:bg-muted transition-colors"
          onclick={() => { dockStore.prevItem(); fullscreenNodeStore.open($dockStore.activeItemId!); }}
          title="上一个 (←)"
        >
          <ChevronLeft class="w-5 h-5" />
        </button>
      {/if}

      <!-- Dock 项目 -->
      {#each $dockStore.items as item (item.id)}
        <div animate:flip={{ duration: 200 }}>
          <DockIcon
            icon={item.icon}
            label={item.label}
            isActive={item.isActive}
            {mouseX}
            onclick={() => handleItemClick(item)}
            oncontextmenu={(e) => handleContextMenu(e, item)}
          />
        </div>
      {/each}

      <!-- 导航按钮 -->
      {#if $dockStore.items.length > 1 && $dockStore.activeItemId}
        <button
          class="p-2 rounded-lg hover:bg-muted transition-colors"
          onclick={() => { dockStore.nextItem(); fullscreenNodeStore.open($dockStore.activeItemId!); }}
          title="下一个 (→)"
        >
          <ChevronRight class="w-5 h-5" />
        </button>
      {/if}

      <!-- 分隔线 -->
      {#if $dockStore.items.length > 0}
        <div class="w-px h-10 bg-border mx-1"></div>
      {/if}

      <!-- 拖拽提示区域 -->
      <div 
        class="flex items-center justify-center w-12 h-12 rounded-xl border-2 border-dashed transition-colors
          {isDragOver ? 'border-primary bg-primary/10' : 'border-muted-foreground/30'}"
      >
        <Minus class="w-5 h-5 text-muted-foreground" />
      </div>
    </div>
  </div>
{:else}
  <!-- 空状态 - 拖拽提示 -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    bind:this={dockRef}
    class="fixed bottom-4 left-1/2 -translate-x-1/2 z-[60]"
    ondragenter={handleDragEnter}
    ondragleave={handleDragLeave}
    ondragover={handleDragOver}
    ondrop={handleDrop}
    role="region"
    aria-label="Dock 拖拽区域"
    transition:fade={{ duration: 200 }}
  >
    <div 
      class="flex items-center gap-2 px-4 py-3 rounded-2xl border-2 border-dashed transition-all duration-200
        {isDragOver ? 'border-primary bg-primary/10' : 'border-muted-foreground/30 bg-card/50'}"
      style="backdrop-filter: blur(8px);"
    >
      <Minus class="w-5 h-5 text-muted-foreground" />
      <span class="text-sm text-muted-foreground">拖拽节点到此处添加到 Dock</span>
    </div>
  </div>
{/if}

<!-- 右键菜单 -->
{#if contextMenu}
  <div
    class="fixed z-[100] min-w-[160px] rounded-lg border bg-popover p-1 shadow-lg"
    style="left: {contextMenu.x}px; top: {contextMenu.y - 80}px;"
    transition:fade={{ duration: 100 }}
  >
    <button
      class="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-muted transition-colors"
      onclick={() => removeFromDock(contextMenu!.item)}
    >
      <X class="w-4 h-4" />
      从 Dock 移除
    </button>
  </div>
{/if}
