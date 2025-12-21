<script lang="ts">
  /**
   * 动画下拉菜单组件
   * 带有平滑动画效果的下拉选择器
   */
  import { Motion, useAnimation } from "svelte-motion";
  import { ChevronRight, Settings } from "@lucide/svelte";
  import { cn } from "$lib/utils";
  import type { Component } from "svelte";

  // Props
  interface DropdownItem {
    id: string;
    name: string;
    icon?: Component;
    badge?: string | number;
    customStyle?: string;
  }

  interface Props {
    items: DropdownItem[];
    value?: string;
    placeholder?: string;
    triggerIcon?: Component;
    class?: string;
    onSelect?: (item: DropdownItem) => void;
  }

  let { 
    items = [], 
    value = $bindable(), 
    placeholder = "选择...",
    triggerIcon: TriggerIcon = Settings,
    class: className = "",
    onSelect
  }: Props = $props();

  let svgControls = useAnimation();
  let isOpen = $state(false);

  // 当前选中项
  let selectedItem = $derived(items.find(item => item.id === value));

  // 动画配置 - 列表容器
  let listVariants = {
    visible: {
      clipPath: "inset(0% 0% 0% 0% round 12px)",
      transition: {
        type: "spring",
        bounce: 0,
      },
    },
    hidden: {
      clipPath: "inset(10% 50% 90% 50% round 12px)",
      transition: {
        duration: 0.3,
        type: "spring",
        bounce: 0,
      },
    },
  };

  // 动画配置 - 列表项
  let itemVariants = {
    visible: (i: number) => ({
      opacity: 1,
      scale: 1,
      filter: "blur(0px)",
      transition: {
        duration: 0.3,
        delay: i * 0.05,
      },
    }),
    hidden: {
      opacity: 0,
      scale: 0.3,
      filter: "blur(20px)",
    },
  };

  function handleSelect(item: DropdownItem) {
    value = item.id;
    isOpen = false;
    onSelect?.(item);
  }

  function handleClickOutside(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest('.animated-dropdown')) {
      isOpen = false;
    }
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div class={cn("animated-dropdown relative w-full", className)}>
  <Motion
    whileTap={{ scale: 0.97 }}
    let:motion
  >
    <button
      use:motion
      onclick={() => (isOpen = !isOpen)}
      type="button"
      class="bg-card border border-border w-full flex items-center justify-between p-2.5 rounded-xl outline-none hover:border-primary/50 transition-colors"
    >
      <span class="text-sm font-medium text-foreground truncate">
        {selectedItem?.name || placeholder}
      </span>
      <div class="flex items-center gap-2">
        {#if selectedItem?.badge}
          <span class="text-xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
            {selectedItem.badge}
          </span>
        {/if}
        <Motion animate={svgControls} let:motion>
          <div use:motion class="text-muted-foreground">
            <TriggerIcon class="w-4 h-4" />
          </div>
        </Motion>
      </div>
    </button>
  </Motion>

  <Motion
    animate={isOpen ? "visible" : "hidden"}
    variants={listVariants}
    initial="hidden"
    let:motion
  >
    <ul
      use:motion
      class={cn(
        "absolute z-50 mt-2 w-full space-y-1 p-2 bg-card border border-border rounded-xl shadow-lg max-h-64 overflow-y-auto",
        isOpen ? "pointer-events-auto" : "pointer-events-none"
      )}
    >
      {#each items as item, i}
        {@const ItemIcon = item.icon}
        <Motion
          custom={i + 1}
          variants={itemVariants}
          initial="hidden"
          animate={isOpen ? "visible" : "hidden"}
          let:motion
        >
          <li use:motion>
            <button
              type="button"
              onclick={() => handleSelect(item)}
              class={cn(
                "group w-full flex items-center justify-between gap-2 p-2 rounded-lg border border-transparent",
                "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                "focus-visible:text-foreground focus-visible:border-border focus-visible:outline-none",
                "transition-colors",
                value === item.id && "bg-muted/50 text-foreground",
                item.customStyle
              )}
            >
              <div class="flex items-center gap-2 min-w-0">
                {#if ItemIcon}
                  <ItemIcon class="w-4 h-4 shrink-0" />
                {/if}
                <span class="text-sm font-medium truncate">{item.name}</span>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                {#if item.badge}
                  <span class="text-xs bg-muted px-1.5 py-0.5 rounded">
                    {item.badge}
                  </span>
                {/if}
                <ChevronRight
                  class="w-3 h-3 -translate-x-1 scale-0 opacity-0 group-hover:opacity-100 group-hover:scale-100 group-hover:translate-x-0 transition-all"
                />
              </div>
            </button>
          </li>
        </Motion>
      {/each}
    </ul>
  </Motion>
</div>
