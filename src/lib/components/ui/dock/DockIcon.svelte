<script lang="ts">
  /**
   * DockIcon - Dock 栏单个图标组件
   * 支持 macOS 风格的悬停放大动画
   */
  import type { MotionValue } from 'svelte-motion';
  import * as Icons from '@lucide/svelte';

  interface Props {
    icon: string;
    label: string;
    isActive?: boolean;
    mouseX: MotionValue<number>;
    onclick?: () => void;
    oncontextmenu?: (e: MouseEvent) => void;
  }

  let { 
    icon, 
    label, 
    isActive = false, 
    mouseX,
    onclick,
    oncontextmenu
  }: Props = $props();

  let ref: HTMLDivElement;

  // 图标大小配置（缩小尺寸）
  const BASE_SIZE = 36;
  const MAX_SIZE = 48;
  const DISTANCE = 100;

  // 计算与鼠标的距离，初始设为无穷大确保显示基础尺寸
  let distance = $state(Infinity);

  $effect(() => {
    if (!ref) return;
    
    // 使用 subscribe 方法订阅 MotionValue 变化
    const unsubscribe = mouseX.subscribe((latestX: number) => {
      if (!isFinite(latestX)) {
        distance = Infinity;
        return;
      }
      const rect = ref.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      distance = Math.abs(latestX - centerX);
    });

    return unsubscribe;
  });

  // 基于距离计算大小
  let size = $derived.by(() => {
    if (!isFinite(distance) || distance > DISTANCE) return BASE_SIZE;
    const scale = 1 - (distance / DISTANCE);
    return BASE_SIZE + (MAX_SIZE - BASE_SIZE) * scale;
  });

  // 直接使用计算的尺寸，不用 spring 避免初始化问题
  let displaySize = $derived(size);

  // 获取图标组件
  let IconComponent = $derived((Icons as any)[icon] || Icons.Box);
</script>

<div
  bind:this={ref}
  class="relative flex items-center justify-center cursor-pointer group"
  style="width: {displaySize}px; height: {displaySize}px; transition: width 0.15s, height 0.15s;"
    onclick={onclick}
    oncontextmenu={oncontextmenu}
    role="button"
    tabindex="0"
    onkeydown={(e) => e.key === 'Enter' && onclick?.()}
  >
    <!-- 图标背景 -->
    <div 
      class="absolute inset-0 rounded-xl transition-colors duration-200
        {isActive 
          ? 'bg-primary/20 ring-2 ring-primary/50' 
          : 'bg-card/80 hover:bg-card group-hover:ring-1 group-hover:ring-border'}"
      style="backdrop-filter: blur(12px);"
    ></div>
    
    <!-- 图标 -->
    <div class="relative z-10 flex items-center justify-center" style="width: 60%; height: 60%;">
      <IconComponent class="w-full h-full {isActive ? 'text-primary' : 'text-foreground'}" />
    </div>

    <!-- 激活指示器 -->
    {#if isActive}
      <div class="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-primary"></div>
    {/if}

    <!-- Tooltip -->
    <div 
      class="absolute -top-10 left-1/2 -translate-x-1/2 px-2 py-1 rounded-md 
        bg-popover text-popover-foreground text-xs whitespace-nowrap
        opacity-0 group-hover:opacity-100 transition-opacity duration-200
        pointer-events-none shadow-lg border"
    >
      {label}
    </div>
  </div>
