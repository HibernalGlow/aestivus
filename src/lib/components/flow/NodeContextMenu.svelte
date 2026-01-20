<script lang="ts">
  import { onMount } from "svelte";
  import * as ContextMenu from "$lib/components/ui/context-menu";
  import { Trash2, Copy, Info } from "@lucide/svelte";

  interface Props {
    id: string;
    x: number;
    y: number;
    onClose: () => void;
    onDelete: (id: string) => void;
    onDuplicate: (id: string) => void;
  }

  let { id, x, y, onClose, onDelete, onDuplicate }: Props = $props();

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
        onDelete(id);
      }}
    >
      <Trash2 class="mr-2 h-4 w-4" />
      <span>删除节点</span>
    </ContextMenu.Item>

    <ContextMenu.Item
      onclick={() => {
        onDuplicate(id);
      }}
    >
      <Copy class="mr-2 h-4 w-4" />
      <span>复制节点</span>
    </ContextMenu.Item>

    <ContextMenu.Separator />

    <ContextMenu.Item onclick={onClose}>
      <Info class="mr-2 h-4 w-4" />
      <span>更多属性</span>
    </ContextMenu.Item>
  </ContextMenu.Content>
</ContextMenu.Root>
