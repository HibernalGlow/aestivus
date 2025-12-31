<script lang="ts">
  /**
   * LataNode - Taskfile 任务启动器节点组件
   * 使用 lata 包列出和执行 Taskfile 中定义的任务
   * 支持 xterm.js 终端显示实时输出
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import { onDestroy } from 'svelte';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { LATA_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, saveNodeState } from '$lib/stores/nodeState.svelte';
  import { getWsBaseUrl } from '$lib/stores/backend';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, Rocket, ListTodo, Terminal,
    CircleCheck, CircleX, Copy, Check, RotateCcw, FolderOpen, RefreshCw, Trash2, Wifi, WifiOff
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: { taskfile_path?: string };
      status?: 'idle' | 'running' | 'completed' | 'error';
      logs?: string[];
      label?: string;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'loading' | 'running' | 'completed' | 'error';

  interface TaskInfo {
    name: string;
    desc: string;
    prompt: string | null;
    cmds: string[];
    cmd_count: number;
    silent: boolean;
    vars: Record<string, any>;
    deps: string[];
  }

  interface LataState {
    phase: Phase;
    progress: number;
    progressText: string;
    taskfilePath: string;
    tasks: TaskInfo[];
    selectedTask: string | null;
    taskArgs: string;
    logs: string[];
  }

  const nodeId = $derived(id);
  const configTaskfilePath = $derived(data?.config?.taskfile_path ?? '');
  const dataLogs = $derived(data?.logs ?? []);
  
  // 默认 Taskfile 路径
  function getDefaultTaskfilePath(): string {
    try { return localStorage.getItem('lata-default-taskfile') || ''; }
    catch { return ''; }
  }

  // 获取共享的响应式状态
  const ns = getNodeState<LataState>(id, {
    phase: 'idle',
    progress: 0,
    progressText: '',
    taskfilePath: configTaskfilePath || getDefaultTaskfilePath(),
    tasks: [],
    selectedTask: null,
    taskArgs: '',
    logs: []
  });

  // 纯 UI 状态（不需要同步）
  let copied = $state(false);
  let layoutRenderer = $state<any>(undefined);

  // xterm 终端相关（本地 UI 状态）
  let terminalContainer: HTMLDivElement | null = $state(null);
  let term: any = null;
  let fitAddon: any = null;
  let terminalWs: WebSocket | null = null;
  let terminalConnected = $state(false);
  
  // 保存为默认路径
  function saveAsDefaultPath() {
    if (ns.taskfilePath) {
      localStorage.setItem('lata-default-taskfile', ns.taskfilePath);
      log(`💾 已保存为默认路径`);
    }
  }
  
  // 同步外部日志
  $effect(() => {
    if (dataLogs.length > 0) {
      ns.logs = [...dataLogs];
    }
  });

  let isRunning = $derived(ns.phase === 'loading' || ns.phase === 'running');
  let canExecute = $derived(ns.phase !== 'loading' && ns.phase !== 'running' && ns.selectedTask !== null);
  let borderClass = $derived({
    idle: 'border-border', loading: 'border-primary shadow-sm', running: 'border-primary shadow-sm',
    completed: 'border-primary/50', error: 'border-destructive/50'
  }[ns.phase]);

  function log(msg: string) { ns.logs = [...ns.logs.slice(-30), msg]; }

  async function selectTaskfile() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFileDialog('选择 Taskfile', [
        { name: 'Taskfile', extensions: ['yml', 'yaml'] }
      ]);
      if (selected) {
        ns.taskfilePath = selected;
        log(`📁 选择了 Taskfile: ${selected.split(/[/\\]/).pop()}`);
        await loadTasks();
      }
    } catch (e) { log(`❌ 选择文件失败: ${e}`); }
  }

  async function loadTasks() {
    if (!ns.taskfilePath) {
      log('❌ 请先选择 Taskfile');
      return;
    }
    
    // 清理路径中的引号
    const cleanPath = ns.taskfilePath.trim().replace(/^["']|["']$/g, '');
    if (cleanPath !== ns.taskfilePath) {
      ns.taskfilePath = cleanPath;
    }
    
    ns.phase = 'loading';
    ns.progress = 0;
    ns.progressText = '正在加载任务列表...';
    log(`📋 加载 Taskfile: ${ns.taskfilePath}`);
    
    try {
      const response = await api.executeNode('lata', {
        action: 'list',
        taskfile_path: ns.taskfilePath
      }) as any;
      
      if (response.success) {
        ns.tasks = response.data?.tasks || response.tasks || [];
        ns.phase = 'idle';
        ns.progress = 100;
        ns.progressText = '';
        log(`✅ 找到 ${ns.tasks.length} 个任务`);
        if (ns.tasks.length > 0 && !ns.selectedTask) {
          ns.selectedTask = ns.tasks[0].name;
        }
      } else {
        ns.phase = 'error';
        log(`❌ 加载失败: ${response.message}`);
      }
    } catch (error) {
      ns.phase = 'error';
      log(`❌ 加载失败: ${error}`);
    }
  }

  async function handleExecute() {
    if (!canExecute || !ns.selectedTask) return;
    
    ns.phase = 'running';
    ns.progress = 0;
    ns.progressText = `正在执行任务: ${ns.selectedTask}`;
    log(`🚀 执行任务: ${ns.selectedTask}`);
    
    // 生成任务 ID 并连接 WebSocket
    const taskId = `lata-${nodeId}-${Date.now()}`;
    writeToTerminal(`\x1b[36m[lata]\x1b[0m 执行任务: ${ns.selectedTask}`);
    connectTerminalWs(taskId);
    
    try {
      const response = await api.executeNode('lata', {
        action: 'execute',
        taskfile_path: ns.taskfilePath,
        task_name: ns.selectedTask,
        task_args: ns.taskArgs
      }, { taskId, nodeId }) as any;
      
      if (response.success) {
        ns.phase = 'completed';
        ns.progress = 100;
        ns.progressText = '任务执行完成';
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
    ns.progress = 0;
    ns.progressText = '';
    ns.logs = [];
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(ns.logs.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  // xterm 终端初始化
  async function initTerminal() {
    if (!terminalContainer || term) return;
    
    try {
      const { Terminal } = await import('@xterm/xterm');
      const { FitAddon } = await import('@xterm/addon-fit');
      await import('@xterm/xterm/css/xterm.css');
      
      term = new Terminal({
        cursorBlink: true,
        fontSize: 12,
        fontFamily: 'Consolas, Monaco, "Courier New", monospace',
        theme: {
          background: '#18181b',
          foreground: '#d4d4d4',
          cursor: '#d4d4d4',
          selectionBackground: '#3b82f680',
        },
        scrollback: 1000,
      });
      
      fitAddon = new FitAddon();
      term.loadAddon(fitAddon);
      term.open(terminalContainer);
      fitAddon.fit();
      
      term.writeln('\x1b[36m[lata]\x1b[0m 终端已就绪，等待任务执行...');
      
      // 监听窗口大小变化
      const resizeObserver = new ResizeObserver(() => {
        if (fitAddon) fitAddon.fit();
      });
      resizeObserver.observe(terminalContainer);
      
    } catch (e) {
      console.error('初始化终端失败:', e);
    }
  }

  function clearTerminal() {
    if (term) {
      term.clear();
      term.writeln('\x1b[36m[lata]\x1b[0m 终端已清空');
    }
  }

  function writeToTerminal(text: string) {
    if (term) {
      term.writeln(text);
    }
  }

  // 连接 WebSocket 获取实时输出
  function connectTerminalWs(taskId: string) {
    if (terminalWs) {
      terminalWs.close();
    }
    
    const wsUrl = `${getWsBaseUrl()}/v1/ws/tasks/${taskId}`;
    terminalWs = new WebSocket(wsUrl);
    
    terminalWs.onopen = () => {
      terminalConnected = true;
      writeToTerminal('\x1b[32m[ws]\x1b[0m 已连接');
    };
    
    terminalWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'log') {
          writeToTerminal(msg.message);
        } else if (msg.type === 'progress') {
          writeToTerminal(`\x1b[33m[进度]\x1b[0m ${msg.progress}% - ${msg.message}`);
        } else if (msg.type === 'status') {
          const color = msg.status === 'completed' ? '32' : msg.status === 'error' ? '31' : '36';
          writeToTerminal(`\x1b[${color}m[${msg.status}]\x1b[0m ${msg.message}`);
        }
      } catch {
        writeToTerminal(event.data);
      }
    };
    
    terminalWs.onclose = () => {
      terminalConnected = false;
      writeToTerminal('\x1b[90m[ws]\x1b[0m 连接已关闭');
    };
    
    terminalWs.onerror = () => {
      writeToTerminal('\x1b[31m[ws]\x1b[0m 连接错误');
    };
  }

  // 初始化终端
  $effect(() => {
    if (terminalContainer && !term) {
      initTerminal();
    }
  });

  onDestroy(() => {
    if (terminalWs) terminalWs.close();
    if (term) term.dispose();
  });
</script>


{#snippet taskfileBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex cq-gap">
      <Button variant="outline" size="sm" class="cq-button-sm flex-1" onclick={selectTaskfile} disabled={isRunning}>
        <FolderOpen class="cq-icon mr-1" />选择文件
      </Button>
      <Button variant="outline" size="sm" class="cq-button-sm" onclick={loadTasks} disabled={isRunning || !ns.taskfilePath}>
        <RefreshCw class="cq-icon" />
      </Button>
    </div>
    <Input 
      bind:value={ns.taskfilePath} 
      placeholder="Taskfile.yml 路径" 
      disabled={isRunning} 
      class="cq-text font-mono"
    />
    <div class="flex items-center justify-between cq-text-sm text-muted-foreground">
      <span>
        {#if ns.taskfilePath}
          {ns.taskfilePath.split(/[/\\\\]/).pop()}
        {:else}
          未选择 Taskfile
        {/if}
      </span>
      {#if ns.taskfilePath}
        <Button variant="ghost" size="sm" class="h-5 px-1 text-xs" onclick={saveAsDefaultPath}>
          设为默认
        </Button>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex flex-col cq-gap cq-padding bg-muted/30 cq-rounded">
      <div class="flex items-center cq-gap">
        {#if ns.phase === 'completed'}
          <CircleCheck class="cq-icon text-green-500 shrink-0" />
          <span class="cq-text text-green-600 font-medium">完成</span>
        {:else if ns.phase === 'error'}
          <CircleX class="cq-icon text-red-500 shrink-0" />
          <span class="cq-text text-red-600 font-medium">失败</span>
        {:else if isRunning}
          <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
          <div class="flex-1"><Progress value={ns.progress} class="h-1.5" /></div>
        {:else}
          <Rocket class="cq-icon text-muted-foreground/50 shrink-0" />
          <span class="cq-text text-muted-foreground">等待执行</span>
        {/if}
      </div>
      {#if isRunning && ns.progressText}
        <div class="cq-text-sm text-muted-foreground truncate">{ns.progressText}</div>
      {/if}
    </div>
    
    {#if ns.selectedTask}
      <Input 
        bind:value={ns.taskArgs} 
        placeholder="任务参数（可选）" 
        disabled={isRunning} 
        class="cq-text"
      />
    {/if}
    
    {#if ns.phase === 'idle' || ns.phase === 'error'}
      <Button class="w-full cq-button flex-1" onclick={handleExecute} disabled={!canExecute}>
        <Play class="cq-icon mr-1" /><span>执行任务</span>
      </Button>
    {:else if isRunning}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span>执行中</span>
      </Button>
    {:else if ns.phase === 'completed'}
      <Button class="w-full cq-button flex-1" onclick={handleExecute} disabled={!canExecute}>
        <Play class="cq-icon mr-1" /><span>再次执行</span>
      </Button>
    {/if}
    <Button variant="ghost" class="w-full cq-button-sm" onclick={handleReset} disabled={isRunning}>
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
  </div>
{/snippet}

{#snippet tasksBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between mb-2 shrink-0">
      <span class="cq-text font-semibold flex items-center gap-1">
        <ListTodo class="cq-icon text-blue-500" />任务列表
      </span>
      <span class="cq-text-sm text-muted-foreground">{ns.tasks.length} 个</span>
    </div>
    <div class="flex-1 overflow-y-auto space-y-1">
      {#if ns.tasks.length > 0}
        {#each ns.tasks as task}
          <button
            class="w-full text-left p-2 rounded-md border transition-all {ns.selectedTask === task.name ? 'bg-primary/10 border-primary/50 shadow-sm' : 'bg-muted/30 border-transparent hover:bg-muted/50 hover:border-muted'}"
            onclick={() => { ns.selectedTask = task.name; }}
            disabled={isRunning}
          >
            <div class="flex items-center justify-between gap-2">
              <span class="font-medium text-sm truncate">{task.name}</span>
              <div class="flex items-center gap-1 shrink-0">
                {#if task.cmd_count > 0}
                  <span class="text-xs px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600">{task.cmd_count} 步</span>
                {/if}
                {#if task.prompt}
                  <span class="text-xs px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-600">需输入</span>
                {/if}
                {#if task.deps && task.deps.length > 0}
                  <span class="text-xs px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-600">依赖</span>
                {/if}
              </div>
            </div>
            {#if task.desc}
              <div class="text-xs text-muted-foreground mt-1 truncate">{task.desc}</div>
            {/if}
            {#if ns.selectedTask === task.name && task.cmds && task.cmds.length > 0}
              <div class="mt-2 pt-2 border-t border-border/50">
                <div class="text-xs text-muted-foreground mb-1">命令:</div>
                <div class="space-y-0.5 max-h-20 overflow-y-auto">
                  {#each task.cmds.slice(0, 5) as cmd, i}
                    <div class="text-xs font-mono bg-background/50 px-1.5 py-0.5 rounded truncate" title={cmd}>
                      <span class="text-muted-foreground">{i + 1}.</span> {cmd}
                    </div>
                  {/each}
                  {#if task.cmds.length > 5}
                    <div class="text-xs text-muted-foreground">... 还有 {task.cmds.length - 5} 条</div>
                  {/if}
                </div>
              </div>
            {/if}
          </button>
        {/each}
      {:else}
        <div class="cq-text text-muted-foreground text-center py-6 bg-muted/20 rounded-md">
          {#if ns.taskfilePath}
            <RefreshCw class="w-8 h-8 mx-auto mb-2 opacity-30" />
            <div>点击刷新加载任务</div>
          {:else}
            <FolderOpen class="w-8 h-8 mx-auto mb-2 opacity-30" />
            <div>请先选择 Taskfile</div>
          {/if}
        </div>
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
        {#each ns.logs.slice(-10) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet terminalBlock()}
  <div class="h-full flex flex-col">
    <!-- 终端工具栏 -->
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold flex items-center gap-1">
        <Terminal class="cq-icon text-green-400" />终端
      </span>
      <div class="flex items-center gap-1">
        {#if terminalConnected}
          <Wifi class="w-3 h-3 text-green-500" />
        {:else}
          <WifiOff class="w-3 h-3 text-muted-foreground" />
        {/if}
        <Button variant="ghost" size="icon" class="h-5 w-5" onclick={clearTerminal} title="清空终端">
          <Trash2 class="w-3 h-3" />
        </Button>
      </div>
    </div>
    <!-- xterm 容器 -->
    <div 
      bind:this={terminalContainer}
      class="flex-1 min-h-[120px] bg-zinc-900 rounded overflow-hidden"
    ></div>
  </div>
{/snippet}

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'taskfile'}{@render taskfileBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'tasks'}{@render tasksBlock()}
  {:else if blockId === 'terminal'}{@render terminalBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 400px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="lata" 
    icon={Rocket} 
    status={ns.phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="lata" 
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
        nodeType="lata"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={LATA_DEFAULT_GRID_LAYOUT}
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
