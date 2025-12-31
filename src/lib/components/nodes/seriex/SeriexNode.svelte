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
  import { getNodeState, saveNodeState } from '$lib/stores/nodeState.svelte';
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
    // 运行时状态
    phase: Phase;
    logs: string[];
    plan: Record<string, Record<string, string[]>>;
    totalSeries: number;
    totalFiles: number;
    expandedDirs: string[];
  }

  const nodeId = $derived(id);
  const dataLogs = $derived(data?.logs ?? []);

  // 获取共享的响应式状态
  const ns = getNodeState<SeriexState>(id, {
    directoryPath: '',
    threshold: 75,
    ratioThreshold: 75,
    partialThreshold: 85,
    tokenThreshold: 80,
    lengthDiffMax: 0.3,
    addPrefix: true,
    prefix: '[#s]',
    knownSeriesDirs: '',
    phase: 'idle',
    logs: [],
    plan: {},
    totalSeries: 0,
    totalFiles: 0,
    expandedDirs: []
  });

  // 本地 UI 状态
  let copied = $state(false);
  let layoutRenderer = $state<any>(undefined);
  
  // 展开状态 Set（派生自 ns.expandedDirs）
  let expandedDirsSet = $state<Set<string>>(new Set());

  // 同步 data.logs
  $effect(() => { 
    if (dataLogs.length > 0) {
      ns.logs = [...dataLogs]; 
    }
  });
  
  // 同步 expandedDirs
  $effect(() => {
    expandedDirsSet = new Set(ns.expandedDirs);
  });

  // 派生状态
  let isPlanning = $derived(ns.phase === 'planning');
  let isExecuting = $derived(ns.phase === 'executing');
  let hasPlan = $derived(Object.keys(ns.plan).length > 0);
  
  let borderClass = $derived({
    idle: 'border-border',
    planning: 'border-primary shadow-sm',
    planned: 'border-blue-500/50',
    executing: 'border-orange-500/50',
    completed: 'border-green-500/50',
    error: 'border-destructive/50'
  }[ns.phase]);

  // 配置变更时自动保存
  $effect(() => { 
    ns.directoryPath; ns.threshold;
    saveNodeState(nodeId); 
  });

  function log(msg: string) { ns.logs = [...ns.logs.slice(-100), msg]; }

  // 生成计划
  async function handlePlan() {
    if (!ns.directoryPath) {
      log('❌ 请输入目录路径');
      return;
    }
    
    ns.phase = 'planning';
    ns.plan = {};
    log(`📂 开始扫描: ${ns.directoryPath}`);
    
    try {
      const response = await api.executeNode('seriex', {
        action: 'plan',
        directory_path: ns.directoryPath,
        threshold: ns.threshold,
        ratio_threshold: ns.ratioThreshold,
        partial_threshold: ns.partialThreshold,
        token_threshold: ns.tokenThreshold,
        length_diff_max: ns.lengthDiffMax,
        add_prefix: ns.addPrefix,
        prefix: ns.prefix,
        known_series_dirs: ns.knownSeriesDirs.split('\n').filter(s => s.trim())
      }) as any;
      
      if (response.logs) for (const m of response.logs) log(m);
      
      if (response.success) {
        ns.phase = 'planned';
        ns.plan = response.data?.plan ?? {};
        ns.totalSeries = response.data?.total_series ?? 0;
        ns.totalFiles = response.data?.total_files ?? 0;
        
        // 默认展开所有目录
        ns.expandedDirs = Object.keys(ns.plan);
        
        log(`✅ ${response.message}`);
      } else {
        ns.phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (error) {
      ns.phase = 'error';
      log(`❌ 扫描失败: ${error}`);
    }
  }

  // 执行计划
  async function handleExecute() {
    if (!hasPlan) {
      log('❌ 没有可执行的计划');
      return;
    }
    
    ns.phase = 'executing';
    log(`🚀 开始执行移动...`);
    
    try {
      const response = await api.executeNode('seriex', {
        action: 'apply',
        directory_path: ns.directoryPath,
        threshold: ns.threshold,
        ratio_threshold: ns.ratioThreshold,
        partial_threshold: ns.partialThreshold,
        token_threshold: ns.tokenThreshold,
        length_diff_max: ns.lengthDiffMax,
        add_prefix: ns.addPrefix,
        prefix: ns.prefix,
        known_series_dirs: ns.knownSeriesDirs.split('\n').filter(s => s.trim())
      }) as any;
      
      if (response.logs) for (const m of response.logs) log(m);
      
      if (response.success) {
        ns.phase = 'completed';
        ns.totalSeries = response.data?.total_series ?? 0;
        ns.totalFiles = response.data?.total_files ?? 0;
        ns.plan = {}; // 清空计划
        log(`✅ ${response.message}`);
      } else {
        ns.phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (error) {
      ns.phase = 'error';
      log(`❌ 执行失败: ${error}`);
    }
  }

  function toggleDir(dirPath: string) {
    const newSet = new Set(expandedDirsSet);
    if (newSet.has(dirPath)) {
      newSet.delete(dirPath);
    } else {
      newSet.add(dirPath);
    }
    expandedDirsSet = newSet;
    ns.expandedDirs = Array.from(newSet);
  }

  function handleReset() {
    ns.phase = 'idle';
    ns.plan = {};
    ns.expandedDirs = [];
    ns.logs = [];
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(ns.logs.join('\n'));
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
        bind:value={ns.directoryPath}
        placeholder="要处理的目录路径"
        disabled={isPlanning || isExecuting}
        class="cq-input font-mono text-xs"
      />
    </div>
    
    <div class="flex flex-col cq-gap">
      <Label class="cq-text font-medium">系列前缀</Label>
      <Input 
        bind:value={ns.prefix}
        placeholder="[#s]"
        disabled={isPlanning || isExecuting}
        class="cq-input font-mono text-xs"
      />
    </div>
    
    <div class="flex items-center cq-gap">
      <Checkbox 
        id="addPrefix"
        bind:checked={ns.addPrefix}
        disabled={isPlanning || isExecuting}
      />
      <Label for="addPrefix" class="cq-text-sm">添加系列前缀</Label>
    </div>
    
    <div class="flex flex-col cq-gap">
      <Label class="cq-text font-medium">已知系列目录（每行一个）</Label>
      <textarea 
        bind:value={ns.knownSeriesDirs}
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
        <span class="cq-text-sm text-muted-foreground">{ns.threshold}%</span>
      </div>
      <Slider 
        type="single"
        value={ns.threshold} 
        onValueChange={(v: number) => ns.threshold = v}
        min={0} max={100} step={1}
        disabled={isPlanning || isExecuting}
      />
    </div>
    
    <div class="flex flex-col cq-gap">
      <div class="flex justify-between">
        <Label class="cq-text-sm">完全匹配</Label>
        <span class="cq-text-sm text-muted-foreground">{ns.ratioThreshold}%</span>
      </div>
      <Slider 
        type="single"
        value={ns.ratioThreshold} 
        onValueChange={(v: number) => ns.ratioThreshold = v}
        min={0} max={100} step={1}
        disabled={isPlanning || isExecuting}
      />
    </div>
    
    <div class="flex flex-col cq-gap">
      <div class="flex justify-between">
        <Label class="cq-text-sm">部分匹配</Label>
        <span class="cq-text-sm text-muted-foreground">{ns.partialThreshold}%</span>
      </div>
      <Slider 
        type="single"
        value={ns.partialThreshold} 
        onValueChange={(v: number) => ns.partialThreshold = v}
        min={0} max={100} step={1}
        disabled={isPlanning || isExecuting}
      />
    </div>
    
    <div class="flex flex-col cq-gap">
      <div class="flex justify-between">
        <Label class="cq-text-sm">标记匹配</Label>
        <span class="cq-text-sm text-muted-foreground">{ns.tokenThreshold}%</span>
      </div>
      <Slider 
        type="single"
        value={ns.tokenThreshold} 
        onValueChange={(v: number) => ns.tokenThreshold = v}
        min={0} max={100} step={1}
        disabled={isPlanning || isExecuting}
      />
    </div>
    
    <div class="flex flex-col cq-gap">
      <div class="flex justify-between">
        <Label class="cq-text-sm">长度差异</Label>
        <span class="cq-text-sm text-muted-foreground">{ns.lengthDiffMax.toFixed(2)}</span>
      </div>
      <Slider 
        type="single"
        value={ns.lengthDiffMax * 100} 
        onValueChange={(v: number) => ns.lengthDiffMax = v / 100}
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
        disabled={isPlanning || isExecuting || !ns.directoryPath}
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
        <div>📚 系列: {ns.totalSeries}</div>
        <div>📄 文件: {ns.totalFiles}</div>
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
        {#each Object.entries(ns.plan) as [dirPath, groups] (dirPath)}
          {@const isExpanded = expandedDirsSet.has(dirPath)}
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
      {#if ns.logs.length > 0}
        {#each ns.logs.slice(-30) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
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
    status={ns.phase === 'idle' ? 'idle' : ns.phase === 'planning' || ns.phase === 'executing' ? 'running' : ns.phase === 'completed' ? 'completed' : ns.phase === 'error' ? 'error' : 'idle'} 
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
