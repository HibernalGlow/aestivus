<script lang="ts">
  /**
   * MagicCard - 鼠标跟随光效卡片组件
   * 基于主题色实现，支持根据卡片大小动态调整光晕尺寸
   */
  import { cn } from "$lib/utils";
  import type { Snippet } from "svelte";

  interface Props {
    /** 光晕基础大小，设为 0 则自动根据卡片大小计算 */
    gradientSize?: number;
    /** 光晕透明度 */
    gradientOpacity?: number;
    /** 是否禁用光效 */
    disabled?: boolean;
    class?: string;
    children?: Snippet;
  }

  let {
    gradientSize = 0,
    gradientOpacity = 0.5,
    disabled = false,
    class: className = "",
    children
  }: Props = $props();

  let containerRef = $state<HTMLDivElement | null>(null);
  let mouseX = $state(-200);
  let mouseY = $state(-200);

  // 动态计算光晕大小：取卡片宽高的较小值的 60%
  const dynamicSize = $derived(() => {
    if (gradientSize > 0) return gradientSize;
    if (!containerRef) return 150;
    const { width, height } = containerRef.getBoundingClientRect();
    return Math.min(width, height) * 0.6;
  });

  function handleMouseMove(e: MouseEvent) {
    if (disabled) return;
    const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
    mouseX = e.clientX - rect.left;
    mouseY = e.clientY - rect.top;
  }

  function handleMouseLeave() {
    const size = dynamicSize();
    mouseX = -size;
    mouseY = -size;
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  bind:this={containerRef}
  onmousemove={handleMouseMove}
  onmouseleave={handleMouseLeave}
  class={cn("group relative", className)}
>
  <!-- 内容区 -->
  <div class="relative z-10 w-full h-full">
    {#if children}
      {@render children()}
    {/if}
  </div>
  <!-- 光效层 -->
  {#if !disabled}
    <div
      class="magic-glow pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-300 group-hover:opacity-100"
      style="--glow-size: {dynamicSize()}px; --glow-x: {mouseX}px; --glow-y: {mouseY}px; --glow-opacity: {gradientOpacity};"
    ></div>
  {/if}
</div>

<style>
  .magic-glow {
    background: radial-gradient(
      var(--glow-size, 200px) circle at var(--glow-x, 0px) var(--glow-y, 0px),
      color-mix(in oklch, var(--color-primary) 40%, transparent),
      transparent 100%
    );
    opacity: var(--glow-opacity, 0.5);
  }
</style>
