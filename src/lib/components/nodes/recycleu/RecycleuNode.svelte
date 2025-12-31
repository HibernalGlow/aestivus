<script lang="ts">
  /**
   * RecycleuNode - 回收站自动清理节点
   * 
   * 功能：定时自动清空 Windows 回收站
   * 支持设置清理间隔、启动/停止控制、立即清空
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Progress } from '$lib/components/ui/progress';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { RECYCLEU_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, saveNodeState } from '$lib/stores/nodeState.svelte';
  import { getWsBaseUrl } from '$lib/stores/backend';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, Trash2, RotateCcw,
    CircleCheck, CircleX, Copy, Check, Square, Clock
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: Record<string, any>;
      status?: 'idle' | 'running' | 'completed' | 'error';
      logs?: string[];
      label?: string;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'running' | 'completed' | 'cancelled' | 'error';

  interface RecycleuState {
    interval: number;
    cleanCount: number;
    lastCleanTime: string | null;
    // 运行时状态
    phase: Phase;
    logs: string[];
    progress: number;
    progressText: string;
    remainingSeconds: number;
    countdownProgress: number;
  }

  const nodeId = $derived(id);
  const dataLogs = $derived(data?.logs ?? []);

  // 获取共享的响应式状态（节点模式和全屏模式共用同一个对象）
  const ns = getNodeState<RecycleuState>(id, {
    interval: 10,
    cleanCount: 0,
    lastCleanTime: null,
    phase: 'idle',
    logs: [],
    progress: 0,
    progressText: '',
    remainingSeconds: 0,
    countdownProgress: 100
  });

  // 本地 UI 状态（不需要跨实例同步）
  let copied = $state(false);
  let layoutRenderer = $state<any>(undefined);
  
  // WebSocket 和取消控制
  let ws: WebSocket | null = null;
  let abortController: AbortController | null = null;

  // 同步 data.logs
  $effect(() => { 
    if (dataLogs.length > 0) {
      ns.logs = [...dataLogs]; 
    }
  });

  // 派生状态
  let isRunning = $derived(ns.phase === 'running');
  let canStart = $derived(ns.phase === 'idle' || ns.phase === 'error' || ns.phase === 'cancelled' || ns.phase === 'completed');
  let borderClass = $derived({
    idle: 'border-border', 
    running: 'border-primary shadow-sm',
    completed: 'border-green-500/50', 
    cancelled: 'border-yellow-500/50', 
    error: 'border-destructive/50'
  }[ns.phase]);

  // 配置变更时自动保存
  $effect(() => { 
    ns.interval; ns.cleanCount;
    saveNodeState(nodeId); 
  });

  function log(msg: string) { ns.logs = [...ns.logs.slice(-50), msg]; }

  // 启动自动清理
  async function handleStart() {
    if (isRunning) return;
    
    ns.phase = 'running';
    ns.progress = 0;
    ns.progressText = '启动中...';
    ns.cleanCount = 0;
    ns.countdownProgress = 100; // 初始化为满圆
    ns.remainingSeconds = ns.interval;
    log(`🚀 启动自动清理，间隔 ${ns.interval} 秒`);
    
    const taskId = `recycleu-${nodeId}-${Date.now()}`;
    abortController = new AbortController();
    
    try {
      // 建立 WebSocket 连接
      const wsUrl = `${getWsBaseUrl()}/v1/ws/tasks/${taskId}`;
      ws = new WebSocket(wsUrl);
      
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'progress') {
            ns.progress = msg.progress;
            ns.progressText = msg.message;
            // 解析清理次数
            const countMatch = msg.message.match(/已清理 (\d+) 次/);
            if (countMatch) ns.cleanCount = parseInt(countMatch[1]);
            // 解析剩余秒数并计算倒计时进度
            const secMatch = msg.message.match(/(\d+)s 后清理/);
            if (secMatch) {
              ns.remainingSeconds = parseInt(secMatch[1]);
              // 倒计时进度：从满圆(100%)减少到空(0%)
              ns.countdownProgress = (ns.remainingSeconds / ns.interval) * 100;
            }
          } else if (msg.type === 'log') {
            log(msg.message);
          }
        } catch (e) {
          console.error('解析消息失败:', e);
        }
      };
      
      // 等待连接
      await new Promise<void>((resolve) => {
        const timeout = setTimeout(resolve, 1000);
        ws!.onopen = () => { clearTimeout(timeout); resolve(); };
        ws!.onerror = () => { clearTimeout(timeout); resolve(); };
      });
      
      const response = await api.executeNode('recycleu', {
        action: 'start',
        interval: ns.interval
      }, { taskId, nodeId }) as any;
      
      if (response.success) {
        ns.phase = 'completed';
        ns.progress = 100;
        ns.progressText = '完成';
        ns.cleanCount = response.clean_count ?? ns.cleanCount;
        ns.lastCleanTime = response.last_clean_time ?? null;
        log(`✅ ${response.message}`);
      } else {
        ns.phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        ns.phase = 'cancelled';
        log('⏹️ 已停止');
      } else {
        ns.phase = 'error';
        log(`❌ 执行失败: ${error}`);
      }
    } finally {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
      ws = null;
      abortController = null;
    }
  }

  // 停止
  function handleStop() {
    if (abortController) {
      abortController.abort();
    }
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
    ns.phase = 'cancelled';
    log('⏹️ 已停止');
  }

  // 立即清空
  async function handleCleanNow() {
    log('🗑️ 立即清空回收站...');
    try {
      const response = await api.executeNode('recycleu', { 
        action: 'clean_now'
      }) as any;
      
      if (response.success) {
        ns.cleanCount = response.clean_count ?? ns.cleanCount + 1;
        ns.lastCleanTime = response.last_clean_time ?? new Date().toLocaleTimeString();
        log(`✅ ${response.message}`);
      } else { 
        log(`❌ ${response.message}`); 
      }
    } catch (error) { 
      log(`❌ 清理失败: ${error}`); 
    }
  }

  // 重置
  function handleReset() {
    if (isRunning) {
      handleStop();
    }
    ns.phase = 'idle';
    ns.progress = 0;
    ns.progressText = '';
    ns.cleanCount = 0;
    ns.lastCleanTime = null;
    ns.logs = [];
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(ns.logs.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) {
      console.error('复制失败:', e);
    }
  }

  function setPreset(sec: number) {
    ns.interval = sec;
  }
</script>

{#snippet settingsBlock()}
  <div class="flex flex-col cq-gap h-full">
    <Label class="cq-text font-medium">清理间隔（秒）</Label>
    <div class="flex cq-gap items-center">
      <Input 
        type="number" 
        bind:value={ns.interval} 
        min={5} 
        max={300} 
        disabled={isRunning} 
        class="cq-text flex-1" 
      />
    </div>
    <div class="grid grid-cols-4 cq-gap">
      <Button variant="outline" size="sm" class="cq-button-sm" onclick={() => setPreset(5)} disabled={isRunning}>5s</Button>
      <Button variant="outline" size="sm" class="cq-button-sm" onclick={() => setPreset(10)} disabled={isRunning}>10s</Button>
      <Button variant="outline" size="sm" class="cq-button-sm" onclick={() => setPreset(30)} disabled={isRunning}>30s</Button>
      <Button variant="outline" size="sm" class="cq-button-sm" onclick={() => setPreset(60)} disabled={isRunning}>1m</Button>
    </div>
    <Button 
      variant="outline" 
      class="w-full cq-button mt-auto" 
      onclick={handleCleanNow}
      disabled={isRunning}
    >
      <Trash2 class="cq-icon mr-1" />立即清空
    </Button>
  </div>
{/snippet}

{#snippet statusBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 圆形倒计时进度 -->
    <div class="flex-1 flex flex-col items-center justify-center">
      <div class="relative w-24 h-24">
        <!-- 背景圆 -->
        <svg class="w-full h-full -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" stroke-width="8" class="text-muted/30" />
          <!-- 倒计时圆环：从满圆减少到单点 -->
          <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" stroke-width="8" 
            class={ns.phase === 'completed' ? 'text-green-500' : ns.phase === 'error' ? 'text-red-500' : 'text-primary'}
            stroke-dasharray={`${ns.countdownProgress * 2.83} 283`}
            stroke-linecap="round" />
        </svg>
        <!-- 中心文字 -->
        <div class="absolute inset-0 flex flex-col items-center justify-center">
          {#if isRunning}
            <span class="text-lg font-mono font-bold">{ns.remainingSeconds}s</span>
            <span class="cq-text-sm text-muted-foreground">{ns.cleanCount}次</span>
          {:else if ns.phase === 'completed'}
            <CircleCheck class="w-8 h-8 text-green-500" />
          {:else if ns.phase === 'error'}
            <CircleX class="w-8 h-8 text-red-500" />
          {:else}
            <Trash2 class="w-8 h-8 text-muted-foreground/50" />
          {/if}
        </div>
      </div>
      <span class="cq-text text-muted-foreground mt-2">{ns.progressText || '等待启动'}</span>
    </div>
    
    <!-- 统计 -->
    <div class="grid grid-cols-2 cq-gap">
      <div class="bg-muted/30 rounded cq-padding text-center">
        <div class="cq-stat-value text-primary tabular-nums">{ns.cleanCount}</div>
        <div class="cq-text-sm text-muted-foreground">清理次数</div>
      </div>
      <div class="bg-muted/30 rounded cq-padding text-center">
        <div class="cq-stat-value text-cyan-500 tabular-nums text-xs">{ns.lastCleanTime ?? '-'}</div>
        <div class="cq-text-sm text-muted-foreground">上次清理</div>
      </div>
    </div>
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    {#if canStart}
      <Button class="w-full cq-button flex-1" onclick={handleStart}>
        <Play class="cq-icon mr-1" />开始
      </Button>
    {:else}
      <Button class="w-full cq-button flex-1" variant="destructive" onclick={handleStop}>
        <Square class="cq-icon mr-1" />停止
      </Button>
    {/if}
    
    <Button variant="outline" class="w-full cq-button-sm" onclick={handleReset}>
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
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
  {#if blockId === 'settings'}{@render settingsBlock()}
  {:else if blockId === 'status'}{@render statusBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 420px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={320} minHeight={280} maxWidth={420} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="recycleu" 
    icon={Trash2} 
    status={ns.phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="recycleu" 
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
        nodeType="recycleu"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={RECYCLEU_DEFAULT_GRID_LAYOUT}
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
