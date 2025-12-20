<script lang="ts">
  /**
   * SleeptNode - 系统定时器节点组件
   * 支持倒计时、指定时间、网速监控、CPU监控触发电源操作
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Progress } from '$lib/components/ui/progress';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { SLEEPT_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import { getWsBaseUrl } from '$lib/stores/backend';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, Clock, Power, Moon, RotateCcw,
    CircleCheck, CircleX, Copy, Check, Activity, Wifi, Cpu,
    Calendar, Timer, XCircle
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
  type TimerMode = 'countdown' | 'specific_time' | 'netspeed' | 'cpu';
  type PowerMode = 'sleep' | 'shutdown' | 'restart';

  interface SleeptState {
    phase: Phase;
    timerMode: TimerMode;
    powerMode: PowerMode;
    hours: number;
    minutes: number;
    seconds: number;
    targetDatetime: string;
    uploadThreshold: number;
    downloadThreshold: number;
    netDuration: number;
    netTriggerMode: 'both' | 'any';
    cpuThreshold: number;
    cpuDuration: number;
    dryrun: boolean;
  }

  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<SleeptState>(nodeId));
  const dataLogs = $derived(data?.logs ?? []);

  // 状态变量
  let timerMode = $state<TimerMode>('countdown');
  let powerMode = $state<PowerMode>('sleep');
  let hours = $state(0);
  let minutes = $state(0);
  let seconds = $state(5);
  let targetDatetime = $state('');
  let uploadThreshold = $state(242);
  let downloadThreshold = $state(242);
  let netDuration = $state(2);
  let netTriggerMode = $state<'both' | 'any'>('both');
  let cpuThreshold = $state(10);
  let cpuDuration = $state(2);
  let dryrun = $state(true);
  
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let copied = $state(false);
  let progress = $state(0);
  let progressText = $state('');
  let currentUpload = $state(0);
  let currentDownload = $state(0);
  let currentCpu = $state(0);
  let layoutRenderer = $state<any>(undefined);

  let initialized = $state(false);
  
  $effect(() => {
    if (initialized) return;
    
    if (savedState) {
      phase = 'idle'; // 重置状态
      timerMode = savedState.timerMode ?? 'countdown';
      powerMode = savedState.powerMode ?? 'sleep';
      hours = savedState.hours ?? 0;
      minutes = savedState.minutes ?? 0;
      seconds = savedState.seconds ?? 5;
      targetDatetime = savedState.targetDatetime ?? '';
      uploadThreshold = savedState.uploadThreshold ?? 242;
      downloadThreshold = savedState.downloadThreshold ?? 242;
      netDuration = savedState.netDuration ?? 2;
      netTriggerMode = savedState.netTriggerMode ?? 'both';
      cpuThreshold = savedState.cpuThreshold ?? 10;
      cpuDuration = savedState.cpuDuration ?? 2;
      dryrun = savedState.dryrun ?? true;
    }
    
    // 设置默认目标时间为1小时后
    if (!targetDatetime) {
      const d = new Date(Date.now() + 3600000);
      targetDatetime = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:00`;
    }
    
    initialized = true;
  });
  
  $effect(() => { logs = [...dataLogs]; });

  function saveState() {
    if (!initialized) return;
    setNodeState<SleeptState>(nodeId, {
      phase, timerMode, powerMode, hours, minutes, seconds, targetDatetime,
      uploadThreshold, downloadThreshold, netDuration, netTriggerMode,
      cpuThreshold, cpuDuration, dryrun
    });
  }

  let isRunning = $derived(phase === 'running');
  let borderClass = $derived({
    idle: 'border-border', running: 'border-primary shadow-sm',
    completed: 'border-green-500/50', cancelled: 'border-yellow-500/50', error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (timerMode || powerMode || dryrun) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-50), msg]; }

  // 启动定时器
  async function handleStart() {
    if (isRunning) return;
    
    phase = 'running';
    progress = 0;
    progressText = '启动中...';
    log(`⏰ 启动 ${timerMode} 模式`);
    
    const taskId = `sleept-${nodeId}-${Date.now()}`;
    let ws: WebSocket | null = null;
    
    try {
      // 建立 WebSocket 连接
      const wsUrl = `${getWsBaseUrl()}/v1/ws/tasks/${taskId}`;
      ws = new WebSocket(wsUrl);
      
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'progress') {
            progress = msg.progress;
            progressText = msg.message;
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
      
      // 构建参数 - action 直接使用 timerMode
      const params: Record<string, any> = {
        action: timerMode,
        power_mode: powerMode,
        dryrun
      };
      
      if (timerMode === 'countdown') {
        params.hours = hours;
        params.minutes = minutes;
        params.seconds = seconds;
      } else if (timerMode === 'specific_time') {
        params.target_datetime = targetDatetime;
      } else if (timerMode === 'netspeed') {
        params.upload_threshold = uploadThreshold;
        params.download_threshold = downloadThreshold;
        params.net_duration = netDuration;
        params.net_trigger_mode = netTriggerMode;
      } else if (timerMode === 'cpu') {
        params.cpu_threshold = cpuThreshold;
        params.cpu_duration = cpuDuration;
      }
      
      // 发送请求（这个请求会阻塞直到定时器完成）
      const response = await api.executeNode('sleept', params, { taskId, nodeId }) as any;
      
      if (response.success) {
        phase = 'completed';
        progress = 100;
        progressText = '完成';
        log(`✅ ${response.message}`);
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      log(`❌ 执行失败: ${error}`);
    } finally {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    }
  }

  // 重置
  function handleReset() {
    phase = 'idle';
    progress = 0;
    progressText = '';
    logs = [];
  }

  // 获取系统状态
  async function fetchStats() {
    try {
      const response = await api.executeNode('sleept', { action: 'get_stats' }) as any;
      if (response.success) {
        currentUpload = response.current_upload ?? 0;
        currentDownload = response.current_download ?? 0;
        currentCpu = response.current_cpu ?? 0;
      }
    } catch (e) {
      console.error('获取状态失败:', e);
    }
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(logs.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) {
      console.error('复制失败:', e);
    }
  }

  // 预设按钮
  function setPreset(h: number, m: number, s: number) {
    hours = h; minutes = m; seconds = s;
  }
</script>

{#snippet modeBlock()}
  <div class="flex flex-col cq-gap h-full">
    <Label class="cq-text font-medium">计时模式</Label>
    <div class="grid grid-cols-2 cq-gap">
      <Button 
        variant={timerMode === 'countdown' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm"
        onclick={() => timerMode = 'countdown'}
        disabled={isRunning}
      >
        <Timer class="cq-icon mr-1" />倒计时
      </Button>
      <Button 
        variant={timerMode === 'specific_time' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm"
        onclick={() => timerMode = 'specific_time'}
        disabled={isRunning}
      >
        <Calendar class="cq-icon mr-1" />指定时间
      </Button>
      <Button 
        variant={timerMode === 'netspeed' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm"
        onclick={() => timerMode = 'netspeed'}
        disabled={isRunning}
      >
        <Wifi class="cq-icon mr-1" />网速监控
      </Button>
      <Button 
        variant={timerMode === 'cpu' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm"
        onclick={() => timerMode = 'cpu'}
        disabled={isRunning}
      >
        <Cpu class="cq-icon mr-1" />CPU监控
      </Button>
    </div>
    
    <Label class="cq-text font-medium mt-2">电源操作</Label>
    <div class="flex cq-gap">
      <Button 
        variant={powerMode === 'sleep' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm flex-1"
        onclick={() => powerMode = 'sleep'}
        disabled={isRunning}
      >
        <Moon class="cq-icon mr-1" />休眠
      </Button>
      <Button 
        variant={powerMode === 'shutdown' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm flex-1"
        onclick={() => powerMode = 'shutdown'}
        disabled={isRunning}
      >
        <Power class="cq-icon mr-1" />关机
      </Button>
      <Button 
        variant={powerMode === 'restart' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm flex-1"
        onclick={() => powerMode = 'restart'}
        disabled={isRunning}
      >
        <RotateCcw class="cq-icon mr-1" />重启
      </Button>
    </div>
    
    <label class="flex items-center cq-gap cursor-pointer mt-2">
      <Checkbox bind:checked={dryrun} disabled={isRunning} />
      <span class="cq-text">演练模式（不实际执行）</span>
    </label>
  </div>
{/snippet}

{#snippet timerBlock()}
  <div class="flex flex-col cq-gap h-full">
    {#if timerMode === 'countdown'}
      <Label class="cq-text font-medium">倒计时设置</Label>
      <div class="flex cq-gap items-center">
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">时</Label>
          <Input type="number" bind:value={hours} min={0} max={23} disabled={isRunning} class="cq-text" />
        </div>
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">分</Label>
          <Input type="number" bind:value={minutes} min={0} max={59} disabled={isRunning} class="cq-text" />
        </div>
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">秒</Label>
          <Input type="number" bind:value={seconds} min={0} max={59} disabled={isRunning} class="cq-text" />
        </div>
      </div>
      <div class="grid grid-cols-4 cq-gap">
        <Button variant="outline" size="sm" class="cq-button-sm" onclick={() => setPreset(0, 0, 5)} disabled={isRunning}>5秒</Button>
        <Button variant="outline" size="sm" class="cq-button-sm" onclick={() => setPreset(0, 5, 0)} disabled={isRunning}>5分</Button>
        <Button variant="outline" size="sm" class="cq-button-sm" onclick={() => setPreset(0, 30, 0)} disabled={isRunning}>30分</Button>
        <Button variant="outline" size="sm" class="cq-button-sm" onclick={() => setPreset(1, 0, 0)} disabled={isRunning}>1时</Button>
      </div>
    {:else if timerMode === 'specific_time'}
      <Label class="cq-text font-medium">目标时间</Label>
      <Input type="text" bind:value={targetDatetime} placeholder="YYYY-MM-DD HH:MM:SS" disabled={isRunning} class="cq-text font-mono" />
      <span class="cq-text-sm text-muted-foreground">格式: 2024-12-21 23:30:00</span>
    {:else}
      <div class="flex items-center justify-center h-full text-muted-foreground cq-text">
        请在监控设置中配置参数
      </div>
    {/if}
  </div>
{/snippet}

{#snippet monitorBlock()}
  <div class="flex flex-col cq-gap h-full">
    {#if timerMode === 'netspeed'}
      <Label class="cq-text font-medium">网速监控设置</Label>
      <div class="flex cq-gap items-center">
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">上传阈值(KB/s)</Label>
          <Input type="number" bind:value={uploadThreshold} min={0} disabled={isRunning} class="cq-text" />
        </div>
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">下载阈值(KB/s)</Label>
          <Input type="number" bind:value={downloadThreshold} min={0} disabled={isRunning} class="cq-text" />
        </div>
      </div>
      <div class="flex cq-gap items-center">
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">持续时间(分钟)</Label>
          <Input type="number" bind:value={netDuration} min={0.5} step={0.5} disabled={isRunning} class="cq-text" />
        </div>
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">触发条件</Label>
          <div class="flex cq-gap">
            <Button variant={netTriggerMode === 'both' ? 'default' : 'outline'} size="sm" class="cq-button-sm flex-1" onclick={() => netTriggerMode = 'both'} disabled={isRunning}>都低于</Button>
            <Button variant={netTriggerMode === 'any' ? 'default' : 'outline'} size="sm" class="cq-button-sm flex-1" onclick={() => netTriggerMode = 'any'} disabled={isRunning}>任一</Button>
          </div>
        </div>
      </div>
      <div class="cq-padding bg-muted/30 cq-rounded cq-text-sm">
        <div class="flex justify-between"><span>当前上传:</span><span>{currentUpload.toFixed(1)} KB/s</span></div>
        <div class="flex justify-between"><span>当前下载:</span><span>{currentDownload.toFixed(1)} KB/s</span></div>
      </div>
    {:else if timerMode === 'cpu'}
      <Label class="cq-text font-medium">CPU监控设置</Label>
      <div class="flex cq-gap items-center">
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">CPU阈值(%)</Label>
          <Input type="number" bind:value={cpuThreshold} min={1} max={100} disabled={isRunning} class="cq-text" />
        </div>
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">持续时间(分钟)</Label>
          <Input type="number" bind:value={cpuDuration} min={0.5} step={0.5} disabled={isRunning} class="cq-text" />
        </div>
      </div>
      <div class="cq-padding bg-muted/30 cq-rounded">
        <div class="flex justify-between cq-text-sm"><span>当前CPU:</span><span>{currentCpu.toFixed(1)}%</span></div>
        <Progress value={currentCpu} max={100} class="h-2 mt-1" />
      </div>
      <span class="cq-text-sm text-muted-foreground">当CPU使用率低于阈值持续指定时间后触发</span>
    {:else}
      <div class="flex flex-col items-center justify-center h-full text-muted-foreground cq-text cq-gap">
        <Activity class="w-8 h-8 opacity-50" />
        <span>当前模式无需监控设置</span>
        <div class="cq-padding bg-muted/30 cq-rounded w-full">
          <div class="flex justify-between cq-text-sm"><span>CPU:</span><span>{currentCpu.toFixed(1)}%</span></div>
          <div class="flex justify-between cq-text-sm"><span>上传:</span><span>{currentUpload.toFixed(1)} KB/s</span></div>
          <div class="flex justify-between cq-text-sm"><span>下载:</span><span>{currentDownload.toFixed(1)} KB/s</span></div>
        </div>
      </div>
    {/if}
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if phase === 'completed'}
        <CircleCheck class="cq-icon text-green-500 shrink-0" />
        <span class="cq-text text-green-600 font-medium">已完成</span>
      {:else if phase === 'cancelled'}
        <XCircle class="cq-icon text-yellow-500 shrink-0" />
        <span class="cq-text text-yellow-600 font-medium">已取消</span>
      {:else if phase === 'error'}
        <CircleX class="cq-icon text-red-500 shrink-0" />
        <span class="cq-text text-red-600 font-medium">错误</span>
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1 flex flex-col cq-gap">
          <Progress value={progress} class="h-1.5" />
          <span class="cq-text-sm text-muted-foreground truncate">{progressText}</span>
        </div>
      {:else}
        <Clock class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待启动</span>
      {/if}
    </div>
    
    {#if phase === 'idle' || phase === 'error' || phase === 'cancelled' || phase === 'completed'}
      <Button class="w-full cq-button flex-1" onclick={handleStart} disabled={isRunning}>
        <Play class="cq-icon mr-1" /><span>开始</span>
      </Button>
    {:else}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span>运行中...</span>
      </Button>
    {/if}
    
    <Button variant="ghost" class="w-full cq-button-sm" onclick={handleReset} disabled={isRunning}>
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
    <Button variant="ghost" class="w-full cq-button-sm" onclick={fetchStats}>
      <Activity class="cq-icon mr-1" />刷新状态
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
      {#if logs.length > 0}
        {#each logs.slice(-15) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'mode'}{@render modeBlock()}
  {:else if blockId === 'timer'}{@render timerBlock()}
  {:else if blockId === 'monitor'}{@render monitorBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 450px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={320} minHeight={280} maxWidth={450} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="sleept" 
    icon={Clock} 
    status={phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="sleept" 
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
        nodeType="sleept"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={SLEEPT_DEFAULT_GRID_LAYOUT}
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
