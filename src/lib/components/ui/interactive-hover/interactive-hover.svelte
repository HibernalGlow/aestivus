<script lang="ts">
  /**
   * InteractiveHover - 交互式悬停按钮
   * 特性：圆形扩展背景 + 文字滑动切换 + 箭头图标
   * 使用 group/btn 命名避免与父级 group 冲突
   */
  import { cn } from "$lib/utils";
  import { ArrowRight } from "@lucide/svelte";
  import type { Snippet } from "svelte";
  import type { HTMLButtonAttributes } from "svelte/elements";

  interface Props extends HTMLButtonAttributes {
    /** 按钮文字 */
    text?: string;
    /** 自定义类名 */
    class?: string;
    /** 自定义图标插槽 */
    icon?: Snippet;
  }

  let { 
    text = "Button", 
    class: className = "",
    icon,
    ...restProps 
  }: Props = $props();
</script>

<button
  class={cn(
    "group/btn relative w-32 cursor-pointer overflow-hidden rounded-full border bg-background p-2 text-center font-semibold",
    className
  )}
  {...restProps}
>
  <!-- 默认状态文字 -->
  <span
    class="inline-block translate-x-1 transition-all duration-300 group-hover/btn:translate-x-12 group-hover/btn:opacity-0"
  >
    {text}
  </span>
  
  <!-- 悬停状态内容 -->
  <div
    class="absolute top-0 z-10 flex h-full w-full translate-x-12 items-center justify-center gap-2 text-primary-foreground opacity-0 transition-all duration-300 group-hover/btn:-translate-x-1 group-hover/btn:opacity-100"
  >
    <span>{text}</span>
    {#if icon}
      {@render icon()}
    {:else}
      <ArrowRight class="h-4 w-4" />
    {/if}
  </div>
  
  <!-- 扩展背景圆 -->
  <div
    class="absolute left-[20%] top-[40%] h-2 w-2 scale-[1] rounded-full bg-primary transition-all duration-300 group-hover/btn:left-[0%] group-hover/btn:top-[0%] group-hover/btn:h-full group-hover/btn:w-full group-hover/btn:scale-[1.8] group-hover/btn:bg-primary"
  ></div>
</button>
