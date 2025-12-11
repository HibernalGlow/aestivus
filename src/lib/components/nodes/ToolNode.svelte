<script lang="ts">
  import { Handle, Position } from '@xyflow/svelte';
  import {
    Package,
    Search,
    AlertTriangle,
    FolderSync,
    FileText,
    Video,
    Terminal,
    Circle,
    Loader2,
    CheckCircle2,
    XCircle
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data: {
      label: string;
      toolName?: string;
      config?: Record<string, unknown>;
      status?: 'idle' | 'running' | 'completed' | 'error';
      progress?: number;
    };
    type: string;
    selected?: boolean;
  }

  let { id, data, type, selected = false }: Props = $props();

  const toolIcons: Record<string, typeof Package> = {
    tool_repacku: Package,
    tool_samea: Search,
    tool_crashu: AlertTriangle,
    tool_migratef: FolderSync,
    tool_nameu: FileText,
    tool_formatv: Video
  };

  const statusIcons = {
    idle: Circle,
    running: Loader2,
    completed: CheckCircle2,
    error: XCircle
  };

  const statusColors = {
    idle: 'border-gray-300 bg-white',
    running: 'border-blue-500 bg-blue-50',
    completed: 'border-green-500 bg-green-50',
    error: 'border-red-500 bg-red-50'
  };

  const status = $derived(data.status || 'idle');
  const ToolIcon = $derived(toolIcons[type] || Terminal);
  const StatusIcon = $derived(statusIcons[status]);
  const toolName = $derived(data.toolName || type.replace('tool_', ''));
</script>

<div
  class="px-4 py-3 rounded-lg border-2 shadow-sm min-w-[160px] transition-all {statusColors[status]}"
  class:ring-2={selected}
  class:ring-blue-400={selected}
>
  <Handle type="target" position={Position.Left} class="!bg-gray-400 !w-3 !h-3" />

  <div class="flex items-center gap-2">
    <div class="p-1.5 rounded bg-blue-100">
      <ToolIcon class="w-4 h-4 text-blue-600" />
    </div>
    <span class="font-medium text-sm text-gray-800">{data.label}</span>
    <StatusIcon
      class="w-4 h-4 ml-auto {status === 'running' ? 'animate-spin text-blue-500' : status === 'completed' ? 'text-green-500' : status === 'error' ? 'text-red-500' : 'text-gray-400'}"
    />
  </div>

  <div class="text-xs text-gray-500 mt-1 flex items-center gap-1">
    <Terminal class="w-3 h-3" />
    {toolName}
  </div>

  {#if status === 'running' && data.progress !== undefined}
    <div class="mt-2 h-1.5 bg-gray-200 rounded-full overflow-hidden">
      <div
        class="h-full bg-blue-500 transition-all duration-300"
        style="width: {data.progress}%"
      ></div>
    </div>
  {/if}

  <Handle type="source" position={Position.Right} class="!bg-gray-400 !w-3 !h-3" />
</div>
