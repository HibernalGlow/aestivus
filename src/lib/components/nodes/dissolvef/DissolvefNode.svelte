<script lang="ts">
  /**
   * DissolvefNode - 文件夹解散节点组件
   * 支持解散嵌套文件夹、单媒体文件夹、单压缩包文件夹、直接解散
   * 支持相似度限制和撤销功能
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Progress } from '$lib/components/ui/progress';
  import { Input } from '$lib/components/ui/input';
  import { Slider } from '$lib/components/ui/slider';
  import * as Select from '$lib/components/ui/select';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { DISSOLVEF_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, saveNodeState } from '$lib/stores/nodeState.svelte';
  import { getWsBaseUrl } from '$lib/stores/backend';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, Clipboard, FolderOpen, FolderInput,
    CircleCheck, CircleX, Copy, Check, RotateCcw, Undo2
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: { 
        path?: string; 
        mode?: string;
        nested?: boolean;
        media?: boolean;
        archive?: boolean;
        direct?: boolean;
        preview?: boolean;
        exclude?: string;
        file_conflict?: string;
        dir_conflict?: string;
      };
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
      label?: string;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'running' | 'completed' | 'error';

  interface OperationRecord {
    id: string;
    timestamp: string;
    mode: string;
    path: string;
    count: number;
    canUndo: boolean;
  }

  interface DissolvefState {
    phase: Phase;
    progress: number;
    progressText: string;
    pathText: string;
    nestedMode: boolean;
    mediaMode: boolean;
    archiveMode: boolean;
    directMode: boolean;
    previewMode: boolean;
    excludeKeywords: string;
    fileConflict: string;
    dirConflict: string;
    enableSimilarity: boolean;
    similarityThreshold: number;
    result: DissolveResult | null;
    operationHistory: OperationRecord[];
    lastOperationId: string;
  }

  interface DissolveResult {
    success: boolean;
    nested_count: number;
    media_count: number;
    archive_count: number;
    direct_files: number;
    direct_dirs: number;
    skipped_count: number;
  }

  const nodeId = $derived(id);
  const configPath = $derived(data?.config?.path ?? '');
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 获取共享的响应式状态（节点模式和全屏模式共用同一个对象）
  const ns = getNodeState<DissolvefState>(id, {
    phase: 'idle',
    progress: 0,
    progressText: '',
    pathText: configPath || '',
    nestedMode: true,
    mediaMode: true,
    archiveMode: true,
    directMode: false,
    previewMode: false,
    excludeKeywords: '',
    fileConflict: 'auto',
    dirConflict: 'auto',
    enableSimilarity: true,
    similarityThreshold: 0.6,
    result: null,
    operationHistory: [],
    lastOperationId: '',
    logs: [],
    hasInputConnection: false
  });

  // 纯 UI 状态（不需要同步）
  let copied = $state(false);
  let layoutRenderer = $state<any>(undefined);
  // similarityThreshold slider 需要数组格式
  let similarityThresholdArr = $derived([ns.similarityThreshold]);
  
  // 持续同步外部数据
  $effect(() => {
    ns.logs = [...dataLogs];
    ns.hasInputConnection = dataHasInputConnection;
  });

  let canExecute = $derived(ns.phase === 'idle' && (ns.pathText.trim() !== '' || ns.hasInputConnection));
  let isRunning = $derived(ns.phase === 'running');
  let borderClass = $derived({
    idle: 'border-border', running: 'border-primary shadow-sm',
    completed: 'border-primary/50', error: 'border-destructive/50'
  }[ns.phase]);

  function log(msg: string) { ns.logs = [...ns.logs.slice(-30), msg]; }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) {
        ns.pathText = text.trim().replace(/^["']|["']$/g, '');
        log(`📋 从剪贴板读取路径`);
      }
    } catch (e) { log(`❌ 读取剪贴板失败: ${e}`); }
  }

  async function selectFolder() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFolderDialog('选择要处理的文件夹');
      if (selected) {
        ns.pathText = selected;
        log(`📁 选择了文件夹: ${selected.split(/[/\\]/).pop()}`);
      }
    } catch (e) { log(`❌ 选择文件夹失败: ${e}`); }
  }

  async function handleExecute() {
    if (!canExecute) return;
    if (!ns.pathText.trim()) { log('❌ 请输入路径'); return; }
    
    ns.phase = 'running'; ns.progress = 0; ns.progressText = '正在处理...'; ns.result = null;
    log(`📂 开始${ns.previewMode ? '预览' : ''}解散文件夹...`);
    
    const taskId = `dissolvef-${nodeId}-${Date.now()}`;
    let ws: WebSocket | null = null;
    
    try {
      const wsUrl = `${getWsBaseUrl()}/v1/ws/tasks/${taskId}`;
      ws = new WebSocket(wsUrl);
      
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'progress') {
            ns.progress = msg.progress;
            ns.progressText = msg.message;
          } else if (msg.type === 'log') {
            log(msg.message);
          }
        } catch (e) { console.error('解析 WebSocket 消息失败:', e); }
      };
      
      await new Promise<void>((resolve) => {
        const timeout = setTimeout(() => resolve(), 2000);
        ws!.onopen = () => { clearTimeout(timeout); resolve(); };
        ws!.onerror = () => { clearTimeout(timeout); resolve(); };
      });
      
      const response = await api.executeNode('dissolvef', {
        action: 'dissolve',
        path: ns.pathText.trim(),
        nested: ns.nestedMode,
        media: ns.mediaMode,
        archive: ns.archiveMode,
        direct: ns.directMode,
        preview: ns.previewMode,
        exclude: ns.excludeKeywords || undefined,
        file_conflict: ns.fileConflict,
        dir_conflict: ns.dirConflict,
        enable_similarity: ns.enableSimilarity,
        similarity_threshold: ns.similarityThreshold
      }, { taskId, nodeId }) as any;
      
      if (response.success) {
        ns.phase = 'completed'; ns.progress = 100; ns.progressText = '处理完成';
        ns.result = {
          success: true,
          nested_count: response.data?.nested_count ?? 0,
          media_count: response.data?.media_count ?? 0,
          archive_count: response.data?.archive_count ?? 0,
          direct_files: response.data?.direct_files ?? 0,
          direct_dirs: response.data?.direct_dirs ?? 0,
          skipped_count: response.data?.skipped_count ?? 0
        };
        log(`✅ ${response.message}`);
        
        // 保存操作记录
        const opId = response.data?.operation_id;
        if (opId && !ns.previewMode) {
          ns.lastOperationId = opId;
          const totalCount = (ns.result.nested_count || 0) + (ns.result.archive_count || 0) + (ns.result.media_count || 0);
          ns.operationHistory = [{
            id: opId,
            timestamp: new Date().toLocaleTimeString(),
            mode: ns.directMode ? 'direct' : (ns.nestedMode ? 'nested' : (ns.archiveMode ? 'archive' : 'media')),
            path: ns.pathText.split(/[/\\]/).pop() || ns.pathText,
            count: totalCount,
            canUndo: true
          }, ...ns.operationHistory].slice(0, 10);
        }
      } else { 
        ns.phase = 'error'; ns.progress = 0; 
        log(`❌ 处理失败: ${response.message}`); 
      }
    } catch (error) { 
      ns.phase = 'error'; ns.progress = 0; 
      log(`❌ 处理失败: ${error}`); 
    } finally {
      if (ws && ws.readyState === WebSocket.OPEN) ws.close();
    }
  }

  async function handleUndo(opId?: string) {
    const targetId = opId || ns.lastOperationId;
    if (!targetId) { log('❌ 无可撤销操作'); return; }
    
    log('🔄 撤销中...');
    try {
      const response = await api.executeNode('dissolvef', {
        action: 'undo',
        undo_id: targetId
      }) as any;
      
      if (response.success) {
        log(`✅ ${response.message}`);
        ns.operationHistory = ns.operationHistory.map(op => 
          op.id === targetId ? { ...op, canUndo: false } : op
        );
        if (targetId === ns.lastOperationId) ns.lastOperationId = '';
        ns.phase = 'idle';
      } else {
        log(`❌ ${response.message}`);
      }
    } catch (e) {
      log(`❌ 撤销失败: ${e}`);
    }
  }

  function handleReset() {
    ns.phase = 'idle'; ns.progress = 0; ns.progressText = '';
    ns.result = null; ns.logs = [];
  }

  async function copyLogs() {
    try { 
      await navigator.clipboard.writeText(ns.logs.join('\n')); 
      copied = true; 
      setTimeout(() => { copied = false; }, 2000); 
    } catch (e) { console.error('复制失败:', e); }
  }

  const conflictOptions = [
    { value: 'auto', label: '自动' },
    { value: 'skip', label: '跳过' },
    { value: 'overwrite', label: '覆盖' },
    { value: 'rename', label: '重命名' }
  ];
</script>


{#snippet sourceBlock()}
  {#if !ns.hasInputConnection}
    <div class="flex flex-col cq-gap h-full">
      <div class="flex cq-gap">
        <Button variant="outline" size="sm" class="cq-button-sm flex-1" onclick={pasteFromClipboard} disabled={isRunning}>
          <Clipboard class="cq-icon mr-1" />剪贴板
        </Button>
        <Button variant="outline" size="sm" class="cq-button-sm flex-1" onclick={selectFolder} disabled={isRunning}>
          <FolderOpen class="cq-icon mr-1" />选择
        </Button>
      </div>
      <Input bind:value={ns.pathText} placeholder="输入文件夹路径" disabled={isRunning} class="cq-text font-mono" />
    </div>
  {:else}
    <div class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-text">
      <span>←</span><span>输入来自上游节点</span>
    </div>
  {/if}
{/snippet}

{#snippet modeBlock()}
  <div class="flex flex-col cq-gap">
    <span class="cq-text-sm text-muted-foreground mb-1">选择解散模式</span>
    <div class="flex items-center cq-gap cursor-pointer" onclick={() => { if (!isRunning && !ns.directMode) ns.nestedMode = !ns.nestedMode; }}>
      <Checkbox checked={ns.nestedMode} disabled={isRunning || ns.directMode} />
      <span class="cq-text">嵌套文件夹</span>
    </div>
    <div class="flex items-center cq-gap cursor-pointer" onclick={() => { if (!isRunning && !ns.directMode) ns.mediaMode = !ns.mediaMode; }}>
      <Checkbox checked={ns.mediaMode} disabled={isRunning || ns.directMode} />
      <span class="cq-text">单媒体文件夹</span>
    </div>
    <div class="flex items-center cq-gap cursor-pointer" onclick={() => { if (!isRunning && !ns.directMode) ns.archiveMode = !ns.archiveMode; }}>
      <Checkbox checked={ns.archiveMode} disabled={isRunning || ns.directMode} />
      <span class="cq-text">单压缩包文件夹</span>
    </div>
    <div class="flex items-center cq-gap cursor-pointer" onclick={() => { if (!isRunning) { ns.directMode = !ns.directMode; if (ns.directMode) { ns.nestedMode = false; ns.mediaMode = false; ns.archiveMode = false; } } }}>
      <Checkbox checked={ns.directMode} disabled={isRunning} />
      <span class="cq-text text-orange-500">直接解散</span>
    </div>
  </div>
{/snippet}

{#snippet optionsBlock()}
  <div class="flex flex-col cq-gap">
    <div class="flex items-center cq-gap cursor-pointer" onclick={() => { if (!isRunning) ns.previewMode = !ns.previewMode; }}>
      <Checkbox checked={ns.previewMode} disabled={isRunning} />
      <span class="cq-text">预览模式</span>
    </div>
    <Input bind:value={ns.excludeKeywords} placeholder="排除关键词(逗号分隔)" disabled={isRunning} class="cq-text-sm" />
    
    <!-- 相似度设置 -->
    {#if !ns.directMode && (ns.nestedMode || ns.archiveMode)}
      <div class="flex flex-col cq-gap mt-1 pt-1 border-t border-border/50">
        <div class="flex items-center cq-gap cursor-pointer" onclick={() => { if (!isRunning) ns.enableSimilarity = !ns.enableSimilarity; }}>
          <Checkbox checked={ns.enableSimilarity} disabled={isRunning} />
          <span class="cq-text">相似度限制</span>
        </div>
        {#if ns.enableSimilarity}
          <div class="flex items-center cq-gap">
            <Slider type="multiple" value={similarityThresholdArr} onValueChange={(v) => ns.similarityThreshold = v[0]} min={0} max={1} step={0.1} disabled={isRunning} class="flex-1" />
            <span class="cq-text-sm text-muted-foreground w-10 text-right">{Math.round(ns.similarityThreshold * 100)}%</span>
          </div>
          <span class="cq-text-sm text-muted-foreground">父文件夹与子项名称相似度需超过此值</span>
        {/if}
      </div>
    {/if}
    
    {#if ns.directMode}
      <div class="flex flex-col cq-gap mt-1">
        <span class="cq-text-sm text-muted-foreground">文件冲突</span>
        <Select.Root type="single" bind:value={ns.fileConflict}>
          <Select.Trigger class="cq-button-sm">
            <span>{conflictOptions.find(o => o.value === ns.fileConflict)?.label ?? '自动'}</span>
          </Select.Trigger>
          <Select.Content>
            {#each conflictOptions as opt}
              <Select.Item value={opt.value}>{opt.label}</Select.Item>
            {/each}
          </Select.Content>
        </Select.Root>
        <span class="cq-text-sm text-muted-foreground">目录冲突</span>
        <Select.Root type="single" bind:value={ns.dirConflict}>
          <Select.Trigger class="cq-button-sm">
            <span>{conflictOptions.find(o => o.value === ns.dirConflict)?.label ?? '自动'}</span>
          </Select.Trigger>
          <Select.Content>
            {#each conflictOptions as opt}
              <Select.Item value={opt.value}>{opt.label}</Select.Item>
            {/each}
          </Select.Content>
        </Select.Root>
      </div>
    {/if}
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if ns.result}
        {#if ns.result.success}
          <CircleCheck class="cq-icon text-green-500 shrink-0" />
          <span class="cq-text text-green-600 font-medium">完成</span>
          {#if ns.result.skipped_count > 0}
            <span class="cq-text-sm text-muted-foreground ml-auto">跳过 {ns.result.skipped_count}</span>
          {/if}
        {:else}
          <CircleX class="cq-icon text-red-500 shrink-0" />
          <span class="cq-text text-red-600 font-medium">失败</span>
        {/if}
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1"><Progress value={ns.progress} class="h-1.5" /></div>
        <span class="cq-text-sm text-muted-foreground">{ns.progress}%</span>
      {:else}
        <FolderInput class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待执行</span>
      {/if}
    </div>
    {#if ns.phase === 'idle' || ns.phase === 'error'}
      <Button class="w-full cq-button flex-1" onclick={handleExecute} disabled={!canExecute}>
        <Play class="cq-icon mr-1" /><span>{ns.previewMode ? '预览' : '执行'}</span>
      </Button>
    {:else if ns.phase === 'running'}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span>处理中</span>
      </Button>
    {:else if ns.phase === 'completed'}
      <Button class="w-full cq-button flex-1" onclick={handleReset}>
        <Play class="cq-icon mr-1" /><span>重新开始</span>
      </Button>
    {/if}
    <Button variant="ghost" class="w-full cq-button-sm" onclick={handleReset} disabled={isRunning}>
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
  </div>
{/snippet}

{#snippet resultBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">处理结果</span>
    </div>
    <div class="flex-1 overflow-y-auto cq-padding bg-muted/30 cq-rounded">
      {#if ns.result}
        <div class="space-y-1 cq-text-sm">
          {#if !ns.directMode}
            {#if ns.nestedMode}
              <div class="flex justify-between"><span>嵌套文件夹</span><span class="text-green-600">{ns.result.nested_count}</span></div>
            {/if}
            {#if ns.mediaMode}
              <div class="flex justify-between"><span>单媒体文件夹</span><span class="text-green-600">{ns.result.media_count}</span></div>
            {/if}
            {#if ns.archiveMode}
              <div class="flex justify-between"><span>单压缩包文件夹</span><span class="text-green-600">{ns.result.archive_count}</span></div>
            {/if}
            {#if ns.result.skipped_count > 0}
              <div class="flex justify-between text-muted-foreground"><span>跳过（相似度不足）</span><span>{ns.result.skipped_count}</span></div>
            {/if}
          {:else}
            <div class="flex justify-between"><span>移动文件</span><span class="text-green-600">{ns.result.direct_files}</span></div>
            <div class="flex justify-between"><span>移动目录</span><span class="text-green-600">{ns.result.direct_dirs}</span></div>
          {/if}
        </div>
      {:else}
        <div class="cq-text text-muted-foreground text-center py-3">暂无结果</div>
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
    <div class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding font-mono cq-text-sm space-y-0.5" style="min-height: 60px;">
      {#if ns.logs.length > 0}
        {#each ns.logs as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet historyBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center gap-2 mb-1 shrink-0">
      <Undo2 class="cq-icon" />
      <span class="cq-text font-semibold">操作历史</span>
    </div>
    <div class="flex-1 overflow-y-auto">
      {#if ns.operationHistory.length > 0}
        {#each ns.operationHistory as op}
          <div class="flex items-center justify-between cq-padding bg-muted/30 cq-rounded mb-1 cq-text-sm">
            <div class="flex flex-col min-w-0 flex-1">
              <span class="truncate">{op.path}</span>
              <span class="text-muted-foreground">{op.timestamp} - {op.count}项</span>
            </div>
            {#if op.canUndo}
              <Button variant="ghost" size="sm" class="h-5 px-2 cq-text-sm shrink-0" onclick={() => handleUndo(op.id)}>
                撤销
              </Button>
            {:else}
              <span class="text-muted-foreground cq-text-sm">已撤销</span>
            {/if}
          </div>
        {/each}
      {:else}
        <div class="cq-text-sm text-muted-foreground text-center py-2">暂无记录</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'source'}{@render sourceBlock()}
  {:else if blockId === 'mode'}{@render modeBlock()}
  {:else if blockId === 'options'}{@render optionsBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'result'}{@render resultBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {:else if blockId === 'history'}{@render historyBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="dissolvef" 
    icon={FolderInput} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="dissolvef" 
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
        nodeType="dissolvef"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={DISSOLVEF_DEFAULT_GRID_LAYOUT}
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
