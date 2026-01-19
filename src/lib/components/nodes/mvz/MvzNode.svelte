<script lang="ts">
  /**
   * MvzNode - 压缩包文件操作节点
   * 支持删除、提取、移动、重命名压缩包内的文件
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import * as Select from '$lib/components/ui/select';
  import { onDestroy } from 'svelte';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import type { GridItem } from '$lib/components/ui/dashboard-grid';
  import { MVZ_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState } from '$lib/stores/nodeState.svelte';
  import { getWsBaseUrl } from '$lib/stores/backend';
  import NodeWrapper from '../NodeWrapper.svelte';
  import type { MvzNodeState, MvzAction } from './types';
  import { 
    Package, LoaderCircle, Trash2, Download, Move, Edit3, 
    CircleCheck, CircleX, Copy, Check, RotateCcw, FileText, Clipboard, Plus, X
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: any;
      status?: 'idle' | 'running' | 'completed' | 'error';
      hasInputConnection?: boolean;
      logs?: string[];
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  const nodeId = $derived(id);
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 获取共享的响应式状态
  const ns = getNodeState<MvzNodeState>(id, {
    phase: 'idle',
    progress: 0,
    action: 'extract',
    files: [],
    output: '.',
    near: false,
    autoDir: false,
    flatten: false,
    pattern: '',
    replacement: '',
    dryRun: false,
    logs: [],
    totalFiles: 0,
    totalArchives: 0,
    successCount: 0,
    failedCount: 0,
    results: [],
    preview: []
  });

  let hasInputConnection = $state(false);
  let layoutRenderer = $state<any>(undefined);
  let fileInput = $state('');
  let copiedLogs = $state(false);

  // WebSocket 连接
  let ws: WebSocket | null = null;

  $effect(() => {
    if (dataLogs.length > 0) ns.logs = [...dataLogs];
    hasInputConnection = dataHasInputConnection;
  });

  function connectWebSocket(tid: string) {
    if (ws) ws.close();
    const wsUrl = `${getWsBaseUrl()}/v1/ws/tasks/${tid}`;
    ws = new WebSocket(wsUrl);
    ws.onopen = () => log('📡 WebSocket 已连接');
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'progress') {
          ns.progress = msg.progress;
        } else if (msg.type === 'log') {
          log(msg.message);
        } else if (msg.type === 'status') {
          if (msg.status === 'completed') {
            ns.phase = 'completed';
            ns.progress = 100;
          } else if (msg.status === 'error') {
            ns.phase = 'error';
          }
        }
      } catch (e) {
        console.error('WebSocket 消息解析失败:', e);
      }
    };
    ws.onerror = (error) => console.error('WebSocket 错误:', error);
    ws.onclose = () => { ws = null; };
  }

  function disconnectWebSocket() {
    if (ws) {
      ws.close();
      ws = null;
    }
  }

  onDestroy(() => disconnectWebSocket());

  let canExecute = $derived(ns.phase === 'idle' && ns.files.length > 0);
  let isRunning = $derived(ns.phase === 'processing');
  let borderClass = $derived({
    idle: 'border-border',
    processing: 'border-blue-500 shadow-sm',
    completed: 'border-primary/50',
    error: 'border-destructive/50'
  }[ns.phase]);

  function log(msg: string) { ns.logs = [...ns.logs.slice(-30), msg]; }

  // 添加文件
  function addFile() {
    const text = fileInput.trim();
    if (!text) return;
    
    // 支持多行粘贴
    const lines = text.split(/\r?\n/).map(l => l.trim()).filter(l => l);
    let added = 0;
    for (const line of lines) {
      if (line.includes('//') && !ns.files.includes(line)) {
        ns.files = [...ns.files, line];
        added++;
      }
    }
    
    if (added > 0) {
      log(`➕ 添加了 ${added} 个文件`);
    }
    fileInput = '';
  }

  // 从剪贴板粘贴
  async function pasteFromClipboard() {
    try {
      const { platform } = await import('$lib/api/platform');
      const text = await platform.readClipboard();
      if (text) {
        fileInput = text.trim();
      }
    } catch (e) { log(`读取剪贴板失败: ${e}`); }
  }

  // 移除文件
  function removeFile(index: number) {
    ns.files = ns.files.filter((_, i) => i !== index);
  }

  // 清空文件
  function clearFiles() {
    ns.files = [];
  }

  // 执行操作
  async function execute() {
    if (!canExecute) return;
    ns.phase = 'processing';
    ns.progress = 0;
    ns.results = [];
    ns.preview = [];

    const newTaskId = `mvz-${nodeId}-${Date.now()}`;
    connectWebSocket(newTaskId);

    log(`🚀 开始执行 ${ns.action} 操作...`);

    try {
      const response = await api.executeNode('mvz', {
        action: ns.action,
        files: ns.files,
        output: ns.output,
        near: ns.near,
        auto_dir: ns.autoDir,
        flatten: ns.flatten,
        pattern: ns.pattern,
        replacement: ns.replacement,
        dry_run: ns.dryRun
      }, { taskId: newTaskId, nodeId }) as any;

      if (response.logs) for (const m of response.logs) log(m);

      if (response.success) {
        ns.phase = 'completed';
        ns.progress = 100;
        ns.totalFiles = response.total_files || 0;
        ns.totalArchives = response.total_archives || 0;
        ns.successCount = response.success_count || 0;
        ns.failedCount = response.failed_count || 0;
        ns.results = response.results || [];
        ns.preview = response.preview || [];
        log(`✅ ${response.message}`);
      } else {
        ns.phase = 'error';
        ns.progress = 0;
        log(`❌ 失败: ${response.message}`);
      }
    } catch (error) {
      ns.phase = 'error';
      ns.progress = 0;
      log(`❌ 失败: ${error}`);
    } finally {
      setTimeout(() => disconnectWebSocket(), 1000);
    }
  }

  function handleReset() {
    ns.phase = 'idle';
    ns.progress = 0;
    ns.results = [];
    ns.preview = [];
    ns.logs = [];
  }

  async function copyToClipboard(text: string, setter: (v: boolean) => void) {
    try {
      await navigator.clipboard.writeText(text);
      setter(true);
      setTimeout(() => setter(false), 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  // 操作选项
  const actions: Array<{ value: MvzAction; label: string; icon: any }> = [
    { value: 'extract', label: '提取', icon: Download },
    { value: 'delete', label: '删除', icon: Trash2 },
    { value: 'move', label: '移动', icon: Move },
    { value: 'rename', label: '重命名', icon: Edit3 }
  ];
</script>

<!-- 输入文件 -->
{#snippet inputBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center gap-1 mb-1 cq-text">
      <FileText class="cq-icon" />
      <span class="font-medium">输入文件</span>
      {#if ns.files.length > 0}
        <span class="text-xs text-muted-foreground">({ns.files.length})</span>
      {/if}
    </div>
    
    <!-- 文件输入框 -->
    <div class="flex flex-col cq-gap mb-1">
      <textarea
        bind:value={fileInput}
        placeholder="粘贴文件路径（archive//internal 格式）..."
        disabled={isRunning}
        class="flex-1 cq-input resize-none"
        rows="2"
        onkeydown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            addFile();
          }
        }}
      />
      <div class="flex cq-gap">
        <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={addFile} disabled={isRunning || !fileInput.trim()} title="添加文件">
          <Plus class="cq-icon" />
        </Button>
        <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={pasteFromClipboard} disabled={isRunning} title="从剪贴板粘贴">
          <Clipboard class="cq-icon" />
        </Button>
        <Button variant="outline" size="icon" class="cq-button-icon shrink-0" onclick={clearFiles} disabled={isRunning || ns.files.length === 0} title="清空所有文件">
          <Trash2 class="cq-icon" />
        </Button>
      </div>
    </div>

    <!-- 文件列表 -->
    {#if ns.files.length > 0}
      <div class="flex-1 overflow-y-auto space-y-0.5 cq-padding bg-muted/30 cq-rounded">
        {#each ns.files as file, index}
          <div class="flex items-center gap-1 cq-text-sm bg-background cq-rounded px-1.5 py-0.5 group">
            <Package class="w-3 h-3 text-purple-500 shrink-0" />
            <span class="flex-1 truncate font-mono text-xs" title={file}>{file}</span>
            <button onclick={() => removeFile(index)} disabled={isRunning} class="opacity-0 group-hover:opacity-100">
              <X class="w-3 h-3 text-muted-foreground hover:text-destructive" />
            </button>
          </div>
        {/each}
      </div>
    {:else}
      <div class="cq-text-sm text-muted-foreground text-center py-4 bg-muted/30 cq-rounded">
        从 findz 输出粘贴文件路径
      </div>
    {/if}
  </div>
{/snippet}

<!-- 操作配置 -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 操作类型 -->
    <div>
      <label class="cq-text-sm font-medium mb-1 block">操作类型</label>
      <div class="grid grid-cols-2 gap-1">
        {#each actions as act}
          <button
            class="flex items-center gap-1 px-2 py-1.5 rounded text-xs transition-colors
              {ns.action === act.value ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/80'}"
            onclick={() => ns.action = act.value}
            disabled={isRunning}
          >
            <act.icon class="w-3 h-3" />
            {act.label}
          </button>
        {/each}
      </div>
    </div>

    <!-- 提取/移动选项 -->
    {#if ns.action === 'extract' || ns.action === 'move'}
      <div class="space-y-1">
        <Input bind:value={ns.output} placeholder="输出目录" disabled={isRunning} class="cq-input" />
        <div class="flex items-center gap-2 text-xs">
          <label class="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" bind:checked={ns.near} disabled={isRunning} class="w-3 h-3" />
            <span>就近提取</span>
          </label>
          <label class="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" bind:checked={ns.autoDir} disabled={isRunning} class="w-3 h-3" />
            <span>自动目录</span>
          </label>
          <label class="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" bind:checked={ns.flatten} disabled={isRunning} class="w-3 h-3" />
            <span>扁平化</span>
          </label>
        </div>
      </div>
    {/if}

    <!-- 重命名选项 -->
    {#if ns.action === 'rename'}
      <div class="space-y-1">
        <Input bind:value={ns.pattern} placeholder="正则模式" disabled={isRunning} class="cq-input" />
        <Input bind:value={ns.replacement} placeholder="替换为" disabled={isRunning} class="cq-input" />
      </div>
    {/if}

    <!-- 预览模式 -->
    <label class="flex items-center gap-2 cursor-pointer cq-text-sm">
      <input type="checkbox" bind:checked={ns.dryRun} disabled={isRunning} class="w-3.5 h-3.5" />
      <span>预览模式（不实际执行）</span>
    </label>

    <!-- 执行按钮 -->
    <Button class="w-full cq-button" onclick={execute} disabled={!canExecute || isRunning}>
      {#if isRunning}<LoaderCircle class="cq-icon mr-1 animate-spin" />{:else}<Package class="cq-icon mr-1" />{/if}
      <span>执行</span>
    </Button>
  </div>
{/snippet}

<!-- 统计 -->
{#snippet statsBlock()}
  {#if ns.phase === 'completed'}
    <div class="grid grid-cols-2 cq-gap">
      <div class="cq-stat-card bg-blue-500/10">
        <div class="cq-stat-label text-muted-foreground">总文件</div>
        <div class="cq-stat-value text-blue-600 tabular-nums">{ns.totalFiles}</div>
      </div>
      <div class="cq-stat-card bg-purple-500/10">
        <div class="cq-stat-label text-muted-foreground">压缩包</div>
        <div class="cq-stat-value text-purple-600 tabular-nums">{ns.totalArchives}</div>
      </div>
      <div class="cq-stat-card bg-green-500/10">
        <div class="cq-stat-label text-muted-foreground">成功</div>
        <div class="cq-stat-value text-green-600 tabular-nums">{ns.successCount}</div>
      </div>
      <div class="cq-stat-card bg-red-500/10">
        <div class="cq-stat-label text-muted-foreground">失败</div>
        <div class="cq-stat-value text-red-600 tabular-nums">{ns.failedCount}</div>
      </div>
    </div>
  {:else}
    <div class="cq-text text-muted-foreground text-center py-2">执行后显示统计</div>
  {/if}
{/snippet}

<!-- 结果 -->
{#snippet resultsBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0">
      <span class="cq-text font-semibold">
        {ns.dryRun ? '预览' : '结果'}
      </span>
      <span class="cq-text-sm text-muted-foreground">
        {ns.dryRun ? ns.preview.length : ns.results.length} 项
      </span>
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
      {#if ns.dryRun && ns.preview.length > 0}
        <div class="space-y-2">
          {#each ns.preview as item}
            <div class="cq-padding bg-muted/30 cq-rounded">
              <div class="cq-text-sm font-medium truncate">{item.archive}</div>
              {#if item.output}
                <div class="cq-text-sm text-muted-foreground">→ {item.output}</div>
              {/if}
              <div class="cq-text-sm text-muted-foreground">{item.count} 个文件</div>
            </div>
          {/each}
        </div>
      {:else if ns.results.length > 0}
        <div class="space-y-2">
          {#each ns.results as result}
            <div class="cq-padding bg-muted/30 cq-rounded">
              <div class="flex items-center gap-1">
                {#if result.success}
                  <CircleCheck class="w-3 h-3 text-green-500 shrink-0" />
                {:else}
                  <CircleX class="w-3 h-3 text-red-500 shrink-0" />
                {/if}
                <span class="cq-text-sm font-medium truncate flex-1">{result.archive}</span>
              </div>
              <div class="cq-text-sm text-muted-foreground mt-0.5">{result.message}</div>
            </div>
          {/each}
        </div>
      {:else}
        <div class="cq-text text-muted-foreground text-center py-4">执行后显示结果</div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 日志 -->
{#snippet logBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">日志</span>
      <Button variant="ghost" size="icon" class="h-5 w-5" onclick={() => copyToClipboard(ns.logs.join('\n'), v => copiedLogs = v)}>
        {#if copiedLogs}<Check class="w-3 h-3 text-green-500" />{:else}<Copy class="w-3 h-3" />{/if}
      </Button>
    </div>
    <div class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding font-mono cq-text-sm space-y-0.5">
      {#if ns.logs.length > 0}
        {#each ns.logs.slice(-10) as logItem}
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
  {#if blockId === 'input'}{@render inputBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'stats'}{@render statsBlock()}
  {:else if blockId === 'results'}{@render resultsBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<!-- 主渲染 -->
<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 420px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={300} minHeight={400} maxWidth={420} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="mvz" 
    icon={Package} 
    status={ns.phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="mvz" 
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
        nodeType="mvz"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={MVZ_DEFAULT_GRID_LAYOUT}
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
