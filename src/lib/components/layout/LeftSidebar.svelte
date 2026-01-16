<script lang="ts">
  /**
   * 左侧边栏 - 节点树面板
   * 支持悬停显示/隐藏、pin 固定、拖拽调整宽度
   */
  import { sidebarStore } from "$lib/stores/sidebar.svelte";
  import { settingsManager } from "$lib/settings/settingsManager";
  import HoverWrapper from "./HoverWrapper.svelte";
  import {
    Pin,
    PinOff,
    GripVertical,
    PanelLeftClose,
    LayoutTemplate,
  } from "@lucide/svelte";
  import NodeTreePalette from "$lib/components/flow/NodeTreePalette.svelte";
  import { flowStore } from "$lib/stores";

  // 面板设置
  let panelSettings = $state(settingsManager.getSettings().panels);
  let sidebarStyle = $derived(
    `background: color-mix(in srgb, var(--card) ${panelSettings.sidebarOpacity}%, transparent); backdrop-filter: blur(${panelSettings.sidebarBlur}px);`
  );

  // 侧边栏状态
  let isVisible = $state($sidebarStore.leftOpen);

  // 拖拽调整宽度
  let isResizing = $state(false);
  let startX = 0;
  let startWidth = 0;

  function handleResizeStart(e: MouseEvent) {
    isResizing = true;
    startX = e.clientX;
    startWidth = $sidebarStore.leftWidth;
    e.preventDefault();

    window.addEventListener("mousemove", handleResizeMove);
    window.addEventListener("mouseup", handleResizeEnd);
  }

  function handleResizeMove(e: MouseEvent) {
    if (!isResizing) return;
    const delta = e.clientX - startX;
    sidebarStore.setLeftWidth(startWidth + delta);
  }

  function handleResizeEnd() {
    isResizing = false;
    window.removeEventListener("mousemove", handleResizeMove);
    window.removeEventListener("mouseup", handleResizeEnd);
  }

  // 悬停显示/隐藏
  function handleVisibilityChange(visible: boolean) {
    if (!$sidebarStore.leftPinned) {
      sidebarStore.setLeftOpen(visible);
    }
  }

  // 切换 pin
  function togglePin() {
    sidebarStore.toggleLeftPin();
  }

  // 关闭侧边栏
  function closeSidebar() {
    sidebarStore.setLeftOpen(false);
  }

  // 监听设置变化
  $effect(() => {
    const callback = (s: any) => {
      panelSettings = s.panels;
    };
    settingsManager.addListener(callback);
    return () => settingsManager.removeListener(callback);
  });

  // 同步 store 状态
  $effect(() => {
    isVisible = $sidebarStore.leftOpen;
  });
</script>

<!-- 触发区域 -->
<div
  class="fixed top-0 left-0 bottom-0 w-2 z-50"
  onmouseenter={() =>
    !$sidebarStore.leftPinned && sidebarStore.setLeftOpen(true)}
  role="presentation"
></div>

<!-- 侧边栏容器 -->
<div
  class="fixed top-0 left-0 bottom-0 z-51 transition-transform duration-300 ease-out"
  class:translate-x-0={isVisible}
  class:-translate-x-full={!isVisible}
  style="width: {$sidebarStore.leftWidth}px;"
>
  <HoverWrapper
    bind:isVisible
    pinned={$sidebarStore.leftPinned}
    onVisibilityChange={handleVisibilityChange}
    hideDelay={500}
  >
    <div class="h-full flex flex-col border-r shadow-xl" style={sidebarStyle}>
      <!-- 标题栏 -->
      <div
        class="h-10 flex items-center justify-between px-3 border-b shrink-0"
      >
        <span class="text-sm font-medium">节点</span>
        <div class="flex items-center gap-1">
          <button
            class="p-1.5 rounded hover:bg-muted transition-colors {$sidebarStore.leftPinned
              ? 'bg-muted'
              : ''}"
            onclick={togglePin}
            title={$sidebarStore.leftPinned ? "取消固定" : "固定侧边栏"}
          >
            {#if $sidebarStore.leftPinned}
              <Pin class="w-4 h-4" />
            {:else}
              <PinOff class="w-4 h-4" />
            {/if}
          </button>
          <button
            class="p-1.5 rounded hover:bg-muted transition-colors"
            onclick={closeSidebar}
            title="关闭侧边栏"
          >
            <PanelLeftClose class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- 节点树面板 -->
      <div class="flex-1 min-h-0 overflow-hidden">
        <NodeTreePalette />
      </div>

      <!-- 底部工具栏 -->
      <div class="p-2 border-t flex items-center gap-2 bg-muted/20">
        <button
          class="flex-1 flex items-center justify-center gap-2 py-1.5 px-3 rounded-md bg-primary/10 hover:bg-primary/20 text-primary transition-colors text-xs font-medium border border-primary/20"
          onclick={() => flowStore.triggerLayout()}
          title="自动整理节点布局"
        >
          <LayoutTemplate class="w-3.5 h-3.5" />
          <span>整理布局</span>
        </button>
      </div>
    </div>

    <!-- 拖拽调整宽度把手 -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="absolute top-0 right-0 bottom-0 w-1 cursor-ew-resize hover:bg-primary/20 transition-colors group"
      onmousedown={handleResizeStart}
    >
      <div
        class="absolute top-1/2 right-0 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <GripVertical class="w-4 h-4 text-muted-foreground" />
      </div>
    </div>
  </HoverWrapper>
</div>
