<script lang="ts">
  /**
   * CrashuNode - 文件夹名称相似度检测节点
   * 
   * 功能：扫描源目录，与目标文件夹名称进行相似度匹配
   * 支持别名解析，可批量移动相似文件夹
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import { Badge } from '$lib/components/ui/badge';
  import { Slider } from '$lib/components/ui/slider';
  import { Textarea } from '$lib/components/ui/textarea';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { CRASHU_DEFAULT_GRID_LAYOUT } from '$lib/components/blocks/blockRegistry';
  import { api } from '$lib/services/api';
  import { getNodeState, saveNodeState } from '$lib/stores/nodeState.svelte';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, FolderOpen, Clipboard, Zap, Target,
    CircleCheck, Copy, Check, ArrowRight, ChevronRight, ChevronDown, Folder
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: { 
        source_paths?: string[];
        target_path?: string;
        target_names?: string[];
        similarity_threshold?: number;
        auto_move?: boolean;
      };
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'scanning' | 'completed' | 'error';

  interface SimilarFolder {
    name: string;
    path: string;
    target: string;
    similarity: number;
    match_dim?: string;
    match_src?: string;
    match_tgt?: string;
    target_fullpath?: string;
  }

  interface CrashuResult {
    total_scanned: number;
    similar_found: number;
    moved_count: number;
    similar_folders: SimilarFolder[];
  }

  interface CrashuState {
    phase: Phase;
    progress: number;
    progressText: string;
    result: CrashuResult | null;
    sourcePaths: string[];
    targetPath: string;
    targetNames: string[];
    similarityThreshold: number;
    autoMove: boolean;
    expandedItems: string[];
    logs: string[];
    hasInputConnection: boolean;
  }

  const nodeId = $derived(id);
  const configSourcePaths = $derived(data?.config?.source_paths ?? []);
  const configTargetPath = $derived(data?.config?.target_path ?? '');
  const configTargetNames = $derived(data?.config?.target_names ?? []);
  const configSimilarityThreshold = $derived(data?.config?.similarity_threshold ?? 0.6);
  const configAutoMove = $derived(data?.config?.auto_move ?? false);
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 获取共享的响应式状态（节点模式和全屏模式共用同一个对象）
  const ns = getNodeState<CrashuState>(id, {
    phase: 'idle',
    progress: 0,
    progressText: '',
    result: null,
    sourcePaths: configSourcePaths,
    targetPath: configTargetPath,
    targetNames: configTargetNames,
    similarityThreshold: configSimilarityThreshold,
    autoMove: configAutoMove,
    expandedItems: [],
    logs: [],
    hasInputConnection: false
  });

  // 纯 UI 状态（不需要同步）
  let copied = $state(false);
  let layoutRenderer = $state<any>(undefined);
  // 文本区域的本地编辑状态
  let sourcePathsText = $state(ns.sourcePaths.join('\n'));
  let targetNamesText = $state(ns.targetNames.join('\n'));
  // expandedItems 需要 Set 格式用于 UI
  let expandedItems = $state<Set<string>>(new Set(ns.expandedItems));
  
  $effect(() => {
    ns.logs = [...dataLogs];
    ns.hasInputConnection = dataHasInputConnection;
  });

  let canExecute = $derived(ns.phase === 'idle' && (ns.sourcePaths.length > 0 || ns.hasInputConnection) && (ns.targetPath.trim() !== '' || ns.targetNames.length > 0));
  let isRunning = $derived(ns.phase === 'scanning');
  let borderClass = $derived({ idle: 'border-border', scanning: 'border-primary shadow-sm', completed: 'border-primary/50', error: 'border-destructive/50' }[ns.phase]);

  function log(msg: string) { ns.logs = [...ns.logs.slice(-30), msg]; }
  function toggleItem(key: string) { 
    if (expandedItems.has(key)) expandedItems.delete(key); 
    else expandedItems.add(key); 
    expandedItems = new Set(expandedItems);
    ns.expandedItems = Array.from(expandedItems);
  }

  function updateSourcePaths(text: string) {
    sourcePathsText = text;
    ns.sourcePaths = text.split('\n').map(s => s.trim()).filter(s => s);
  }

  function updateTargetNames(text: string) {
    targetNamesText = text;
    ns.targetNames = text.split('\n').map(s => s.trim()).filter(s => s);
  }

  async function selectSourceFolder() { 
    try { 
      const { platform } = await import('$lib/api/platform'); 
      const selected = await platform.openFolderDialog('选择源目录'); 
      if (selected) {
        ns.sourcePaths = [...ns.sourcePaths, selected];
        sourcePathsText = ns.sourcePaths.join('\n');
      }
    } catch (e) { log(`选择文件夹失败: ${e}`); } 
  }

  async function selectTargetFolder() { 
    try { 
      const { platform } = await import('$lib/api/platform'); 
      const selected = await platform.openFolderDialog('选择目标目录'); 
      if (selected) ns.targetPath = selected;
    } catch (e) { log(`选择文件夹失败: ${e}`); } 
  }

  async function pasteSourcePaths() { 
    try { 
      const { platform } = await import('$lib/api/platform'); 
      const text = await platform.readClipboard(); 
      if (text) {
        const paths = text.split('\n').map(s => s.trim()).filter(s => s);
        ns.sourcePaths = [...ns.sourcePaths, ...paths];
        sourcePathsText = ns.sourcePaths.join('\n');
      }
    } catch (e) { log(`读取剪贴板失败: ${e}`); } 
  }

  async function handleExecute() {
    if (!canExecute) return;
    ns.phase = 'scanning'; ns.progress = 0; ns.progressText = '正在扫描...';
    ns.result = null; expandedItems.clear(); ns.expandedItems = [];
    log(`💥 开始执行 crashu`);
    log(`📂 源目录: ${ns.sourcePaths.length} 个`);
    log(`🎯 目标: ${ns.targetPath || ns.targetNames.join(', ')}`);
    log(`📋 相似度阈值: ${(ns.similarityThreshold * 100).toFixed(0)}%`);
    
    try {
      ns.progress = 30; ns.progressText = '正在匹配文件夹名称...';
      const response = await api.executeNode('crashu', { 
        source_paths: ns.sourcePaths,
        target_path: ns.targetPath,
        target_names: ns.targetNames,
        similarity_threshold: ns.similarityThreshold, 
        auto_move: ns.autoMove 
      }) as any;
      
      if (response.logs) for (const m of response.logs) log(m);
      
      if (response.success) {
        ns.phase = 'completed'; ns.progress = 100; ns.progressText = '检测完成';
        ns.result = {
          total_scanned: response.data?.total_scanned ?? 0,
          similar_found: response.data?.similar_found ?? 0,
          moved_count: response.data?.moved_count ?? 0,
          similar_folders: response.data?.similar_folders ?? []
        };
        log(`✅ ${response.message}`);
      } else { 
        ns.phase = 'error'; ns.progress = 0; 
        log(`❌ 执行失败: ${response.message}`); 
      }
    } catch (error) { 
      ns.phase = 'error'; ns.progress = 0; 
      log(`❌ 执行失败: ${error}`); 
    }
  }

  function handleReset() { 
    ns.phase = 'idle'; ns.progress = 0; ns.progressText = ''; 
    ns.result = null; ns.logs = []; expandedItems.clear(); ns.expandedItems = [];
  }
  
  async function copyLogs() { 
    try { 
      await navigator.clipboard.writeText(ns.logs.join('\n')); 
      copied = true; 
      setTimeout(() => { copied = false; }, 2000); 
    } catch (e) { console.error('复制失败:', e); } 
  }

  async function copyResults() {
    if (!ns.result?.similar_folders.length) return;
    const text = ns.result.similar_folders.map(f => 
      `${f.path} -> ${f.target} (${(f.similarity * 100).toFixed(0)}%)`
    ).join('\n');
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }
</script>

<!-- 源目录输入区块 -->
{#snippet sourceBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between cq-mb shrink-0">
      <span class="cq-text font-medium flex items-center gap-1">
        <Folder class="cq-icon text-blue-500" />源目录
      </span>
      <div class="flex cq-gap">
        <Button variant="outline" size="icon" class="cq-button-icon" onclick={selectSourceFolder} disabled={isRunning}>
          <FolderOpen class="cq-icon" />
        </Button>
        <Button variant="outline" size="icon" class="cq-button-icon" onclick={pasteSourcePaths} disabled={isRunning}>
          <Clipboard class="cq-icon" />
        </Button>
      </div>
    </div>
    {#if ns.hasInputConnection}
      <div class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-text">
        <span>←</span><span>输入来自上游节点</span>
      </div>
    {:else}
      <Textarea 
        value={sourcePathsText}
        oninput={(e) => updateSourcePaths(e.currentTarget.value)}
        placeholder="每行一个源目录路径..."
        disabled={isRunning}
        class="flex-1 cq-input font-mono text-xs resize-none min-h-[60px]"
      />
      <span class="cq-text-sm text-muted-foreground mt-1">{ns.sourcePaths.length} 个目录</span>
    {/if}
  </div>
{/snippet}

<!-- 目标配置区块 -->
{#snippet targetBlock()}
  <div class="h-full flex flex-col cq-space">
    <!-- 目标路径 -->
    <div>
      <div class="flex items-center justify-between cq-mb">
        <span class="cq-text font-medium flex items-center gap-1">
          <Target class="cq-icon text-orange-500" />目标路径
        </span>
        <Button variant="outline" size="icon" class="cq-button-icon" onclick={selectTargetFolder} disabled={isRunning}>
          <FolderOpen class="cq-icon" />
        </Button>
      </div>
      <Input 
        bind:value={ns.targetPath} 
        placeholder="自动获取子文件夹名称..." 
        disabled={isRunning} 
        class="cq-input"
      />
      <span class="cq-text-sm text-muted-foreground">从此目录自动获取文件夹名称</span>
    </div>
    <!-- 或手动指定名称 -->
    <div class="flex-1 flex flex-col">
      <span class="cq-text font-medium cq-mb">或手动指定名称</span>
      <Textarea 
        value={targetNamesText}
        oninput={(e) => updateTargetNames(e.currentTarget.value)}
        placeholder="每行一个目标名称..."
        disabled={isRunning || ns.targetPath.trim() !== ''}
        class="flex-1 cq-input font-mono text-xs resize-none min-h-[40px]"
      />
    </div>
  </div>
{/snippet}

<!-- 选项区块 -->
{#snippet optionsBlock()}
  <div class="cq-space">
    <div class="cq-space-sm">
      <div class="flex items-center justify-between cq-text">
        <span>相似度阈值</span>
        <span class="font-mono text-primary">{(ns.similarityThreshold * 100).toFixed(0)}%</span>
      </div>
      <Slider 
        type="single" 
        value={ns.similarityThreshold} 
        onValueChange={(v: number) => ns.similarityThreshold = v} 
        min={0.3} max={1} step={0.05} 
        disabled={isRunning} 
        class="w-full" 
      />
      <div class="flex justify-between cq-text-sm text-muted-foreground">
        <span>宽松</span><span>严格</span>
      </div>
    </div>
    <label class="flex items-center cq-gap cursor-pointer">
      <Checkbox id="auto-move-{nodeId}" bind:checked={ns.autoMove} disabled={isRunning} />
      <span class="cq-text flex items-center gap-1">
        <ArrowRight class="cq-icon" />自动移动匹配文件夹
      </span>
    </label>
  </div>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if ns.phase === 'completed'}
        <CircleCheck class="cq-icon text-green-500 shrink-0" />
        <span class="cq-text text-green-600 font-medium">完成</span>
        <span class="cq-text-sm text-muted-foreground ml-auto">{ns.result?.similar_found ?? 0} 个匹配</span>
      {:else if ns.phase === 'error'}
        <Zap class="cq-icon text-red-500 shrink-0" />
        <span class="cq-text text-red-600 font-medium">失败</span>
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1"><Progress value={ns.progress} class="h-1.5" /></div>
        <span class="cq-text-sm text-muted-foreground">{ns.progress}%</span>
      {:else}
        <Zap class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待执行</span>
      {/if}
    </div>
    <Button class="w-full cq-button flex-1" onclick={handleExecute} disabled={!canExecute || isRunning}>
      {#if isRunning}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Zap class="cq-icon mr-1" />{/if}
      <span>检测相似</span>
    </Button>
    {#if ns.phase === 'completed' || ns.phase === 'error'}
      <Button variant="outline" class="w-full cq-button-sm" onclick={handleReset}>
        <Play class="cq-icon mr-1" />重新开始
      </Button>
    {/if}
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock()}
  {#if ns.result}
    <div class="grid grid-cols-3 cq-gap">
      <div class="cq-stat-card bg-blue-500/10">
        <div class="flex flex-col items-center">
          <span class="cq-stat-value text-blue-600 tabular-nums">{ns.result.total_scanned}</span>
          <span class="cq-stat-label text-muted-foreground">目标数</span>
        </div>
      </div>
      <div class="cq-stat-card bg-green-500/10">
        <div class="flex flex-col items-center">
          <span class="cq-stat-value text-green-600 tabular-nums">{ns.result.similar_found}</span>
          <span class="cq-stat-label text-muted-foreground">匹配</span>
        </div>
      </div>
      <div class="cq-stat-card bg-orange-500/10">
        <div class="flex flex-col items-center">
          <span class="cq-stat-value text-orange-600 tabular-nums">{ns.result.moved_count}</span>
          <span class="cq-stat-label text-muted-foreground">已移动</span>
        </div>
      </div>
    </div>
  {:else}
    <div class="cq-text text-muted-foreground text-center py-2">检测后显示统计</div>
  {/if}
{/snippet}

<!-- 结果列表区块 -->
{#snippet resultsBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0">
      <div class="flex items-center cq-gap">
        <Target class="cq-icon text-green-500" />
        <span class="font-semibold cq-text">匹配结果</span>
        {#if ns.result}<Badge variant="secondary" class="cq-text-sm">{ns.result.similar_found}</Badge>{/if}
      </div>
      {#if ns.result?.similar_folders.length}
        <Button variant="ghost" size="icon" class="h-5 w-5" onclick={copyResults}>
          {#if copied}<Check class="w-3 h-3 text-green-500" />{:else}<Copy class="w-3 h-3" />{/if}
        </Button>
      {/if}
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
      {#if ns.result && ns.result.similar_folders.length > 0}
        {#each ns.result.similar_folders as folder}
          {@const isExpanded = expandedItems.has(folder.path)}
          <div class="mb-2">
            <button 
              class="w-full flex items-center cq-gap cq-padding cq-rounded hover:bg-muted/50 text-left" 
              onclick={() => toggleItem(folder.path)}
            >
              {#if isExpanded}<ChevronDown class="cq-icon text-muted-foreground" />
              {:else}<ChevronRight class="cq-icon text-muted-foreground" />{/if}
              <Folder class="cq-icon text-yellow-500" />
              <span class="flex-1 cq-text truncate">{folder.name}</span>
              <Badge variant="outline" class="cq-text-sm">{(folder.similarity * 100).toFixed(0)}%</Badge>
            </button>
            {#if isExpanded}
              <div class="ml-6 mt-1 cq-space-sm cq-text-sm">
                <div class="flex items-center gap-1 text-muted-foreground">
                  <span>源:</span>
                  <span class="truncate font-mono">{folder.path}</span>
                </div>
                <div class="flex items-center gap-1 text-muted-foreground">
                  <ArrowRight class="w-3 h-3" />
                  <span>目标:</span>
                  <span class="truncate font-mono text-primary">{folder.target}</span>
                </div>
                {#if folder.match_dim}
                  <div class="text-muted-foreground/70">
                    匹配: {folder.match_src} ↔ {folder.match_tgt} ({folder.match_dim})
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      {:else}
        <div class="text-center text-muted-foreground py-8 cq-text">检测后显示匹配结果</div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 日志区块 -->
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
        {#each ns.logs.slice(-15) as logItem}
          <div class="text-muted-foreground break-all">{logItem}</div>
        {/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 区块渲染器 -->
{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'source'}{@render sourceBlock()}
  {:else if blockId === 'target'}{@render targetBlock()}
  {:else if blockId === 'options'}{@render optionsBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'stats'}{@render statsBlock()}
  {:else if blockId === 'results'}{@render resultsBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<!-- 主渲染 -->
<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 420px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={300} minHeight={300} maxWidth={420} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="crashu" 
    icon={Zap} 
    status={ns.phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="crashu" 
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
        nodeType="crashu"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={CRASHU_DEFAULT_GRID_LAYOUT}
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
