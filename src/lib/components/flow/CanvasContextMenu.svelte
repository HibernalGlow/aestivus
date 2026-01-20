<script lang="ts">
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu";
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

<DropdownMenu.Root bind:open>
  <div
    style="position: fixed; left: {x}px; top: {y}px; width: 1px; height: 1px; opacity: 0; pointer-events: none;"
    aria-hidden="true"
  >
    <DropdownMenu.Trigger />
  </div>
  <DropdownMenu.Content class="w-48 z-1000" align="start">
    <DropdownMenu.Item
      onclick={() => {
        onAutoLayout();
        onClose();
      }}
    >
      <Layout class="mr-2 h-4 w-4" />
      <span>自动布局</span>
    </DropdownMenu.Item>

    <DropdownMenu.Separator />

    <DropdownMenu.Item disabled>
      <Plus class="mr-2 h-4 w-4" />
      <span>添加节点 (待选)</span>
    </DropdownMenu.Item>

    <DropdownMenu.Item disabled>
      <Play class="mr-2 h-4 w-4" />
      <span>运行全部</span>
    </DropdownMenu.Item>
  </DropdownMenu.Content>
</DropdownMenu.Root>
