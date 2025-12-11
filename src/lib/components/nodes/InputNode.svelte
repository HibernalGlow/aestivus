<script lang="ts">
  import { Handle, Position } from '@xyflow/svelte';
  import { Clipboard, Folder, FileInput } from '@lucide/svelte';

  interface Props {
    id: string;
    data: {
      label: string;
      config?: Record<string, unknown>;
      status?: 'idle' | 'running' | 'completed' | 'error';
    };
    type: string;
    selected?: boolean;
  }

  let { id, data, type, selected = false }: Props = $props();

  const icons: Record<string, typeof Clipboard> = {
    clipboard_input: Clipboard,
    folder_input: Folder,
    path_input: FileInput
  };

  const Icon = $derived(icons[type] || FileInput);

  const statusColors = {
    idle: 'border-green-300 bg-green-50',
    running: 'border-green-500 bg-green-100 animate-pulse',
    completed: 'border-green-600 bg-green-100',
    error: 'border-red-500 bg-red-50'
  };

  const status = $derived(data.status || 'idle');
</script>

<div
  class="px-4 py-3 rounded-lg border-2 shadow-sm min-w-[140px] transition-all {statusColors[status]}"
  class:ring-2={selected}
  class:ring-green-400={selected}
>
  <div class="flex items-center gap-2">
    <div class="p-1.5 rounded bg-green-200">
      <Icon class="w-4 h-4 text-green-700" />
    </div>
    <span class="font-medium text-sm text-gray-800">{data.label}</span>
  </div>

  {#if data.config?.path}
    <div class="mt-2 text-xs text-gray-500 truncate max-w-[160px]" title={String(data.config.path)}>
      {data.config.path}
    </div>
  {/if}

  <Handle type="source" position={Position.Right} class="!bg-green-500 !w-3 !h-3" />
</div>
