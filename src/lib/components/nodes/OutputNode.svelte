<script lang="ts">
  import { Handle, Position } from '@xyflow/svelte';
  import { Terminal } from '@lucide/svelte';

  interface Props {
    id: string;
    data: {
      label: string;
      status?: 'idle' | 'running' | 'completed' | 'error';
    };
    type: string;
    selected?: boolean;
  }

  let { id, data, type, selected = false }: Props = $props();

  const statusColors = {
    idle: 'border-amber-300 bg-amber-50',
    running: 'border-amber-500 bg-amber-100 animate-pulse',
    completed: 'border-amber-600 bg-amber-100',
    error: 'border-red-500 bg-red-50'
  };

  const status = $derived(data.status || 'idle');
</script>

<div
  class="px-4 py-3 rounded-lg border-2 shadow-sm min-w-[140px] transition-all {statusColors[status]}"
  class:ring-2={selected}
  class:ring-amber-400={selected}
>
  <Handle type="target" position={Position.Left} class="!bg-amber-500 !w-3 !h-3" />

  <div class="flex items-center gap-2">
    <div class="p-1.5 rounded bg-amber-200">
      <Terminal class="w-4 h-4 text-amber-700" />
    </div>
    <span class="font-medium text-sm text-gray-800">{data.label}</span>
  </div>
</div>
