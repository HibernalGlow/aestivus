<script lang="ts">
  /**
   * DockIcon - Dock 栏单个图标组件
   * 支持 macOS 风格的悬停放大动画
   */
  import { Motion, useSpring } from 'svelte-motion';
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

  // 图标大小配置
  const BASE_SIZE = 48;
  const MAX_SIZE = 72;
  const DISTANCE = 150;

  // 计算与鼠标的距离
  let distance = $state(DISTANCE);

  $effect(() => {
    if (!ref) return;
    
    // 使用 subscribe 方法订阅 MotionValue 变化
    const unsubscribe = mouseX.subscribe((latestX: number) => {
      const rect = ref.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      distance = Math.abs(latestX - centerX);
    });

    return unsubscribe;
  });

  // 基于距离计算大小
  let size = $derived.by(() => {
    if (distance > DISTANCE) return BASE_SIZE;
    const scale = 1 - (distance / DISTANCE);
    return BASE_SIZE + (MAX_SIZE - BASE_SIZE) * scale;
  });

  // 使用 spring 动画
  let springSize = useSpring(BASE_SIZE, { stiffness: 300, damping: 25 });
  
  $effect(() => {
    springSize.set(size);
  });

  // 获取图标组件
  let IconComponent = $derived((Icons as any)[icon] || Icons.Box);
</script>

<Motion let:motion>
  <div
    bind:this={ref}
    use:motion
    class="relative flex items-center justify-center cursor-pointer group"
    style="width: {$springSize}px; height: {$springSize}px;"
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
</Motion>
