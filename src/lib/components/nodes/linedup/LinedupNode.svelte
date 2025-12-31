<script lang="ts">
  /**
   * LinedupNode - 行去重工具节点
   * 
   * 功能：过滤包含特定内容的行
   * 支持 diff 红绿显示和下载功能
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Textarea } from '$lib/components/ui/textarea';
  import { Label } from '$lib/components/ui/label';
  import * as Diff from 'diff';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { LINEDUP_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, saveNodeState } from '$lib/stores/nodeState.svelte';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    LoaderCircle, Filter, Clipboard,
    Copy, Check, RotateCcw, Zap, Download
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: Record<string, any>;
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'running' | 'completed' | 'error';

  interface LinedupState {
    sourceText: string;
    filterText: string;
  }

  interface DiffPart {
    value: string;
    added?: boolean;
    removed?: boolean;
  }

  const nodeId = $derived(id);
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 获取共享的响应式状态
  const ns = getNodeState<LinedupState>(id, {
    sourceText: '',
    filterText: ''
  });

  // 运行时状态（不需持久化）
  let keptLines = $state<string[]>([]);
  let removedLines = $state<string[]>([]);
  let diffParts = $state<DiffPart[]>([]);
  
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let copied = $state(false);
  let hasInputConnection = $state(false);
  let layoutRenderer = $state<any>(undefined);
  
  $effect(() => {
    logs = [...dataLogs];
    hasInputConnection = dataHasInputConnection;
  });

  let isRunning = $derived(phase === 'running');
  let sourceLines = $derived(ns.sourceText.split('\n').filter(s => s.trim()));
  let filterLines = $derived(ns.filterText.split('\n').filter(s => s.trim()));
  let canExecute = $derived(sourceLines.length > 0 && !isRunning);
  
  let borderClass = $derived({
    idle: 'border-border',
    running: 'border-primary shadow-sm',
    completed: 'border-green-500/50',
    error: 'border-destructive/50'
  }[phase]);

  function log(msg: string) { logs = [...logs.slice(-50), msg]; }

  async function pasteSource() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) ns.sourceText = text;
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

  async function pasteFilter() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) ns.filterText = text;
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

  // 执行过滤
  async function handleExecute() {
    if (!canExecute) return;
    
    phase = 'running';
    keptLines = [];
    removedLines = [];
    diffParts = [];
    log(`🔍 开始过滤，源: ${sourceLines.length} 行，过滤条件: ${filterLines.length} 行`);
    
    try {
      const response = await api.executeNode('linedup', {
        action: 'filter',
        source_lines: sourceLines,
        filter_lines: filterLines
      }) as any;
      
      if (response.logs) for (const m of response.logs) log(m);
      
      if (response.success) {
        phase = 'completed';
        keptLines = response.data?.filtered_lines ?? [];
        
        // 计算被移除的行
        const keptSet = new Set(keptLines.map(l => l.trim().toLowerCase()));
        removedLines = sourceLines.filter(l => !keptSet.has(l.trim().toLowerCase()));
        
        // 生成 diff
        const originalText = sourceLines.join('\n');
        const filteredText = keptLines.join('\n');
        diffParts = Diff.diffLines(originalText, filteredText);
        
        log(`✅ ${response.message}`);
      } else {
        phase = 'error';
        log(`❌ 过滤失败: ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      log(`❌ 过滤失败: ${error}`);
    }
  }

  function handleReset() {
    phase = 'idle';
    keptLines = [];
    removedLines = [];
    diffParts = [];
    logs = [];
  }

  async function copyKept() {
    if (keptLines.length === 0) return;
    try {
      await navigator.clipboard.writeText(keptLines.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
      log('✅ 保留内容已复制');
    } catch (e) { log(`❌ 复制失败: ${e}`); }
  }

  async function copyRemoved() {
    if (removedLines.length === 0) return;
    try {
      await navigator.clipboard.writeText(removedLines.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
      log('✅ 移除内容已复制');
    } catch (e) { log(`❌ 复制失败: ${e}`); }
  }

  // 下载文件
  function downloadFile(content: string, filename: string) {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    log(`✅ 已下载: ${filename}`);
  }

  function downloadKept() {
    if (keptLines.length === 0) return;
    downloadFile(keptLines.join('\n'), 'kept_lines.txt');
  }

  function downloadRemoved() {
    if (removedLines.length === 0) return;
    downloadFile(removedLines.join('\n'), 'removed_lines.txt');
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(logs.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }
</script>

{#snippet sourceBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between cq-mb shrink-0">
      <Label class="cq-text font-medium">源内容</Label>
      <Button variant="outline" size="icon" class="cq-button-icon" onclick={pasteSource} disabled={isRunning}>
        <Clipboard class="cq-icon" />
      </Button>
    </div>
    <Textarea 
      bind:value={ns.sourceText}
      placeholder="每行一个内容..."
      disabled={isRunning}
      class="flex-1 cq-input font-mono text-xs resize-none min-h-[80px]"
    />
    <span class="cq-text-sm text-muted-foreground mt-1">{sourceLines.length} 行</span>
  </div>
{/snippet}

{#snippet filterBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between cq-mb shrink-0">
      <Label class="cq-text font-medium">过滤条件</Label>
      <Button variant="outline" size="icon" class="cq-button-icon" onclick={pasteFilter} disabled={isRunning}>
        <Clipboard class="cq-icon" />
      </Button>
    </div>
    <Textarea 
      bind:value={ns.filterText}
      placeholder="每行一个过滤关键词...&#10;源行包含这些内容将被移除"
      disabled={isRunning}
      class="flex-1 cq-input font-mono text-xs resize-none min-h-[80px]"
    />
    <span class="cq-text-sm text-muted-foreground mt-1">{filterLines.length} 个条件</span>
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="p-2 rounded cq-text-sm bg-muted/50">
      <div class="text-muted-foreground">源: {sourceLines.length} 行</div>
      <div class="text-muted-foreground">过滤: {filterLines.length} 条件</div>
      {#if keptLines.length > 0 || removedLines.length > 0}
        <div class="text-green-600 mt-1">保留: {keptLines.length}</div>
        <div class="text-red-500">移除: {removedLines.length}</div>
      {/if}
    </div>
    
    <Button 
      class="w-full cq-button flex-1" 
      onclick={handleExecute}
      disabled={!canExecute}
    >
      {#if isRunning}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Zap class="cq-icon mr-1" />{/if}
      <span>过滤</span>
    </Button>
    
    <!-- 保留内容操作 -->
    <div class="flex cq-gap">
      <Button 
        variant="outline" 
        size="sm"
        class="flex-1 cq-button-sm" 
        onclick={copyKept}
        disabled={keptLines.length === 0}
      >
        <Copy class="w-3 h-3 mr-1" />保留
      </Button>
      <Button 
        variant="outline" 
        size="sm"
        class="flex-1 cq-button-sm" 
        onclick={downloadKept}
        disabled={keptLines.length === 0}
      >
        <Download class="w-3 h-3 mr-1" />下载
      </Button>
    </div>
    
    <!-- 移除内容操作 -->
    <div class="flex cq-gap">
      <Button 
        variant="outline" 
        size="sm"
        class="flex-1 cq-button-sm text-red-500 hover:text-red-600" 
        onclick={copyRemoved}
        disabled={removedLines.length === 0}
      >
        <Copy class="w-3 h-3 mr-1" />移除
      </Button>
      <Button 
        variant="outline" 
        size="sm"
        class="flex-1 cq-button-sm text-red-500 hover:text-red-600" 
        onclick={downloadRemoved}
        disabled={removedLines.length === 0}
      >
        <Download class="w-3 h-3 mr-1" />下载
      </Button>
    </div>
    
    <Button variant="ghost" class="w-full cq-button-sm" onclick={handleReset}>
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
  </div>
{/snippet}

{#snippet resultBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0">
      <span class="font-semibold cq-text">Diff 结果</span>
      {#if keptLines.length > 0 || removedLines.length > 0}
        <span class="cq-text-sm">
          <span class="text-green-600">+{keptLines.length}</span>
          <span class="text-muted-foreground mx-1">/</span>
          <span class="text-red-500">-{removedLines.length}</span>
        </span>
      {/if}
    </div>
    <div class="flex-1 overflow-y-auto cq-padding font-mono text-xs">
      {#if diffParts.length > 0}
        {#each diffParts as part}
          {#each part.value.split('\n').filter((_, i, arr) => i < arr.length - 1 || part.value.slice(-1) !== '\n') as line}
            <div class="py-0.5 px-1 rounded {part.removed ? 'bg-red-500/20 text-red-600 line-through' : part.added ? 'bg-green-500/20 text-green-600' : 'text-muted-foreground'}">
              <span class="inline-block w-4 text-center opacity-60">{part.removed ? '-' : part.added ? '+' : ' '}</span>
              {line || ' '}
            </div>
          {/each}
        {/each}
      {:else}
        <div class="text-center text-muted-foreground py-4">
          过滤后将显示 diff 对比<br/>
          <span class="text-green-600">绿色</span> = 保留，
          <span class="text-red-500">红色</span> = 移除
        </div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet logBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">日志</span>
      <Button variant="ghost" size="icon" class="h-5 w-5" onclick={copyLogs}>
        {#if copied}<Check class="w-3 h-3 text-green-500" />{:else}<Copy class="w-3 h-3" />{/if}
      </Button>
    </div>
    <div class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding font-mono cq-text-sm space-y-0.5">
      {#if logs.length > 0}
        {#each logs.slice(-15) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'source'}{@render sourceBlock()}
  {:else if blockId === 'filter'}{@render filterBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'result'}{@render resultBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 480px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={360} minHeight={300} maxWidth={480} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="linedup" 
    icon={Filter} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="linedup" 
    currentLayout={layoutRenderer?.getCurrentLayout()}
    currentTabGroups={layoutRenderer?.getCurrentTabGroups()}
    onApplyLayout={(layout, tabGroups) => layoutRenderer?.applyLayout(layout, tabGroups)}
    canCreateTab={true}
    onCreateTab={(blockIds) => layoutRenderer?.createTab(blockIds)}
    layoutMode={isFullscreenRender ? 'fullscreen' : 'normal'}
  >
    {#snippet children()}
      <NodeLayoutRenderer
        bind:this={layoutRenderer}
        nodeId={nodeId}
        nodeType="linedup"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={LINEDUP_DEFAULT_GRID_LAYOUT}
      >
        {#snippet renderBlock(blockId: string)}
          {@render renderBlockContent(blockId)}
        {/snippet}
      </NodeLayoutRenderer>
    {/snippet}
  </NodeWrapper>

  {#if !isFullscreenRender}
    <Handle type="source" position={Position.Right} class="bg-primary!" />
  {/if}
</div>
