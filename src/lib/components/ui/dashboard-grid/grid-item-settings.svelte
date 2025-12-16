<script lang="ts">
  /**
   * GridItemSettings - 网格项布局设置按钮
   * 放在标题行中，点击弹出设置面板
   */
  import { getContext } from "svelte";
  import { Settings2 } from "@lucide/svelte";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import * as Popover from "$lib/components/ui/popover";

  interface Props {
    /** 网格项 ID */
    id: string;
    /** 当前 X 位置 */
    x: number;
    /** 当前 Y 位置 */
    y: number;
    /** 当前宽度 */
    w: number;
    /** 当前高度 */
    h: number;
    /** 最小宽度 */
    minW?: number;
    /** 最小高度 */
    minH?: number;
    /** 最大宽度 */
    maxW?: number;
    /** 最大高度 */
    maxH?: number;
  }

  let { id, x, y, w, h, minW, minH, maxW, maxH }: Props = $props();

  // 从 context 获取 grid 的 updateItem 方法
  const gridContext = getContext<{ updateItem: (id: string, x: number, y: number, w: number, h: number) => void }>('dashboard-grid');

  // 编辑状态
  let editX = $state(0);
  let editY = $state(0);
  let editW = $state(1);
  let editH = $state(1);
  let popoverOpen = $state(false);

  // 打开弹窗时同步当前值
  function openPopover() {
    editX = x;
    editY = y;
    editW = w;
    editH = h;
    popoverOpen = true;
  }

  // 应用更改
  function applyChanges() {
    gridContext?.updateItem(id, editX, editY, editW, editH);
    popoverOpen = false;
  }
</script>

<Popover.Root bind:open={popoverOpen}>
  <Popover.Trigger>
    {#snippet child({ props })}
      <button
        {...props}
        class="ml-auto p-1 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-all opacity-0 group-hover:opacity-100"
        title="设置布局"
        onclick={(e) => { e.stopPropagation(); openPopover(); }}
      >
        <Settings2 class="w-3.5 h-3.5" />
      </button>
    {/snippet}
  </Popover.Trigger>
  <Popover.Content class="w-48 p-2" align="end" side="bottom">
    <div class="space-y-2">
      <div class="text-xs font-semibold text-muted-foreground mb-2">布局</div>
      
      <div class="grid grid-cols-4 gap-1.5">
        <div class="flex flex-col">
          <span class="text-[10px] text-muted-foreground">X</span>
          <Input type="number" bind:value={editX} min={0} class="h-6 text-xs px-1" />
        </div>
        <div class="flex flex-col">
          <span class="text-[10px] text-muted-foreground">Y</span>
          <Input type="number" bind:value={editY} min={0} class="h-6 text-xs px-1" />
        </div>
        <div class="flex flex-col">
          <span class="text-[10px] text-muted-foreground">W</span>
          <Input type="number" bind:value={editW} min={minW ?? 1} max={maxW} class="h-6 text-xs px-1" />
        </div>
        <div class="flex flex-col">
          <span class="text-[10px] text-muted-foreground">H</span>
          <Input type="number" bind:value={editH} min={minH ?? 1} max={maxH} class="h-6 text-xs px-1" />
        </div>
      </div>
      
      <Button size="sm" class="w-full h-6 text-xs" onclick={applyChanges}>
        应用
      </Button>
    </div>
  </Popover.Content>
</Popover.Root>
