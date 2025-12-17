<script lang="ts">
  /**
   * NodeLayoutEditor - 节点布局编辑器
   * 在全屏模式下编辑节点模式的布局，使用限制大小的画布模拟节点尺寸
   */
  import type { GridItem } from './dashboard-grid.svelte';
  import { DashboardGrid, DashboardItem } from './index';
  import { getBlockDefinition, getNodeBlockLayout } from '$lib/components/blocks/blockRegistry';
  import { X, Save, RotateCcw } from '@lucide/svelte';

  interface Props {
    /** 节点类型 */
    nodeType: string;
    /** 当前节点模式布局 */
    currentLayout: GridItem[];
    /** 保存回调 */
    onSave: (layout: GridItem[]) => void;
    /** 取消回调 */
    onCancel: () => void;
  }

  let { nodeType, currentLayout, onSave, onCancel }: Props = $props();

  // 编辑中的布局（深拷贝）
  let editingLayout = $state<GridItem[]>(JSON.parse(JSON.stringify(currentLayout)));
  
  // DashboardGrid 引用
  let dashboardGrid = $state<{ compact: () => void; applyLayout: (layout: GridItem[]) => void } | undefined>(undefined);

  // 生成默认布局
  function generateDefaultLayout(): GridItem[] {
    const layout = getNodeBlockLayout(nodeType);
    if (!layout) return [];
    return layout.blocks
      .filter(b => b.visibleInNormal !== false && !b.isTabContainer)
      .map((b, idx) => ({
        id: b.id,
        x: idx % 2,
        y: Math.floor(idx / 2),
        w: b.colSpan ?? 1,
        h: 1,
        minW: 1,
        minH: 1
      }));
  }

  // 处理布局变化
  function handleLayoutChange(newLayout: GridItem[]) {
    editingLayout = newLayout;
  }

  // 重置为默认布局
  function handleReset() {
    const defaultLayout = generateDefaultLayout();
    editingLayout = defaultLayout;
    dashboardGrid?.applyLayout(defaultLayout);
  }

  // 整理布局
  function handleCompact() {
    dashboardGrid?.compact();
  }

  // 保存布局
  function handleSave() {
    onSave(editingLayout);
  }
</script>

<!-- 模态框遮罩 -->
<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
  <!-- 编辑器容器 -->
  <div class="bg-card border rounded-lg shadow-2xl w-[500px] max-h-[80vh] flex flex-col">
    <!-- 标题栏 -->
    <div class="flex items-center justify-between px-4 py-3 border-b">
      <h3 class="text-sm font-semibold">编辑节点布局</h3>
      <button
        class="p-1 rounded hover:bg-muted transition-colors text-muted-foreground"
        onclick={onCancel}
        title="取消"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- 工具栏 -->
    <div class="flex items-center gap-2 px-4 py-2 border-b bg-muted/30">
      <button
        class="px-2 py-1 text-xs rounded border border-border hover:bg-muted transition-colors flex items-center gap-1"
        onclick={handleReset}
        title="重置为默认布局"
      >
        <RotateCcw class="w-3 h-3" />
        重置
      </button>
      <button
        class="px-2 py-1 text-xs rounded border border-border hover:bg-muted transition-colors"
        onclick={handleCompact}
        title="整理布局"
      >
        整理
      </button>
      <div class="flex-1"></div>
      <button
        class="px-3 py-1 text-xs rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex items-center gap-1"
        onclick={handleSave}
      >
        <Save class="w-3 h-3" />
        保存
      </button>
    </div>

    <!-- 编辑区域（模拟节点大小，2列布局） -->
    <div class="flex-1 overflow-auto p-4">
      <div class="border-2 border-dashed border-primary/30 rounded-lg bg-muted/10" style="width: 100%; min-height: 400px;">
        <DashboardGrid
          bind:this={dashboardGrid}
          columns={2}
          cellHeight={60}
          margin={8}
          showToolbar={false}
          onLayoutChange={handleLayoutChange}
        >
          {#each editingLayout as item (item.id)}
            {@const blockDef = getBlockDefinition(nodeType, item.id)}
            <DashboardItem
              id={item.id}
              x={item.x}
              y={item.y}
              w={item.w}
              h={item.h}
              minW={item.minW ?? 1}
              minH={item.minH ?? 1}
            >
              <div class="h-full flex items-center justify-center bg-card border rounded-md p-2">
                {#if blockDef}
                  {@const Icon = blockDef.icon}
                  <div class="flex items-center gap-2 text-sm">
                    {#if Icon}
                      <svelte:component this={Icon} class="w-4 h-4 {blockDef.iconClass}" />
                    {/if}
                    <span class="truncate">{blockDef.title}</span>
                  </div>
                {:else}
                  <span class="text-xs text-muted-foreground">{item.id}</span>
                {/if}
              </div>
            </DashboardItem>
          {/each}
        </DashboardGrid>
      </div>
    </div>

    <!-- 提示 -->
    <div class="px-4 py-2 border-t text-xs text-muted-foreground">
      拖拽区块调整位置和大小，保存后将应用到节点模式
    </div>
  </div>
</div>
