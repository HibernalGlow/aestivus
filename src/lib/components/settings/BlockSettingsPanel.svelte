<script lang="ts">
  /**
   * 区块管理设置面板 - 重构版
   * 支持拖拽排序、显隐切换、持久化存储
   */
  import {
    LayoutGrid,
    Eye,
    EyeOff,
    Search,
    RotateCcw,
    GripVertical,
    Check,
  } from "@lucide/svelte";
  import * as icons from "@lucide/svelte";
  import { blockConfigStore } from "$lib/stores/blockConfig.svelte";
  import { nodeBlockRegistry } from "$lib/components/blocks/blockRegistry";
  import { getNodeDefinition } from "$lib/stores/nodeRegistry";
  import { AnimatedDropdown } from "$lib/components/ui/animated-dropdown";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { Badge } from "$lib/components/ui/badge";
  import * as Table from "$lib/components/ui/table";
  import * as Tooltip from "$lib/components/ui/tooltip";
  import { cn } from "$lib/utils";

  // 获取所有节点类型
  const nodeTypes = Object.keys(nodeBlockRegistry);

  // 下拉菜单项
  const dropdownItems = nodeTypes.map((type) => {
    const def = getNodeDefinition(type);
    const iconName = def?.icon || "LayoutGrid";
    // @ts-ignore - 动态获取图标
    const IconComponent = icons[iconName as keyof typeof icons] || LayoutGrid;

    return {
      id: type,
      name: def?.label || type,
      icon: IconComponent,
      badge: blockConfigStore.getNodeBlocks(type).length,
    };
  });

  let activeNode = $state<string>(nodeTypes[0] || "repacku");
  let searchQuery = $state("");
  let saveMessage = $state<string | null>(null);

  // 响应式获取当前节点的区块列表
  // 注意：blockConfigStore.getNodeBlocks 返回的是 snapshot，我们需要追踪 store 变化
  // 使用 $derived 来保持同步
  const currentBlocks = $derived.by(() => {
    // 触发依赖
    const _ = blockConfigStore.configs;
    return blockConfigStore.getNodeBlocks(activeNode);
  });

  const filteredBlocks = $derived.by(() => {
    const query = searchQuery.toLowerCase().trim();
    if (!query) return currentBlocks;

    return currentBlocks.filter(
      (b) =>
        b.title.toLowerCase().includes(query) ||
        b.id.toLowerCase().includes(query)
    );
  });

  // --- 拖拽逻辑 (复用 CardPanelManager 的 Pointer 实现) ---
  let dragId = $state<string | null>(null);
  let startY = $state(0);
  let currentDeltaY = $state(0);
  let dragIndex = $state(-1); // 在当前列表中的索引
  let dropTargetId = $state<string | null>(null);

  function handlePointerDown(
    event: PointerEvent,
    blockId: string,
    index: number
  ) {
    if (event.button !== 0) return; // 仅左键
    const target = event.target as HTMLElement;
    if (target.closest("button") || target.closest("a")) return;

    dragId = blockId;
    startY = event.clientY;
    currentDeltaY = 0;
    dragIndex = index;
    dropTargetId = null;

    const row = event.currentTarget as HTMLElement;
    row.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: PointerEvent) {
    if (!dragId) return;
    currentDeltaY = event.clientY - startY;

    // 查找鼠标下的行
    const element = document.elementFromPoint(event.clientX, event.clientY);
    const row = element?.closest("[data-drag-id]") as HTMLElement;

    if (row && row.dataset.dragId && row.dataset.dragId !== dragId) {
      dropTargetId = row.dataset.dragId;
    } else {
      dropTargetId = null;
    }
  }

  function handlePointerUp(event: PointerEvent) {
    if (!dragId) return;

    // 执行移动
    if (dropTargetId && dropTargetId !== dragId) {
      // 计算目标位置在完整列表中的索引（不仅仅是过滤后的）
      // 这里为了简单，我们要求拖拽时最好不要有过滤，或者小心处理索引
      // 但更安全的做法是基于 ID 查找
      const targetIndex = currentBlocks.findIndex((b) => b.id === dropTargetId);
      if (targetIndex !== -1) {
        blockConfigStore.moveBlock(activeNode, dragId, targetIndex);
      }
    }

    // 重置状态
    dragId = null;
    dropTargetId = null;
    currentDeltaY = 0;
    dragIndex = -1;

    const row = event.currentTarget as HTMLElement;
    if (row && row.releasePointerCapture) {
      row.releasePointerCapture(event.pointerId);
    }
  }

  // 重置当前节点
  function handleReset() {
    blockConfigStore.resetNode(activeNode);
    showSaveMessage("已重置");
  }

  function showSaveMessage(msg: string) {
    saveMessage = msg;
    setTimeout(() => (saveMessage = null), 2000);
  }

  function toggleVisibility(blockId: string, currentVisible: boolean) {
    blockConfigStore.setBlockVisible(activeNode, blockId, !currentVisible);
  }
</script>

<Tooltip.Provider>
  <div class="flex h-full flex-col gap-6 overflow-hidden p-1">
    <!-- 头部信息 -->
    <div class="flex flex-col gap-1.5 px-1">
      <h3 class="text-xl font-bold tracking-tight flex items-center gap-2">
        <LayoutGrid class="w-5 h-5" />
        区块管理
      </h3>
      <p class="text-muted-foreground text-sm">
        自定义各节点的区块显示顺序和可见性
      </p>
    </div>

    <!-- 工具栏 -->
    <div class="flex flex-wrap items-center justify-between gap-4 px-1">
      <div class="flex items-center gap-3 flex-1">
        <!-- 节点选择器 -->
        <div class="w-56 shrink-0">
          <AnimatedDropdown
            items={dropdownItems}
            bind:value={activeNode}
            placeholder="选择节点"
            triggerIcon={LayoutGrid}
          />
        </div>

        <!-- 搜索框 -->
        <div class="relative w-full max-w-xs">
          <Search
            class="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2"
          />
          <Input
            bind:value={searchQuery}
            placeholder="搜索区块..."
            class="h-10 rounded-xl pl-9"
          />
        </div>
      </div>

      <div class="flex items-center gap-2">
        {#if saveMessage}
          <span
            class="animate-in fade-in slide-in-from-right-2 text-xs font-medium text-green-600 flex items-center gap-1"
          >
            <Check class="w-3 h-3" />
            {saveMessage}
          </span>
        {/if}
        <Button
          variant="outline"
          size="sm"
          onclick={handleReset}
          class="h-10 gap-2 rounded-xl"
        >
          <RotateCcw class="h-4 w-4" />
          重置默认
        </Button>
      </div>
    </div>

    <!-- 表格区域 -->
    <div class="bg-card flex-1 overflow-auto rounded-2xl border shadow-sm">
      <Table.Root class="table-fixed">
        <Table.Header class="bg-muted/50 sticky top-0 z-10 backdrop-blur-md">
          <Table.Row>
            <Table.Head class="w-10 px-2"></Table.Head>
            <!-- 这个 Drag Handle -->
            <Table.Head class="w-12 px-0 text-center">图标</Table.Head>
            <Table.Head class="w-auto">名称</Table.Head>
            <Table.Head class="w-24 text-center">属性</Table.Head>
            <!-- 宽/高/可折叠 -->
            <Table.Head class="w-[100px] text-right pr-6">可见性</Table.Head>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {#each filteredBlocks as block, index (block.id)}
            <Table.Row
              onpointerdown={(e) => handlePointerDown(e, block.id, index)}
              onpointermove={handlePointerMove}
              onpointerup={handlePointerUp}
              onpointercancel={handlePointerUp}
              data-drag-id={block.id}
              class={cn(
                "group transition-all duration-200 select-none touch-none",
                dragId === block.id &&
                  "z-50 shadow-xl ring-2 ring-primary/50 bg-accent relative translate-y-0 opacity-90 scale-[1.02] pointer-events-none",
                dropTargetId === block.id &&
                  dragId !== block.id &&
                  "bg-primary/5 border-primary/20 scale-[0.98] blur-[0.5px]"
              )}
              style={dragId === block.id
                ? `transform: translateY(${currentDeltaY}px); z-index: 100; cursor: grabbing;`
                : ""}
            >
              <!-- 拖拽手柄 -->
              <Table.Cell class="px-2">
                <div
                  class="drag-handle text-muted-foreground/20 group-hover:text-muted-foreground/60 flex cursor-grab items-center justify-center p-1 transition-colors"
                >
                  <GripVertical class="h-4 w-4" />
                </div>
              </Table.Cell>

              <!-- 图标 -->
              <Table.Cell class="px-0">
                <div class="flex items-center justify-center">
                  <div
                    class="bg-muted group-hover:bg-primary group-hover:text-primary-foreground flex h-9 w-9 items-center justify-center rounded-xl shadow-sm transition-all duration-300"
                  >
                    {#if block.icon}
                      <svelte:component
                        this={block.icon}
                        class={cn(
                          "w-4.5 h-4.5",
                          block.iconClass || "text-muted-foreground",
                          "group-hover:text-primary-foreground"
                        )}
                      />
                    {:else}
                      <LayoutGrid
                        class={cn(
                          "w-4.5 h-4.5",
                          block.iconClass || "text-muted-foreground",
                          "group-hover:text-primary-foreground"
                        )}
                      />
                    {/if}
                  </div>
                </div>
              </Table.Cell>

              <!-- 名称 & ID -->
              <Table.Cell class="min-w-0 px-2">
                <div class="flex min-w-0 flex-col overflow-hidden">
                  <span class="block truncate font-medium" title={block.title}
                    >{block.title}</span
                  >
                  <span
                    class="text-muted-foreground block truncate font-mono text-[10px] uppercase opacity-50"
                    >{block.id}</span
                  >
                </div>
              </Table.Cell>

              <!-- 属性徽章 -->
              <Table.Cell class="text-center px-2">
                <div class="flex items-center justify-center gap-1.5 flex-wrap">
                  {#if block.colSpan === 2}
                    <Badge
                      variant="secondary"
                      class="text-[9px] px-1 h-5 min-w-[20px]">宽</Badge
                    >
                  {/if}
                  {#if block.canHide}
                    <Badge
                      variant="outline"
                      class="text-[9px] px-1 h-5 min-w-[20px] opacity-70"
                      >隐藏</Badge
                    >
                  {/if}
                </div>
              </Table.Cell>

              <!-- 操作（可见性） -->
              <Table.Cell class="text-right pr-4">
                <Tooltip.Root>
                  <Tooltip.Trigger asChild>
                    {#snippet children({ props })}
                      <Button
                        {...props}
                        variant="ghost"
                        size="icon"
                        class={cn(
                          "h-8 w-8 hover:bg-muted",
                          !block.visible && "text-muted-foreground opacity-50"
                        )}
                        onclick={() =>
                          toggleVisibility(block.id, block.visible)}
                      >
                        {#if block.visible}
                          <Eye class="w-4 h-4 text-primary" />
                        {:else}
                          <EyeOff class="w-4 h-4" />
                        {/if}
                      </Button>
                    {/snippet}
                  </Tooltip.Trigger>
                  <Tooltip.Content>
                    {block.visible ? "点击隐藏" : "点击显示"}
                  </Tooltip.Content>
                </Tooltip.Root>
              </Table.Cell>
            </Table.Row>
          {:else}
            <div
              class="flex flex-col items-center justify-center py-20 text-muted-foreground"
            >
              <LayoutGrid class="w-12 h-12 mb-4 opacity-10" />
              <p class="text-sm">未找到相关区块</p>
            </div>
          {/each}
        </Table.Body>
      </Table.Root>
    </div>

    <div
      class="flex items-center justify-between text-xs text-muted-foreground px-2"
    >
      <span>共 {currentBlocks.length} 个区块</span>
      <span>支持拖拽排序</span>
    </div>
  </div>
</Tooltip.Provider>
