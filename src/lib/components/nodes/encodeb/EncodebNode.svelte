<script lang="ts">
  /**
   * EncodebNode - 文件名编码修复节点
   * 
   * 功能：修复乱码文件名，支持预览和批量重命名
   * 支持多种编码预设（中文、日文等）
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Textarea } from '$lib/components/ui/textarea';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { ENCODEB_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState } from '$lib/stores/nodeState.svelte';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, FileText, FolderOpen, Clipboard,
    CircleCheck, CircleX, Copy, Check, RotateCcw, Search, Zap
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

  type Phase = 'idle' | 'scanning' | 'previewing' | 'executing' | 'completed' | 'error';

  interface PreviewItem {
    src: string;
    dst: string;
  }

  // 共享状态接口
  interface EncodebNodeState {
    sourcePaths: string[];
    srcEncoding: string;
    dstEncoding: string;
    preset: string;
    strategy: 'replace' | 'copy';
    phase: Phase;
    logs: string[];
    previewItems: PreviewItem[];
  }

  const nodeId = $derived(id);
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);
  
  // 初始状态
  const defaultState: EncodebNodeState = {
    sourcePaths: [],
    srcEncoding: 'cp437',
    dstEncoding: 'cp936',
    preset: 'cn',
    strategy: 'replace',
    phase: 'idle',
    logs: [...dataLogs],
    previewItems: []
  };
  
  const ns = getNodeState<EncodebNodeState>(nodeId, defaultState);
  
  // UI 状态 (不需要同步)
  let sourcePathsText = $state(ns.sourcePaths.join('\n'));
  let copied = $state(false);
  let hasInputConnection = $state(dataHasInputConnection);
  let layoutRenderer = $state<any>(undefined);

  // 预设配置
  const PRESETS = [
    { id: 'cn', label: '中文', src: 'cp437', dst: 'cp936' },
    { id: 'jp', label: '日文', src: 'cp437', dst: 'cp932' },
    { id: 'kr', label: '韩文', src: 'cp437', dst: 'cp949' },
    { id: 'custom', label: '自定义', src: '', dst: '' }
  ];
  
  // 同步 hasInputConnection
  $effect(() => {
    hasInputConnection = dataHasInputConnection;
  });
  
  // 同步 sourcePathsText 和 ns.sourcePaths
  $effect(() => {
    sourcePathsText = ns.sourcePaths.join('\n');
  });

  let isRunning = $derived(ns.phase === 'scanning' || ns.phase === 'previewing' || ns.phase === 'executing');
  let canExecute = $derived(ns.phase === 'idle' || ns.phase === 'completed' || ns.phase === 'error');
  let borderClass = $derived({
    idle: 'border-border',
    scanning: 'border-primary shadow-sm',
    previewing: 'border-primary shadow-sm',
    executing: 'border-primary shadow-sm',
    completed: 'border-green-500/50',
    error: 'border-destructive/50'
  }[ns.phase]);

  function log(msg: string) { ns.logs = [...ns.logs.slice(-50), msg]; }

  function updateSourcePaths(text: string) {
    sourcePathsText = text;
    ns.sourcePaths = text.split('\n').map(s => s.trim()).filter(s => s);
  }

  function selectPreset(presetId: string) {
    ns.preset = presetId;
    const p = PRESETS.find(x => x.id === presetId);
    if (p && p.id !== 'custom') {
      ns.srcEncoding = p.src;
      ns.dstEncoding = p.dst;
    }
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

  // 预览
  async function handlePreview() {
    if (ns.sourcePaths.length === 0 && !hasInputConnection) return;
    
    ns.phase = 'previewing';
    ns.previewItems = [];
    log(`🔍 预览编码转换: ${ns.srcEncoding} -> ${ns.dstEncoding}`);
    
    try {
      const response = await api.executeNode('encodeb', {
        action: 'preview',
        paths: ns.sourcePaths,
        src_encoding: ns.srcEncoding,
        dst_encoding: ns.dstEncoding
      }) as any;
      
      if (response.success) {
        ns.previewItems = response.data?.mappings ?? [];
        ns.phase = ns.previewItems.length > 0 ? 'idle' : 'completed';
        log(`✅ 预览完成，${ns.previewItems.length} 个文件需要修复`);
      } else {
        ns.phase = 'error';
        log(`❌ 预览失败: ${response.message}`);
      }
    } catch (error) {
      ns.phase = 'error';
      log(`❌ 预览失败: ${error}`);
    }
  }

  // 扫描乱码
  async function handleFind() {
    if (ns.sourcePaths.length === 0 && !hasInputConnection) return;
    
    ns.phase = 'scanning';
    log(`🔍 扫描疑似乱码文件名...`);
    
    try {
      const response = await api.executeNode('encodeb', {
        action: 'find',
        paths: ns.sourcePaths
      }) as any;
      
      if (response.success) {
        const found = response.data?.matches ?? [];
        ns.phase = 'completed';
        log(`✅ 扫描完成，发现 ${found.length} 个疑似乱码`);
        if (response.logs) for (const m of response.logs) log(m);
      } else {
        ns.phase = 'error';
        log(`❌ 扫描失败: ${response.message}`);
      }
    } catch (error) {
      ns.phase = 'error';
      log(`❌ 扫描失败: ${error}`);
    }
  }

  // 执行修复
  async function handleExecute() {
    if (ns.sourcePaths.length === 0 && !hasInputConnection) return;
    
    ns.phase = 'executing';
    log(`⚡ 执行编码修复 (${ns.strategy === 'replace' ? '原地重命名' : '复制'})`);
    
    try {
      const response = await api.executeNode('encodeb', {
        action: 'recover',
        paths: ns.sourcePaths,
        src_encoding: ns.srcEncoding,
        dst_encoding: ns.dstEncoding,
        strategy: ns.strategy
      }) as any;
      
      if (response.logs) for (const m of response.logs) log(m);
      
      if (response.success) {
        ns.phase = 'completed';
        ns.previewItems = [];
        log(`✅ ${response.message}`);
      } else {
        ns.phase = 'error';
        log(`❌ 执行失败: ${response.message}`);
      }
    } catch (error) {
      ns.phase = 'error';
      log(`❌ 执行失败: ${error}`);
    }
  }

  function handleReset() {
    ns.phase = 'idle';
    ns.previewItems = [];
    ns.logs = [];
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(ns.logs.join('\n'));
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
        placeholder="每行一个路径..."
        disabled={isRunning}
        class="flex-1 cq-input font-mono text-xs resize-none min-h-[60px]"
      />
      <span class="cq-text-sm text-muted-foreground mt-1">{ns.sourcePaths.length} 个路径</span>
    {/if}
  </div>
{/snippet}

{#snippet encodingBlock()}
  <div class="flex flex-col cq-gap h-full">
    <Label class="cq-text font-medium">编码预设</Label>
    <div class="grid grid-cols-4 cq-gap">
      {#each PRESETS as p}
        <Button 
          variant={ns.preset === p.id ? 'default' : 'outline'} 
          size="sm" 
          class="cq-button-sm"
          onclick={() => selectPreset(p.id)}
          disabled={isRunning}
        >
          {p.label}
        </Button>
      {/each}
    </div>
    
    <div class="flex cq-gap">
      <div class="flex-1">
        <Label class="cq-text-sm text-muted-foreground">源编码</Label>
        <Input bind:value={ns.srcEncoding} disabled={isRunning || ns.preset !== 'custom'} class="cq-input font-mono" />
      </div>
      <div class="flex-1">
        <Label class="cq-text-sm text-muted-foreground">目标编码</Label>
        <Input bind:value={ns.dstEncoding} disabled={isRunning || ns.preset !== 'custom'} class="cq-input font-mono" />
      </div>
    </div>
    
    <Label class="cq-text font-medium">修复策略</Label>
    <div class="flex cq-gap">
      <Button 
        variant={ns.strategy === 'replace' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm flex-1"
        onclick={() => ns.strategy = 'replace'}
        disabled={isRunning}
      >
        原地重命名
      </Button>
      <Button 
        variant={ns.strategy === 'copy' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm flex-1"
        onclick={() => ns.strategy = 'copy'}
        disabled={isRunning}
      >
        复制到新目录
      </Button>
    </div>
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <Button 
      variant="outline" 
      class="w-full cq-button flex-1" 
      onclick={handleFind}
      disabled={isRunning || (ns.sourcePaths.length === 0 && !hasInputConnection)}
    >
      {#if ns.phase === 'scanning'}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Search class="cq-icon mr-1" />{/if}
      <span>扫描乱码</span>
    </Button>
    
    <Button 
      variant="outline" 
      class="w-full cq-button flex-1" 
      onclick={handlePreview}
      disabled={isRunning || (ns.sourcePaths.length === 0 && !hasInputConnection)}
    >
      {#if ns.phase === 'previewing'}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<FileText class="cq-icon mr-1" />{/if}
      <span>预览</span>
    </Button>
    
    <Button 
      class="w-full cq-button flex-1" 
      onclick={handleExecute}
      disabled={isRunning || (ns.sourcePaths.length === 0 && !hasInputConnection)}
    >
      {#if ns.phase === 'executing'}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Zap class="cq-icon mr-1" />{/if}
      <span>执行修复</span>
    </Button>
    
    <Button variant="ghost" class="w-full cq-button-sm" onclick={handleReset}>
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
  </div>
{/snippet}

{#snippet previewBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0">
      <span class="font-semibold cq-text">预览结果</span>
      {#if ns.previewItems.length > 0}
        <span class="cq-text-sm text-muted-foreground">{ns.previewItems.length} 项</span>
      {/if}
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
      {#if ns.previewItems.length > 0}
        {#each ns.previewItems.slice(0, 50) as item}
          <div class="mb-2 cq-text-sm">
            <div class="text-muted-foreground truncate">{item.src}</div>
            <div class="text-primary truncate">→ {item.dst}</div>
          </div>
        {/each}
        {#if ns.previewItems.length > 50}
          <div class="text-muted-foreground cq-text-sm text-center">... 还有 {ns.previewItems.length - 50} 项</div>
        {/if}
      {:else}
        <div class="text-center text-muted-foreground py-4 cq-text">点击"预览"查看转换结果</div>
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
      {#if ns.logs.length > 0}
        {#each ns.logs.slice(-15) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'source'}{@render sourceBlock()}
  {:else if blockId === 'encoding'}{@render encodingBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'preview'}{@render previewBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 480px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={360} minHeight={320} maxWidth={480} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="encodeb" 
    icon={FileText} 
    status={ns.phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="encodeb" 
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
        nodeType="encodeb"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={ENCODEB_DEFAULT_GRID_LAYOUT}
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
