<script lang="ts">
  /**
   * KavvkaNode - Czkawka 辅助工具节点
   * 
   * 功能：处理图片文件夹，查找画师文件夹，移动文件到比较文件夹
   * 生成 Czkawka 路径字符串
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Textarea } from '$lib/components/ui/textarea';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Label } from '$lib/components/ui/label';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { KAVVKA_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, Image, FolderOpen, Clipboard,
    Copy, Check, RotateCcw, Zap
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

  interface KavvkaState {
    sourcePaths: string[];
    forceMove: boolean;
  }

  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<KavvkaState>(nodeId));
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 状态变量
  let sourcePaths = $state<string[]>([]);
  let sourcePathsText = $state('');
  let forceMove = $state(false);
  
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let copied = $state(false);
  let resultPaths = $state<string[]>([]);
  let hasInputConnection = $state(false);
  let layoutRenderer = $state<any>(undefined);

  let initialized = $state(false);
  
  $effect(() => {
    if (initialized) return;
    
    if (savedState) {
      sourcePaths = savedState.sourcePaths ?? [];
      forceMove = savedState.forceMove ?? false;
    }
    sourcePathsText = sourcePaths.join('\n');
    initialized = true;
  });
  
  $effect(() => {
    logs = [...dataLogs];
    hasInputConnection = dataHasInputConnection;
  });

  function saveState() {
    if (!initialized) return;
    setNodeState<KavvkaState>(nodeId, { sourcePaths, forceMove });
  }

  let isRunning = $derived(phase === 'running');
  let canExecute = $derived((sourcePaths.length > 0 || hasInputConnection) && !isRunning);
  let borderClass = $derived({
    idle: 'border-border',
    running: 'border-primary shadow-sm',
    completed: 'border-green-500/50',
    error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (forceMove !== undefined) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-50), msg]; }

  function updateSourcePaths(text: string) {
    sourcePathsText = text;
    sourcePaths = text.split('\n').map(s => s.trim()).filter(s => s);
  }

  async function selectSourceFolder() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog('选择源目录');
      if (selected) {
        sourcePaths = [...sourcePaths, selected];
        sourcePathsText = sourcePaths.join('\n');
      }
    } catch (e) { log(`选择文件夹失败: ${e}`); }
  }

  async function pasteSourcePaths() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) {
        const paths = text.split('\n').map(s => s.trim()).filter(s => s);
        sourcePaths = [...sourcePaths, ...paths];
        sourcePathsText = sourcePaths.join('\n');
      }
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

  // 执行处理
  async function handleExecute() {
    if (!canExecute) return;
    
    phase = 'running';
    resultPaths = [];
    log(`🚀 开始处理 ${sourcePaths.length} 个路径`);
    
    try {
      const response = await api.executeNode('kavvka', {
        action: 'process',
        paths: sourcePaths,
        force: forceMove
      }) as any;
      
      if (response.logs) for (const m of response.logs) log(m);
      
      if (response.success) {
        phase = 'completed';
        resultPaths = response.data?.all_combined_paths ?? [];
        log(`✅ ${response.message}`);
      } else {
        phase = 'error';
        log(`❌ 处理失败: ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      log(`❌ 处理失败: ${error}`);
    }
  }

  function handleReset() {
    phase = 'idle';
    resultPaths = [];
    logs = [];
  }

  async function copyResults() {
    if (resultPaths.length === 0) return;
    try {
      await navigator.clipboard.writeText(resultPaths.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
      log('✅ 路径已复制到剪贴板');
    } catch (e) { 
      console.error('复制失败:', e); 
      log(`❌ 复制失败: ${e}`);
    }
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
      <Label class="cq-text font-medium">源路径</Label>
      <div class="flex cq-gap">
        <Button variant="outline" size="icon" class="cq-button-icon" onclick={selectSourceFolder} disabled={isRunning}>
          <FolderOpen class="cq-icon" />
        </Button>
        <Button variant="outline" size="icon" class="cq-button-icon" onclick={pasteSourcePaths} disabled={isRunning}>
          <Clipboard class="cq-icon" />
        </Button>
      </div>
    </div>
    {#if hasInputConnection}
      <div class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-text">
        <span>←</span><span>输入来自上游节点</span>
      </div>
    {:else}
      <Textarea 
        value={sourcePathsText}
        oninput={(e) => updateSourcePaths(e.currentTarget.value)}
        placeholder="每行一个路径（画集文件夹）..."
        disabled={isRunning}
        class="flex-1 cq-input font-mono text-xs resize-none min-h-[60px]"
      />
      <span class="cq-text-sm text-muted-foreground mt-1">{sourcePaths.length} 个路径</span>
    {/if}
    
    <label class="flex items-center cq-gap cursor-pointer mt-2">
      <Checkbox bind:checked={forceMove} disabled={isRunning} />
      <span class="cq-text">强制移动（不询问确认）</span>
    </label>
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <Button 
      class="w-full cq-button flex-1" 
      onclick={handleExecute}
      disabled={!canExecute}
    >
      {#if isRunning}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Zap class="cq-icon mr-1" />{/if}
      <span>处理</span>
    </Button>
    
    <Button 
      variant="outline" 
      class="w-full cq-button flex-1" 
      onclick={copyResults}
      disabled={resultPaths.length === 0}
    >
      {#if copied}<Check class="cq-icon mr-1 text-green-500" />{:else}<Copy class="cq-icon mr-1" />{/if}
      <span>复制路径</span>
    </Button>
    
    <Button variant="ghost" class="w-full cq-button-sm" onclick={handleReset}>
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
  </div>
{/snippet}

{#snippet resultBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0">
      <span class="font-semibold cq-text">Czkawka 路径</span>
      {#if resultPaths.length > 0}
        <span class="cq-text-sm text-muted-foreground">{resultPaths.length} 组</span>
      {/if}
    </div>
    <div class="flex-1 overflow-y-auto cq-padding font-mono cq-text-sm">
      {#if resultPaths.length > 0}
        {#each resultPaths as pathStr, i}
          <div class="mb-2 p-2 bg-muted/30 rounded break-all">
            <span class="text-muted-foreground">{i + 1}.</span> {pathStr}
          </div>
        {/each}
      {:else}
        <div class="text-center text-muted-foreground py-4">处理后显示路径</div>
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
    title="kavvka" 
    icon={Image} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="kavvka" 
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
        nodeType="kavvka"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={KAVVKA_DEFAULT_GRID_LAYOUT}
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
