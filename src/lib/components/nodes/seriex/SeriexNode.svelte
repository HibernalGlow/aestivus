<script lang="ts">
  /**
   * SeriexNode - 漫画压缩包系列提取节点
   * 
   * 功能：自动识别并整理同一系列的漫画压缩包
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Slider } from '$lib/components/ui/slider';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { SERIEX_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    BookOpen, FolderSearch, Play, RotateCcw, Copy, Check,
    FolderOpen, ChevronDown, ChevronRight, Loader2
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: Record<string, any>;
      status?: 'idle' | 'running' | 'completed' | 'error';
      logs?: string[];
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'planning' | 'planned' | 'executing' | 'completed' | 'error';

  interface SeriexState {
    directoryPath: string;
    threshold: number;
    ratioThreshold: number;
    partialThreshold: number;
    tokenThreshold: number;
    lengthDiffMax: number;
    addPrefix: boolean;
    prefix: string;
    knownSeriesDirs: string;
  }

  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<SeriexState>(nodeId));
  const dataLogs = $derived(data?.logs ?? []);

  // 状态变量
  let directoryPath = $state('');
  let threshold = $state(75);
  let ratioThreshold = $state(75);
  let partialThreshold = $state(85);
  let tokenThreshold = $state(80);
  let lengthDiffMax = $state(0.3);
  let addPrefix = $state(true);
  let prefix = $state('[#s]');
  let knownSeriesDirs = $state('');
  
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let copied = $state(false);
  let layoutRenderer = $state<any>(undefined);
  
  // 计划结果
  let plan = $state<Record<string, Record<string, string[]>>>({});
  let totalSeries = $state(0);
  let totalFiles = $state(0);
  
  // 展开状态
  let expandedDirs = $state<Set<string>>(new Set());

  let initialized = $state(false);
  
  $effect(() => {
    if (initialized) return;
    
    if (savedState) {
      directoryPath = savedState.directoryPath ?? '';
      threshold = savedState.threshold ?? 75;
      ratioThreshold = savedState.ratioThreshold ?? 75;
      partialThreshold = savedState.partialThreshold ?? 85;
      tokenThreshold = savedState.tokenThreshold ?? 80;
      lengthDiffMax = savedState.lengthDiffMax ?? 0.3;
      addPrefix = savedState.addPrefix ?? true;
      prefix = savedState.prefix ?? '[#s]';
      knownSeriesDirs = savedState.knownSeriesDirs ?? '';
    }
    initialized = true;
  });
  
  $effect(() => { logs = [...dataLogs]; });

  function saveState() {
    if (!initialized) return;
    setNodeState<SeriexState>(nodeId, { 
      directoryPath, threshold, ratioThreshold, partialThreshold,
      tokenThreshold, lengthDiffMax, addPrefix, prefix, knownSeriesDirs
    });
  }

  // 派生状态
  let isPlanning = $derived(phase === 'planning');
  let isExecuting = $derived(phase === 'executing');
  let hasPlan = $derived(Object.keys(plan).length > 0);
  
  let borderClass = $derived({
    idle: 'border-border',
    planning: 'border-primary shadow-sm',
    planned: 'border-blue-500/50',
    executing: 'border-orange-500/50',
    completed: 'border-green-500/50',
    error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (directoryPath || threshold) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-100), msg]; }

  // 生成计划
  async function handlePlan() {
    if (!directoryPath) {
      log('❌ 请输入目录路径');
      return;
    }
    
    phase = 'planning';
    plan = {};
    log(`📂 开始扫描: ${directoryPath}`);
    
    try {
      const response = await api.executeNode('seriex', {
        action: 'plan',
        directory_path: directoryPath,
        threshold,
        ratio_threshold: ratioThreshold,
        partial_threshold: partialThreshold,
        token_threshold: tokenThreshold,
        length_diff_max: lengthDiffMax,
        add_prefix: addPrefix,
        prefix,
        known_series_dirs: knownSeriesDirs.split('\n').filter(s => s.trim())
      }) as any;
      
      if (response.logs) for (const m of response.logs) log(m);
      
      if (response.success) {
        phase = 'planned';
        plan = response.data?.plan ?? {};
        totalSeries = response.data?.total_series ?? 0;
        totalFiles = response.data?.total_files ?? 0;
        
        // 默认展开所有目录
        expandedDirs = new Set(Object.keys(plan));
        
        log(`✅ ${response.message}`);
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      log(`❌ 扫描失败: ${error}`);
    }
  }

  // 执行计划
  async function handleExecute() {
    if (!hasPlan) {
      log('❌ 没有可执行的计划');
      return;
    }
    
    phase = 'executing';
    log(`🚀 开始执行移动...`);
    
    try {
      const response = await api.executeNode('seriex', {
        action: 'apply',
        directory_path: directoryPath,
        threshold,
        ratio_threshold: ratioThreshold,
        partial_threshold: partialThreshold,
        token_threshold: tokenThreshold,
        length_diff_max: lengthDiffMax,
        add_prefix: addPrefix,
        prefix,
        known_series_dirs: knownSeriesDirs.split('\n').filter(s => s.trim())
      }) as any;
      
      if (response.logs) for (const m of response.logs) log(m);
      
      if (response.success) {
        phase = 'completed';
        totalSeries = response.data?.total_series ?? 0;
        totalFiles = response.data?.total_files ?? 0;
        plan = {}; // 清空计划
        log(`✅ ${response.message}`);
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      log(`❌ 执行失败: ${error}`);
    }
  }

  function toggleDir(dirPath: string) {
    const newSet = new Set(expandedDirs);
    if (newSet.has(dirPath)) {
      newSet.delete(dirPath);
    } else {
      newSet.add(dirPath);
    }
    expandedDirs = newSet;
  }

  function handleReset() {
    phase = 'idle';
    plan = {};
    expandedDirs = new Set();
    logs = [];
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(logs.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  // 打开文件夹
  async function openFolder(path: string) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('open_path', { path });
      log(`📂 已打开: ${path}`);
    } catch (e) {
      log(`❌ 打开失败: ${e}`);
    }
  }
</script>

{#snippet configBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex flex-col cq-gap">
      <Label class="cq-text font-medium">目录路径</Label>
      <Input 
        bind:value={directoryPath}
        placeholder="要处理的目录路径"
        disabled={isPlanning || isExecuting}
        class="cq-input font-mono text-xs"
      />
    </div>
    
    <div class="flex flex-col cq-gap">
      <Label class="cq-text font-medium">系列前缀</Label>
      <Input 
        bind:value={prefix}
        placeholder="[#s]"
        disabled={isPlanning || isExecuting}
        class="cq-input font-mono text-xs"
      />
    </div>
    
    <div class="flex items-center cq-gap">
      <Checkbox 
        id="addPrefix"
        bind:checked={addPrefix}
        disabled={isPlanning || isExecuting}
      />
      <Label for="addPrefix" class="cq-text-sm">添加系列前缀</Label>
    </div>
    
    <div class="flex flex-col cq-gap">
      <Label class="cq-text font-medium">已知系列目录（每行一个）</Label>
      <textarea 
        bind:value={knownSeriesDirs}
        placeholder="已知系列库目录..."
        disabled={isPlanning || isExecuting}
        class="flex-1 cq-input font-mono text-xs resize-none min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2"
      ></textarea>
    </div>
  </div>
{/snippet}

{#snippet similarityBlock()}
  <div class="flex flex-col cq-gap h-full overflow-y-auto">
    <div class="flex flex-col cq-gap">
      <div class="flex justify-between">
        <Label class="cq-text-sm">基本相似度</Label>
        <span class="cq-text-sm text-muted-foreground">{threshold}%</span>
      </div>
      <Slider 
        type="single"
        value={threshold} 
        onValueChange={(v: number) => threshold = v}
        min={0} max={100} step={1}
        disabled={isPlanning || isExecuting}
      />
    </div>
    
    <div class="flex flex-col cq-gap">
      <div class="flex justify-between">
        <Label class="cq-text-sm">完全匹配</Label>
        <span class="cq-text-sm text-muted-foreground">{ratioThreshold}%</span>
      </div>
      <Slider 
        type="single"
        value={ratioThreshold} 
        onValueChange={(v: number) => ratioThreshold = v}
        min={0} max={100} step={1}
        disabled={isPlanning || isExecuting}
      />
    </div>
    
    <div class="flex flex-col cq-gap">
      <div class="flex justify-between">
        <Label class="cq-text-sm">部分匹配</Label>
        <span class="cq-text-sm text-muted-foreground">{partialThreshold}%</span>
      </div>
      <Slider 
        type="single"
        value={partialThreshold} 
        onValueChange={(v: number) => partialThreshold = v}
        min={0} max={100} step={1}
        disabled={isPlanning || isExecuting}
      />
    </div>
    
    <div class="flex flex-col cq-gap">
      <div class="flex justify-between">
        <Label class="cq-text-sm">标记匹配</Label>
        <span class="cq-text-sm text-muted-foreground">{tokenThreshold}%</span>
      </div>
      <Slider 
        type="single"
        value={tokenThreshold} 
        onValueChange={(v: number) => tokenThreshold = v}
        min={0} max={100} step={1}
        disabled={isPlanning || isExecuting}
      />
    </div>
    
    <div class="flex flex-col cq-gap">
      <div class="flex justify-between">
        <Label class="cq-text-sm">长度差异</Label>
        <span class="cq-text-sm text-muted-foreground">{lengthDiffMax.toFixed(2)}</span>
      </div>
      <Slider 
        type="single"
        value={lengthDiffMax * 100} 
        onValueChange={(v: number) => lengthDiffMax = v / 100}
        min={0} max={100} step={1}
        disabled={isPlanning || isExecuting}
      />
    </div>
  </div>
{/snippet}

{#snippet actionBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex cq-gap">
      <Button 
        class="flex-1 cq-button" 
        onclick={handlePlan}
        disabled={isPlanning || isExecuting || !directoryPath}
      >
        {#if isPlanning}
          <Loader2 class="cq-icon mr-1 animate-spin" />
        {:else}
          <FolderSearch class="cq-icon mr-1" />
        {/if}
        扫描
      </Button>
      
      <Button 
        class="flex-1 cq-button" 
        variant="default"
        onclick={handleExecute}
        disabled={!hasPlan || isExecuting || isPlanning}
      >
        {#if isExecuting}
          <Loader2 class="cq-icon mr-1 animate-spin" />
        {:else}
          <Play class="cq-icon mr-1" />
        {/if}
        执行
      </Button>
    </div>
    
    {#if hasPlan}
      <div class="p-2 rounded bg-muted/50 cq-text-sm">
        <div>📚 系列: {totalSeries}</div>
        <div>📄 文件: {totalFiles}</div>
      </div>
    {/if}
    
    <Button variant="ghost" class="w-full cq-button-sm mt-auto" onclick={handleReset}>
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
  </div>
{/snippet}

{#snippet planBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    {#if !hasPlan}
      <div class="flex-1 flex items-center justify-center text-muted-foreground cq-text">
        点击"扫描"生成计划
      </div>
    {:else}
      <div class="flex-1 overflow-y-auto space-y-2 cq-padding">
        {#each Object.entries(plan) as [dirPath, groups] (dirPath)}
          {@const isExpanded = expandedDirs.has(dirPath)}
          {@const dirName = dirPath.split(/[/\\]/).pop() ?? dirPath}
          
          <div class="border rounded-lg bg-card/50">
            <!-- 目录标题 -->
            <button
              class="w-full flex items-center justify-between p-2 hover:bg-muted/50 transition-colors"
              onclick={() => toggleDir(dirPath)}
            >
              <div class="flex items-center cq-gap">
                {#if isExpanded}
                  <ChevronDown class="w-4 h-4" />
                {:else}
                  <ChevronRight class="w-4 h-4" />
                {/if}
                <span class="font-semibold cq-text truncate" title={dirPath}>
                  📁 {dirName}
                </span>
                <span class="cq-text-sm text-muted-foreground">
                  ({Object.keys(groups).length} 系列)
                </span>
              </div>
              <Button 
                variant="ghost" 
                size="icon"
                class="h-6 w-6"
                onclick={(e: MouseEvent) => { e.stopPropagation(); openFolder(dirPath); }}
              >
                <FolderOpen class="w-3 h-3" />
              </Button>
            </button>
            
            <!-- 系列列表 -->
            {#if isExpanded}
              <div class="border-t px-2 pb-2 space-y-1">
                {#each Object.entries(groups) as [folderName, files] (folderName)}
                  <div class="pl-6 py-1">
                    <div class="flex items-center cq-gap">
                      <span class="cq-text-sm font-medium text-primary">{folderName}</span>
                      <span class="cq-text-sm text-muted-foreground">({files.length})</span>
                    </div>
                    <div class="pl-4 space-y-0.5">
                      {#each files.slice(0, 5) as file (file)}
                        {@const fileName = file.split(/[/\\]/).pop() ?? file}
                        <div class="cq-text-sm text-muted-foreground truncate" title={file}>
                          └─ {fileName}
                        </div>
                      {/each}
                      {#if files.length > 5}
                        <div class="cq-text-sm text-muted-foreground">
                          ... 还有 {files.length - 5} 个文件
                        </div>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
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
        {#each logs.slice(-30) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'config'}{@render configBlock()}
  {:else if blockId === 'similarity'}{@render similarityBlock()}
  {:else if blockId === 'action'}{@render actionBlock()}
  {:else if blockId === 'plan'}{@render planBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 520px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={400} minHeight={350} maxWidth={520} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="seriex" 
    icon={BookOpen} 
    status={phase === 'idle' ? 'idle' : phase === 'planning' || phase === 'executing' ? 'running' : phase === 'completed' ? 'completed' : phase === 'error' ? 'error' : 'idle'} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="seriex" 
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
        nodeType="seriex"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={SERIEX_DEFAULT_GRID_LAYOUT}
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
