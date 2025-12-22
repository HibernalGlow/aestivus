<script lang="ts">
  /**
   * KavvkaNode - Czkawka 辅助工具节点
   * 
   * 功能：处理图片文件夹，查找画师文件夹，移动文件到比较文件夹
   * 支持关键词扫描（如"画集"）- 扫描结果填充到源路径
   * 生成 Czkawka 路径字符串
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Textarea } from '$lib/components/ui/textarea';
  import { Input } from '$lib/components/ui/input';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Label } from '$lib/components/ui/label';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { KAVVKA_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    LoaderCircle, Image, FolderOpen, Clipboard,
    Copy, Check, RotateCcw, Zap, Search
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

  type Phase = 'idle' | 'scanning' | 'running' | 'completed' | 'error';

  interface KavvkaState {
    sourcePaths: string[];
    scanRoots: string[];
    forceMove: boolean;
    keywords: string[];
    scanDepth: number;
  }

  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<KavvkaState>(nodeId));
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 默认关键词
  const DEFAULT_KEYWORDS = ['画集', 'CG', '图集', '作品集'];

  // 状态变量
  let sourcePaths = $state<string[]>([]);      // 处理用的源路径
  let sourcePathsText = $state('');
  let scanRoots = $state<string[]>([]);        // 扫描用的根目录
  let scanRootsText = $state('');
  let forceMove = $state(false);
  let keywords = $state<string[]>(DEFAULT_KEYWORDS);
  let keywordsText = $state('');
  let scanDepth = $state(3);
  
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
      scanRoots = savedState.scanRoots ?? [];
      forceMove = savedState.forceMove ?? false;
      keywords = savedState.keywords ?? DEFAULT_KEYWORDS;
      scanDepth = savedState.scanDepth ?? 3;
    }
    sourcePathsText = sourcePaths.join('\n');
    scanRootsText = scanRoots.join('\n');
    keywordsText = keywords.join(', ');
    initialized = true;
  });
  
  $effect(() => {
    logs = [...dataLogs];
    hasInputConnection = dataHasInputConnection;
  });

  function saveState() {
    if (!initialized) return;
    setNodeState<KavvkaState>(nodeId, { sourcePaths, scanRoots, forceMove, keywords, scanDepth });
  }

  let isRunning = $derived(phase === 'running' || phase === 'scanning');
  let canExecute = $derived((sourcePaths.length > 0 || hasInputConnection) && !isRunning);
  let canScan = $derived(scanRoots.length > 0 && !isRunning);
  let borderClass = $derived({
    idle: 'border-border',
    scanning: 'border-orange-500 shadow-sm',
    running: 'border-primary shadow-sm',
    completed: 'border-green-500/50',
    error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (forceMove !== undefined || scanDepth) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-50), msg]; }

  function updateSourcePaths(text: string) {
    sourcePathsText = text;
    sourcePaths = text.split('\n').map(s => s.trim()).filter(s => s);
    saveState();
  }

  function updateScanRoots(text: string) {
    scanRootsText = text;
    scanRoots = text.split('\n').map(s => s.trim()).filter(s => s);
    saveState();
  }

  function updateKeywords(text: string) {
    keywordsText = text;
    keywords = text.split(',').map(s => s.trim()).filter(s => s);
  }

  // 选择源路径文件夹
  async function selectSourceFolder() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog('选择源目录');
      if (selected) {
        sourcePaths = [...sourcePaths, selected];
        sourcePathsText = sourcePaths.join('\n');
        saveState();
      }
    } catch (e) { log(`选择文件夹失败: ${e}`); }
  }

  // 粘贴源路径
  async function pasteSourcePaths() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) {
        const paths = text.split('\n').map(s => s.trim()).filter(s => s);
        sourcePaths = [...sourcePaths, ...paths];
        sourcePathsText = sourcePaths.join('\n');
        saveState();
      }
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

  // 选择扫描根目录
  async function selectScanRoot() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog('选择扫描根目录');
      if (selected) {
        scanRoots = [...scanRoots, selected];
        scanRootsText = scanRoots.join('\n');
        saveState();
      }
    } catch (e) { log(`选择文件夹失败: ${e}`); }
  }

  // 粘贴扫描根目录
  async function pasteScanRoots() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) {
        const paths = text.split('\n').map(s => s.trim()).filter(s => s);
        scanRoots = [...scanRoots, ...paths];
        scanRootsText = scanRoots.join('\n');
        saveState();
      }
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

  // 扫描关键词 - 结果填充到源路径
  async function handleScan() {
    if (!canScan) return;
    
    phase = 'scanning';
    log(`🔍 扫描关键词: ${keywords.join(', ')}`);
    log(`📁 扫描深度: ${scanDepth}`);
    
    try {
      const response = await api.executeNode('kavvka', {
        action: 'scan',
        paths: scanRoots,
        keywords: keywords,
        scan_depth: scanDepth
      }) as any;
      
      if (response.logs) for (const m of response.logs) log(m);
      
      if (response.success) {
        phase = 'idle';
        const matchedPaths = response.data?.matched_paths ?? [];
        // 扫描结果填充到源路径
        sourcePaths = matchedPaths;
        sourcePathsText = sourcePaths.join('\n');
        saveState();
        log(`✅ 找到 ${matchedPaths.length} 个匹配文件夹，已填充到源路径`);
      } else {
        phase = 'error';
        log(`❌ 扫描失败: ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      log(`❌ 扫描失败: ${error}`);
    }
  }

  // 执行处理 - 统一使用源路径
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

  function clearSourcePaths() {
    sourcePaths = [];
    sourcePathsText = '';
    saveState();
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
      <Label class="cq-text font-medium">源路径（处理用）</Label>
      <div class="flex cq-gap">
        <Button variant="ghost" size="icon" class="cq-button-icon" onclick={clearSourcePaths} disabled={isRunning || sourcePaths.length === 0} title="清空">
          <RotateCcw class="cq-icon" />
        </Button>
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
        placeholder="每行一个路径（可手动输入或由扫描填充）..."
        disabled={isRunning}
        class="flex-1 cq-input font-mono text-xs resize-none min-h-[40px]"
      />
      <span class="cq-text-sm text-muted-foreground mt-1">{sourcePaths.length} 个路径</span>
    {/if}
  </div>
{/snippet}

{#snippet scanBlock()}
  <div class="h-full flex flex-col cq-gap">
    <!-- 扫描根目录输入 -->
    <div class="flex-1 flex flex-col">
      <div class="flex items-center justify-between cq-mb shrink-0">
        <Label class="cq-text font-medium">扫描根目录</Label>
        <div class="flex cq-gap">
          <Button variant="outline" size="icon" class="cq-button-icon" onclick={selectScanRoot} disabled={isRunning}>
            <FolderOpen class="cq-icon" />
          </Button>
          <Button variant="outline" size="icon" class="cq-button-icon" onclick={pasteScanRoots} disabled={isRunning}>
            <Clipboard class="cq-icon" />
          </Button>
        </div>
      </div>
      <Textarea 
        value={scanRootsText}
        oninput={(e) => updateScanRoots(e.currentTarget.value)}
        placeholder="每行一个根目录..."
        disabled={isRunning}
        class="flex-1 cq-input font-mono text-xs resize-none min-h-[30px]"
      />
      <span class="cq-text-sm text-muted-foreground">{scanRoots.length} 个根目录</span>
    </div>
    
    <div>
      <Label class="cq-text font-medium">关键词</Label>
      <Input 
        value={keywordsText}
        oninput={(e) => updateKeywords(e.currentTarget.value)}
        placeholder="画集, CG, 图集..."
        disabled={isRunning}
        class="cq-input text-xs mt-1"
      />
    </div>
    
    <div class="flex items-center cq-gap">
      <div>
        <Label class="cq-text font-medium">深度</Label>
        <Input 
          type="number"
          bind:value={scanDepth}
          min={1}
          max={10}
          disabled={isRunning}
          class="cq-input w-16 mt-1"
        />
      </div>
      <label class="flex items-center cq-gap cursor-pointer mt-4">
        <Checkbox bind:checked={forceMove} disabled={isRunning} />
        <span class="cq-text">强制移动</span>
      </label>
    </div>
    
    <Button 
      variant="outline" 
      class="w-full cq-button" 
      onclick={handleScan}
      disabled={!canScan}
    >
      {#if phase === 'scanning'}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Search class="cq-icon mr-1" />{/if}
      <span>扫描 → 填充源路径</span>
    </Button>
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="p-2 rounded cq-text-sm bg-muted/50">
      <div class="flex items-center gap-1 text-muted-foreground">
        <FolderOpen class="w-3 h-3" />
        <span>处理源路径</span>
      </div>
      <div class="text-muted-foreground mt-1">{sourcePaths.length} 个路径</div>
    </div>
    
    <Button 
      class="w-full cq-button flex-1" 
      onclick={handleExecute}
      disabled={!canExecute}
    >
      {#if phase === 'running'}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Zap class="cq-icon mr-1" />{/if}
      <span>处理 ({sourcePaths.length})</span>
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
  {:else if blockId === 'scan'}{@render scanBlock()}
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
