<script lang="ts">
  import { Handle, Position } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Badge } from '$lib/components/ui/badge';
  import { PathInput } from '$lib/components/input';
  import { Play, LoaderCircle, ChevronDown, ChevronRight, X, Pin, PinOff } from '@lucide/svelte';
  import { flowStore } from '$lib/stores';
  
  // Props
  export let id: string;
  export let icon: string = '📦';
  export let displayName: string = '节点';
  export let status: 'idle' | 'running' | 'completed' | 'error' = 'idle';
  export let hasInputConnection: boolean = false;
  export let path: string = '';
  export let logs: string[] = [];
  export let onExecute: (() => Promise<void>) | null = null;
  
  // 节点控制状态
  let collapsed = false;
  let pinned = false;
  
  function handleClose() { flowStore.removeNode(id); }
  function toggleCollapse() { collapsed = !collapsed; }
  function togglePin() { 
    pinned = !pinned; 
    flowStore.updateNode(id, { draggable: !pinned });
  }
  
  // 计算按钮是否可用
  $: canExecute = status !== 'running' && (path.trim() !== '' || hasInputConnection);
  
  // 状态样式映射
  const statusStyles: Record<string, string> = {
    idle: 'border-border',
    running: 'border-blue-500 shadow-blue-500/20 shadow-lg animate-pulse',
    completed: 'border-green-500',
    error: 'border-red-500'
  };
  
  const statusLabels: Record<string, string> = {
    idle: '就绪',
    running: '运行中',
    completed: '完成',
    error: '错误'
  };
  
  const statusVariants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
    idle: 'secondary',
    running: 'default',
    completed: 'default',
    error: 'destructive'
  };
  
  // 执行处理
  async function handleExecute() {
    if (onExecute && canExecute) {
      await onExecute();
    }
  }

  // 忽略未使用的 id 警告
  void id;
</script>

<div class="rounded-lg border-2 bg-card min-w-[300px] {statusStyles[status]}">
  <!-- 输入端口 -->
  <Handle type="target" position={Position.Left} class="bg-primary!" />
  
  <!-- 标题栏 -->
  <div class="flex items-center justify-between px-3 py-2 border-b bg-muted/30">
    <div class="flex items-center gap-2">
      <button class="p-0.5 rounded hover:bg-muted" onclick={toggleCollapse} title={collapsed ? '展开' : '折叠'}>
        {#if collapsed}<ChevronRight class="w-4 h-4" />{:else}<ChevronDown class="w-4 h-4" />{/if}
      </button>
      <span class="text-lg">{icon}</span>
      <span class="font-semibold">{displayName}</span>
      <Badge variant={statusVariants[status]} class="text-xs">
        {statusLabels[status]}
      </Badge>
    </div>
    <div class="flex items-center gap-0.5">
      <button class="p-1 rounded hover:bg-muted {pinned ? 'text-primary' : 'text-muted-foreground'}" onclick={togglePin} title={pinned ? '取消固定' : '固定'}>
        {#if pinned}<Pin class="w-3.5 h-3.5" />{:else}<PinOff class="w-3.5 h-3.5" />{/if}
      </button>
      <button class="p-1 rounded hover:bg-destructive hover:text-destructive-foreground text-muted-foreground" onclick={handleClose} title="关闭">
        <X class="w-3.5 h-3.5" />
      </button>
    </div>
  </div>
  
  <!-- 内容区（折叠时隐藏） -->
  {#if !collapsed}
  <div class="p-4 nodrag">
    <!-- 输入区域 -->
    {#if !hasInputConnection}
      <div class="mb-3">
        <PathInput bind:value={path} disabled={status === 'running'} />
      </div>
    {:else}
      <div class="text-sm text-muted-foreground mb-3 p-2 bg-muted rounded flex items-center gap-2">
        <span>←</span>
        <span>输入来自上游节点</span>
      </div>
    {/if}
    
    <!-- 工具特定配置插槽 -->
    <slot name="config" />
    
    <!-- 执行按钮 -->
    <Button 
      class="w-full mt-3" 
      onclick={handleExecute}
      disabled={!canExecute}
    >
      {#if status === 'running'}
        <LoaderCircle class="h-4 w-4 mr-2 animate-spin" />
        执行中...
      {:else}
        <Play class="h-4 w-4 mr-2" />
        执行
      {/if}
    </Button>
    
    <!-- 日志输出 -->
    {#if logs.length > 0}
      <div class="mt-3 p-2 bg-muted rounded text-xs font-mono max-h-32 overflow-y-auto">
        {#each logs.slice(-5) as log}
          <div class="text-muted-foreground truncate">{log}</div>
        {/each}
      </div>
    {/if}
  </div>
  {/if}
  
  <!-- 输出端口 -->
  <Handle type="source" position={Position.Right} class="bg-primary!" />
</div>
