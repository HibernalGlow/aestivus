<script lang="ts">
  import * as ContextMenu from "$lib/components/ui/context-menu";
  import { Layout, Plus, Play } from "@lucide/svelte";

  interface Props {
    x: number;
    y: number;
    onClose: () => void;
    onAutoLayout: () => void;
  }

  let { x, y, onClose, onAutoLayout }: Props = $props();
  let open = $state(true);

  $effect(() => {
    if (!open) {
      onClose();
    }
  });
</script>

<ContextMenu.Root bind:open>
  <div
    style="position: absolute; left: {x}px; top: {y}px; width: 1px; height: 1px; opacity: 0; pointer-events: none;"
    aria-hidden="true"
  >
    <ContextMenu.Trigger />
  </div>
  <ContextMenu.Content class="w-48 z-1000">
    <ContextMenu.Item
      onclick={() => {
        onAutoLayout();
        onClose();
      }}
    >
      <Layout class="mr-2 h-4 w-4" />
      <span>自动布局</span>
    </ContextMenu.Item>

    <ContextMenu.Separator />

    <ContextMenu.Item disabled>
      <Plus class="mr-2 h-4 w-4" />
      <span>添加节点 (待选)</span>
    </ContextMenu.Item>

    <ContextMenu.Item disabled>
      <Play class="mr-2 h-4 w-4" />
      <span>运行全部</span>
    </ContextMenu.Item>
  </ContextMenu.Content>
</ContextMenu.Root>
