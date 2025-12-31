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
  import { getNodeState, saveNodeState } from '$lib/stores/nodeState.svelte';
  import { getWsBaseUrl } from '$lib/stores/backend';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, Clock, Power, Moon, RotateCcw,
    CircleCheck, CircleX, Copy, Check, Activity, Wifi, Cpu,
    Calendar, Timer, XCircle, Pause, Square
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

  type Phase = 'idle' | 'running' | 'paused' | 'completed' | 'cancelled' | 'error';
  type TimerMode = 'countdown' | 'specific_time' | 'netspeed' | 'cpu';
  type PowerMode = 'sleep' | 'shutdown' | 'restart';

  interface SleeptState {
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
    // 运行时状态
    phase: Phase;
    logs: string[];
    progress: number;
    progressText: string;
    remainingTime: string;
    currentUpload: number;
    currentDownload: number;
    currentCpu: number;
    netHistory: {time: number, up: number, down: number}[];
    cpuHistory: number[];
  }

  const nodeId = $derived(id);
  const dataLogs = $derived(data?.logs ?? []);

  // 初始化默认目标时间
  function getDefaultTargetDatetime(): string {
    const d = new Date(Date.now() + 3600000);
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:00`;
  }

  // 获取共享的响应式状态（节点模式和全屏模式共用同一个对象）
  const ns = getNodeState<SleeptState>(id, {
    timerMode: 'countdown',
    powerMode: 'sleep',
    hours: 0,
    minutes: 0,
    seconds: 5,
    targetDatetime: getDefaultTargetDatetime(),
    uploadThreshold: 242,
    downloadThreshold: 242,
    netDuration: 2,
    netTriggerMode: 'both',
    cpuThreshold: 10,
    cpuDuration: 2,
    dryrun: true,
    phase: 'idle',
    logs: [],
    progress: 0,
    progressText: '',
    remainingTime: '00:00:00',
    currentUpload: 0,
    currentDownload: 0,
    currentCpu: 0,
    netHistory: [],
    cpuHistory: []
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
  let isPaused = $derived(ns.phase === 'paused');
  let canStart = $derived(ns.phase === 'idle' || ns.phase === 'error' || ns.phase === 'cancelled' || ns.phase === 'completed');
  let borderClass = $derived({
    idle: 'border-border', running: 'border-primary shadow-sm', paused: 'border-yellow-500 shadow-sm',
    completed: 'border-green-500/50', cancelled: 'border-yellow-500/50', error: 'border-destructive/50'
  }[ns.phase]);

  // 配置变更时自动保存
  $effect(() => { 
    ns.timerMode; ns.powerMode; ns.dryrun;
    ns.hours; ns.minutes; ns.seconds;
    saveNodeState(nodeId); 
  });

  function log(msg: string) { ns.logs = [...ns.logs.slice(-50), msg]; }

  // 启动定时器
  async function handleStart() {
    if (isRunning) return;
    
    ns.phase = 'running';
    ns.progress = 0;
    ns.progressText = '启动中...';
    ns.netHistory = [];
    ns.cpuHistory = [];
    log(`⏰ 启动 ${ns.timerMode} 模式`);
    
    const taskId = `sleept-${nodeId}-${Date.now()}`;
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
            // 解析剩余时间
            const match = msg.message.match(/剩余 (\d{2}:\d{2}:\d{2})/);
            if (match) ns.remainingTime = match[1];
            // 解析网速数据
            const netMatch = msg.message.match(/↑([\d.]+) ↓([\d.]+)/);
            if (netMatch) {
              ns.currentUpload = parseFloat(netMatch[1]);
              ns.currentDownload = parseFloat(netMatch[2]);
              ns.netHistory = [...ns.netHistory.slice(-29), { time: Date.now(), up: ns.currentUpload, down: ns.currentDownload }];
            }
            // 解析CPU数据
            const cpuMatch = msg.message.match(/CPU ([\d.]+)%/);
            if (cpuMatch) {
              ns.currentCpu = parseFloat(cpuMatch[1]);
              ns.cpuHistory = [...ns.cpuHistory.slice(-29), ns.currentCpu];
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
      
      // 构建参数
      const params: Record<string, any> = {
        action: ns.timerMode,
        power_mode: ns.powerMode,
        dryrun: ns.dryrun
      };
      
      if (ns.timerMode === 'countdown') {
        params.hours = ns.hours;
        params.minutes = ns.minutes;
        params.seconds = ns.seconds;
      } else if (ns.timerMode === 'specific_time') {
        params.target_datetime = ns.targetDatetime;
      } else if (ns.timerMode === 'netspeed') {
        params.upload_threshold = ns.uploadThreshold;
        params.download_threshold = ns.downloadThreshold;
        params.net_duration = ns.netDuration;
        params.net_trigger_mode = ns.netTriggerMode;
      } else if (ns.timerMode === 'cpu') {
        params.cpu_threshold = ns.cpuThreshold;
        params.cpu_duration = ns.cpuDuration;
      }
      
      const response = await api.executeNode('sleept', params, { taskId, nodeId }) as any;
      
      if (response.success) {
        ns.phase = 'completed';
        ns.progress = 100;
        ns.progressText = '完成';
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

  // 停止定时器
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

  // 重置
  function handleReset() {
    // 如果正在运行，先停止
    if (isRunning || isPaused) {
      handleStop();
    }
    ns.phase = 'idle';
    ns.progress = 0;
    ns.progressText = '';
    ns.remainingTime = '00:00:00';
    ns.netHistory = [];
    ns.cpuHistory = [];
    ns.logs = [];
  }

  // 获取系统状态
  async function fetchStats() {
    try {
      const response = await api.executeNode('sleept', { action: 'get_stats' }) as any;
      if (response.success) {
        ns.currentUpload = response.current_upload ?? 0;
        ns.currentDownload = response.current_download ?? 0;
        ns.currentCpu = response.current_cpu ?? 0;
      }
    } catch (e) {
      console.error('获取状态失败:', e);
    }
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

  function setPreset(h: number, m: number, s: number) {
    ns.hours = h; ns.minutes = m; ns.seconds = s;
  }
  
  // 绘制迷你折线图
  function drawMiniChart(data: number[], color: string, max?: number): string {
    if (data.length < 2) return '';
    const h = 40, w = 100;
    const maxVal = max ?? Math.max(...data, 1);
    const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - (v / maxVal) * h}`).join(' ');
    return `<svg viewBox="0 0 ${w} ${h}" class="w-full h-10"><polyline fill="none" stroke="${color}" stroke-width="1.5" points="${points}"/></svg>`;
  }
</script>

{#snippet modeBlock()}
  <div class="flex flex-col cq-gap h-full">
    <Label class="cq-text font-medium">计时模式</Label>
    <div class="grid grid-cols-2 cq-gap">
      <Button 
        variant={ns.timerMode === 'countdown' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm"
        onclick={() => ns.timerMode = 'countdown'}
        disabled={isRunning}
      >
        <Timer class="cq-icon mr-1" />倒计时
      </Button>
      <Button 
        variant={ns.timerMode === 'specific_time' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm"
        onclick={() => ns.timerMode = 'specific_time'}
        disabled={isRunning}
      >
        <Calendar class="cq-icon mr-1" />指定时间
      </Button>
      <Button 
        variant={ns.timerMode === 'netspeed' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm"
        onclick={() => ns.timerMode = 'netspeed'}
        disabled={isRunning}
      >
        <Wifi class="cq-icon mr-1" />网速监控
      </Button>
      <Button 
        variant={ns.timerMode === 'cpu' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm"
        onclick={() => ns.timerMode = 'cpu'}
        disabled={isRunning}
      >
        <Cpu class="cq-icon mr-1" />CPU监控
      </Button>
    </div>
    
    <Label class="cq-text font-medium mt-2">电源操作</Label>
    <div class="flex cq-gap">
      <Button 
        variant={ns.powerMode === 'sleep' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm flex-1"
        onclick={() => ns.powerMode = 'sleep'}
        disabled={isRunning}
      >
        <Moon class="cq-icon mr-1" />休眠
      </Button>
      <Button 
        variant={ns.powerMode === 'shutdown' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm flex-1"
        onclick={() => ns.powerMode = 'shutdown'}
        disabled={isRunning}
      >
        <Power class="cq-icon mr-1" />关机
      </Button>
      <Button 
        variant={ns.powerMode === 'restart' ? 'default' : 'outline'} 
        size="sm" 
        class="cq-button-sm flex-1"
        onclick={() => ns.powerMode = 'restart'}
        disabled={isRunning}
      >
        <RotateCcw class="cq-icon mr-1" />重启
      </Button>
    </div>
    
    <label class="flex items-center cq-gap cursor-pointer mt-2">
      <Checkbox bind:checked={ns.dryrun} disabled={isRunning} />
      <span class="cq-text">演练模式</span>
    </label>
  </div>
{/snippet}

{#snippet timerBlock()}
  <div class="flex flex-col cq-gap h-full">
    {#if ns.timerMode === 'countdown'}
      <Label class="cq-text font-medium">倒计时设置</Label>
      <div class="flex cq-gap items-center">
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">时</Label>
          <Input type="number" bind:value={ns.hours} min={0} max={23} disabled={isRunning} class="cq-text" />
        </div>
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">分</Label>
          <Input type="number" bind:value={ns.minutes} min={0} max={59} disabled={isRunning} class="cq-text" />
        </div>
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">秒</Label>
          <Input type="number" bind:value={ns.seconds} min={0} max={59} disabled={isRunning} class="cq-text" />
        </div>
      </div>
      <div class="grid grid-cols-4 cq-gap">
        <Button variant="outline" size="sm" class="cq-button-sm" onclick={() => setPreset(0, 0, 5)} disabled={isRunning}>5秒</Button>
        <Button variant="outline" size="sm" class="cq-button-sm" onclick={() => setPreset(0, 5, 0)} disabled={isRunning}>5分</Button>
        <Button variant="outline" size="sm" class="cq-button-sm" onclick={() => setPreset(0, 30, 0)} disabled={isRunning}>30分</Button>
        <Button variant="outline" size="sm" class="cq-button-sm" onclick={() => setPreset(1, 0, 0)} disabled={isRunning}>1时</Button>
      </div>
    {:else if ns.timerMode === 'specific_time'}
      <Label class="cq-text font-medium">目标时间</Label>
      <Input type="text" bind:value={ns.targetDatetime} placeholder="YYYY-MM-DD HH:MM:SS" disabled={isRunning} class="cq-text font-mono" />
      <span class="cq-text-sm text-muted-foreground">格式: 2024-12-21 23:30:00</span>
    {:else if ns.timerMode === 'netspeed'}
      <Label class="cq-text font-medium">网速监控设置</Label>
      <div class="flex cq-gap items-center">
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">上传阈值(KB/s)</Label>
          <Input type="number" bind:value={ns.uploadThreshold} min={0} disabled={isRunning} class="cq-text" />
        </div>
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">下载阈值(KB/s)</Label>
          <Input type="number" bind:value={ns.downloadThreshold} min={0} disabled={isRunning} class="cq-text" />
        </div>
      </div>
      <div class="flex cq-gap items-center">
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">持续(分钟)</Label>
          <Input type="number" bind:value={ns.netDuration} min={0.5} step={0.5} disabled={isRunning} class="cq-text" />
        </div>
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">触发</Label>
          <div class="flex cq-gap">
            <Button variant={ns.netTriggerMode === 'both' ? 'default' : 'outline'} size="sm" class="cq-button-sm flex-1" onclick={() => ns.netTriggerMode = 'both'} disabled={isRunning}>都低于</Button>
            <Button variant={ns.netTriggerMode === 'any' ? 'default' : 'outline'} size="sm" class="cq-button-sm flex-1" onclick={() => ns.netTriggerMode = 'any'} disabled={isRunning}>任一</Button>
          </div>
        </div>
      </div>
    {:else if ns.timerMode === 'cpu'}
      <Label class="cq-text font-medium">CPU监控设置</Label>
      <div class="flex cq-gap items-center">
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">CPU阈值(%)</Label>
          <Input type="number" bind:value={ns.cpuThreshold} min={1} max={100} disabled={isRunning} class="cq-text" />
        </div>
        <div class="flex-1">
          <Label class="cq-text-sm text-muted-foreground">持续(分钟)</Label>
          <Input type="number" bind:value={ns.cpuDuration} min={0.5} step={0.5} disabled={isRunning} class="cq-text" />
        </div>
      </div>
      <span class="cq-text-sm text-muted-foreground">CPU低于阈值持续指定时间后触发</span>
    {/if}
  </div>
{/snippet}

{#snippet statusBlock()}
  <div class="flex flex-col cq-gap h-full">
    {#if ns.timerMode === 'countdown' || ns.timerMode === 'specific_time'}
      <!-- 倒计时/指定时间：圆形进度 -->
      <div class="flex-1 flex flex-col items-center justify-center">
        <div class="relative w-24 h-24">
          <!-- 背景圆 -->
          <svg class="w-full h-full -rotate-90" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" stroke-width="8" class="text-muted/30" />
            <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" stroke-width="8" 
              class={ns.phase === 'completed' ? 'text-green-500' : ns.phase === 'error' ? 'text-red-500' : 'text-primary'}
              stroke-dasharray={`${ns.progress * 2.83} 283`}
              stroke-linecap="round" />
          </svg>
          <!-- 中心文字 -->
          <div class="absolute inset-0 flex flex-col items-center justify-center">
            {#if isRunning}
              <span class="text-lg font-mono font-bold">{ns.remainingTime}</span>
              <span class="cq-text-sm text-muted-foreground">{ns.progress}%</span>
            {:else if ns.phase === 'completed'}
              <CircleCheck class="w-8 h-8 text-green-500" />
            {:else if ns.phase === 'error'}
              <CircleX class="w-8 h-8 text-red-500" />
            {:else}
              <Clock class="w-8 h-8 text-muted-foreground/50" />
            {/if}
          </div>
        </div>
        <span class="cq-text text-muted-foreground mt-2">{ns.progressText || '等待启动'}</span>
      </div>
    {:else if ns.timerMode === 'netspeed'}
      <!-- 网速监控：折线图 -->
      <div class="flex-1 flex flex-col">
        <div class="flex justify-between cq-text-sm mb-1">
          <span class="text-cyan-500">↑ {ns.currentUpload.toFixed(1)} KB/s</span>
          <span class="text-green-500">↓ {ns.currentDownload.toFixed(1)} KB/s</span>
        </div>
        <div class="flex-1 bg-muted/20 rounded relative overflow-hidden min-h-[60px]">
          {#if ns.netHistory.length > 1}
            <svg viewBox="0 0 100 50" class="w-full h-full" preserveAspectRatio="none">
              <!-- 上传线 -->
              <polyline 
                fill="none" 
                stroke="#06b6d4" 
                stroke-width="1.5"
                points={ns.netHistory.map((d, i) => `${(i / Math.max(ns.netHistory.length - 1, 1)) * 100},${50 - (d.up / Math.max(...ns.netHistory.map(h => Math.max(h.up, h.down)), 1)) * 45}`).join(' ')}
              />
              <!-- 下载线 -->
              <polyline 
                fill="none" 
                stroke="#22c55e" 
                stroke-width="1.5"
                points={ns.netHistory.map((d, i) => `${(i / Math.max(ns.netHistory.length - 1, 1)) * 100},${50 - (d.down / Math.max(...ns.netHistory.map(h => Math.max(h.up, h.down)), 1)) * 45}`).join(' ')}
              />
              <!-- 阈值线 -->
              <line x1="0" y1="25" x2="100" y2="25" stroke="#f59e0b" stroke-width="0.5" stroke-dasharray="2,2" />
            </svg>
          {:else}
            <div class="flex items-center justify-center h-full text-muted-foreground cq-text-sm">
              {isRunning ? '采集数据中...' : '启动后显示图表'}
            </div>
          {/if}
        </div>
        <div class="flex items-center cq-gap mt-1">
          <Progress value={ns.progress} class="flex-1 h-1.5" />
          <span class="cq-text-sm text-muted-foreground w-10 text-right">{ns.progress}%</span>
        </div>
      </div>
    {:else if ns.timerMode === 'cpu'}
      <!-- CPU监控：柱状/折线 -->
      <div class="flex-1 flex flex-col">
        <div class="flex justify-between items-center mb-1">
          <span class="cq-text font-medium">CPU {ns.currentCpu.toFixed(1)}%</span>
          <span class="cq-text-sm text-muted-foreground">阈值 {ns.cpuThreshold}%</span>
        </div>
        <div class="flex-1 bg-muted/20 rounded relative overflow-hidden min-h-[60px]">
          {#if ns.cpuHistory.length > 1}
            <svg viewBox="0 0 100 50" class="w-full h-full" preserveAspectRatio="none">
              <!-- CPU折线 -->
              <polyline 
                fill="none" 
                stroke="#8b5cf6" 
                stroke-width="2"
                points={ns.cpuHistory.map((v, i) => `${(i / Math.max(ns.cpuHistory.length - 1, 1)) * 100},${50 - (v / 100) * 45}`).join(' ')}
              />
              <!-- 阈值线 -->
              <line x1="0" y1={50 - (ns.cpuThreshold / 100) * 45} x2="100" y2={50 - (ns.cpuThreshold / 100) * 45} stroke="#f59e0b" stroke-width="0.5" stroke-dasharray="2,2" />
            </svg>
          {:else}
            <div class="flex items-center justify-center h-full text-muted-foreground cq-text-sm">
              {isRunning ? '采集数据中...' : '启动后显示图表'}
            </div>
          {/if}
        </div>
        <div class="flex items-center cq-gap mt-1">
          <Progress value={ns.progress} class="flex-1 h-1.5" />
          <span class="cq-text-sm text-muted-foreground w-10 text-right">{ns.progress}%</span>
        </div>
      </div>
    {/if}
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
    
    <Button variant="ghost" class="w-full cq-button-sm" onclick={fetchStats}>
      <Activity class="cq-icon mr-1" />刷新
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
  {#if blockId === 'mode'}{@render modeBlock()}
  {:else if blockId === 'timer'}{@render timerBlock()}
  {:else if blockId === 'status'}{@render statusBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
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
    title="sleept" 
    icon={Clock} 
    status={ns.phase} 
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
