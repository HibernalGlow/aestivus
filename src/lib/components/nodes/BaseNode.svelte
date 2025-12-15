<script lang="ts">
  /**
   * BaseNode - 通用基础节点组件
   * 
   * 提供：路径输入、执行按钮、日志显示、配置插槽
   * 被 RawfilterNode、CrashuNode 等使用
   */
  import { Handle, Position } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { PathInput } from '$lib/components/input';
  import { Play, LoaderCircle } from '@lucide/svelte';
  import NodeWrapper from './NodeWrapper.svelte';
  
  // Props
  export let id: string;
  export let icon: string = '📦';
  export let displayName: string = '节点';
  export let status: 'idle' | 'running' | 'completed' | 'error' = 'idle';
  export let hasInputConnection: boolean = false;
  export let path: string = '';
  export let logs: string[] = [];
  export let onExecute: (() => Promise<void>) | null = null;
  
  // 计算按钮是否可用
  $: canExecute = status !== 'running' && (path.trim() !== '' || hasInputConnection);
  
  // 边框样式映射
  const statusStyles: Record<string, string> = {
    idle: 'border-border',
    running: 'border-primary shadow-sm',
    completed: 'border-primary/50',
    error: 'border-destructive/50'
  };
  
  // 执行处理
  async function handleExecute() {
    if (onExecute && canExecute) {
      await onExecute();
    }
  }
</script>

<div class="min-w-[240px] max-w-[300px]">
  <Handle type="target" position={Position.Left} class="bg-primary!" />
  
  <NodeWrapper
    nodeId={id}
    title={displayName}
    emoji={icon}
    {status}
    borderClass={statusStyles[status]}
  >
    {#snippet children()}
      <div class="p-4">
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
    {/snippet}
  </NodeWrapper>
  
  <Handle type="source" position={Position.Right} class="bg-primary!" />
</div>
