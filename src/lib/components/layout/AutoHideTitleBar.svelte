<script lang="ts">
  /**
   * 自动隐藏标题栏包装器
   * 支持悬停唤出、pin 固定、顶部触发区域
   */
  import type { Snippet } from "svelte";
  import HoverWrapper from "./HoverWrapper.svelte";
  import { settingsManager } from "$lib/settings/settingsManager";

  interface Props {
    children: Snippet;
    /** 初始是否固定 */
    initialPinned?: boolean;
    /** 隐藏延迟 (ms) */
    hideDelay?: number;
    /** 触发区域高度 (px) */
    triggerHeight?: number;
    /** pin 状态变化回调 */
    onPinnedChange?: (pinned: boolean) => void;
  }

  let {
    children,
    initialPinned = true,
    hideDelay = 500,
    triggerHeight = 8,
    onPinnedChange,
  }: Props = $props();

  // 从设置中读取 pin 状态
  let panelSettings = $state(settingsManager.getSettings().panels);
  let isPinned = $state(panelSettings.titleBarPinned ?? initialPinned);
  let isVisible = $state(isPinned);

  // 监听设置变化
  $effect(() => {
    const callback = (
      s: typeof panelSettings extends infer T ? { panels: T } : never,
    ) => {
      panelSettings = s.panels;
      if (s.panels.titleBarPinned !== undefined) {
        isPinned = s.panels.titleBarPinned;
        onPinnedChange?.(isPinned);
      }
    };
    settingsManager.addListener(callback as any);
    return () => settingsManager.removeListener(callback as any);
  });

  // 切换 pin 状态
  export function togglePin() {
    isPinned = !isPinned;
    settingsManager.updateNestedSettings("panels", {
      titleBarPinned: isPinned,
    });
    if (isPinned) {
      isVisible = true;
    }
    onPinnedChange?.(isPinned);
    // 取消固定时不立即隐藏，等鼠标移出后由 HoverWrapper 处理
  }

  // 获取 pin 状态
  export function getPinned() {
    return isPinned;
  }

  function handleVisibilityChange(visible: boolean) {
    isVisible = visible;
  }

  // 鼠标进入触发区域
  function handleTriggerEnter() {
    if (!isPinned) {
      isVisible = true;
    }
  }
</script>

<!-- 顶部触发区域（隐形条） -->
<div
  class="fixed top-0 left-0 right-0 z-[99]"
  style="height: {triggerHeight}px;"
  onmouseenter={handleTriggerEnter}
  role="presentation"
></div>

<!-- 标题栏容器 -->
<div
  class="fixed top-0 left-0 right-0 w-full z-[100] transition-transform duration-300 ease-out"
  class:translate-y-0={isVisible}
  class:-translate-y-full={!isVisible}
>
  <HoverWrapper
    bind:isVisible
    pinned={isPinned}
    onVisibilityChange={handleVisibilityChange}
    {hideDelay}
  >
    <div class="w-full">
      {@render children?.()}
    </div>
  </HoverWrapper>
</div>

<!-- 占位符：pin 时保持布局空间 -->
{#if isPinned}
  <div class="h-10 shrink-0"></div>
{/if}
