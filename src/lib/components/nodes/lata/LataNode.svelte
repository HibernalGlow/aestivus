<script lang="ts">
  /**
   * LataNode - Taskfile 任务启动器节点组件
   * 使用 lata 包列出和执行 Taskfile 中定义的任务
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { LATA_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, Rocket, ListTodo,
    CircleCheck, CircleX, Copy, Check, RotateCcw, FolderOpen, RefreshCw
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
  }

  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<LataState>(nodeId));
  const configTaskfilePath = $derived(data?.config?.taskfile_path ?? '');
  const dataLogs = $derived(data?.logs ?? []);

  let taskfilePath = $state('');
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let copied = $state(false);
  let progress = $state(0);
  let progressText = $state('');
  let tasks = $state<TaskInfo[]>([]);
  let selectedTask = $state<string | null>(null);
  let taskArgs = $state('');
  let layoutRenderer = $state<any>(undefined);

  let initialized = $state(false);
  
  // 默认 Taskfile 路径存储 key
  const DEFAULT_TASKFILE_KEY = 'lata-default-taskfile';
  
  // 获取默认路径
  function getDefaultTaskfilePath(): string {
    try {
      return localStorage.getItem(DEFAULT_TASKFILE_KEY) || '';
    } catch { return ''; }
  }
  
  // 保存为默认路径
  function saveAsDefaultPath() {
    if (taskfilePath) {
      localStorage.setItem(DEFAULT_TASKFILE_KEY, taskfilePath);
      log(`💾 已保存为默认路径`);
    }
  }

  // 初始化
  $effect(() => {
    if (initialized) return;
    
    if (savedState) {
      phase = savedState.phase ?? 'idle';
      progress = savedState.progress ?? 0;
      progressText = savedState.progressText ?? '';
      taskfilePath = savedState.taskfilePath ?? configTaskfilePath ?? getDefaultTaskfilePath();
      tasks = savedState.tasks ?? [];
      selectedTask = savedState.selectedTask ?? null;
      taskArgs = savedState.taskArgs ?? '';
    } else {
      taskfilePath = configTaskfilePath || getDefaultTaskfilePath();
    }
    
    initialized = true;
  });
  
  $effect(() => {
    logs = [...dataLogs];
  });

  function saveState() {
    if (!initialized) return;
    setNodeState<LataState>(nodeId, {
      phase, progress, progressText, taskfilePath, tasks, selectedTask, taskArgs
    });
  }

  let isRunning = $derived(phase === 'loading' || phase === 'running');
  let canExecute = $derived(phase !== 'loading' && phase !== 'running' && selectedTask !== null);
  let borderClass = $derived({
    idle: 'border-border', loading: 'border-primary shadow-sm', running: 'border-primary shadow-sm',
    completed: 'border-primary/50', error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (phase || tasks || selectedTask) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-30), msg]; }

  async function selectTaskfile() {
    try {
      const { platform } = await import('$lib/api/platform');
      const selected = await platform.openFileDialog('选择 Taskfile', [
        { name: 'Taskfile', extensions: ['yml', 'yaml'] }
      ]);
      if (selected) {
        taskfilePath = selected;
        log(`📁 选择了 Taskfile: ${selected.split(/[/\\]/).pop()}`);
        await loadTasks();
      }
    } catch (e) { log(`❌ 选择文件失败: ${e}`); }
  }

  async function loadTasks() {
    if (!taskfilePath) {
      log('❌ 请先选择 Taskfile');
      return;
    }
    
    // 清理路径中的引号
    const cleanPath = taskfilePath.trim().replace(/^["']|["']$/g, '');
    if (cleanPath !== taskfilePath) {
      taskfilePath = cleanPath;
    }
    
    phase = 'loading';
    progress = 0;
    progressText = '正在加载任务列表...';
    log(`📋 加载 Taskfile: ${taskfilePath}`);
    
    try {
      const response = await api.executeNode('lata', {
        action: 'list',
        taskfile_path: taskfilePath
      }) as any;
      
      if (response.success) {
        tasks = response.data?.tasks || response.tasks || [];
        phase = 'idle';
        progress = 100;
        progressText = '';
        log(`✅ 找到 ${tasks.length} 个任务`);
        if (tasks.length > 0 && !selectedTask) {
          selectedTask = tasks[0].name;
        }
      } else {
        phase = 'error';
        log(`❌ 加载失败: ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      log(`❌ 加载失败: ${error}`);
    }
  }

  async function handleExecute() {
    if (!canExecute || !selectedTask) return;
    
    phase = 'running';
    progress = 0;
    progressText = `正在执行任务: ${selectedTask}`;
    log(`🚀 执行任务: ${selectedTask}`);
    
    try {
      const response = await api.executeNode('lata', {
        action: 'execute',
        taskfile_path: taskfilePath,
        task_name: selectedTask,
        task_args: taskArgs
      }) as any;
      
      if (response.success) {
        phase = 'completed';
        progress = 100;
        progressText = '任务执行完成';
        log(`✅ ${response.message}`);
      } else {
        phase = 'error';
        log(`❌ 执行失败: ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      log(`❌ 执行失败: ${error}`);
    }
  }

  function handleReset() {
    phase = 'idle';
    progress = 0;
    progressText = '';
    logs = [];
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(logs.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }
</script>


{#snippet taskfileBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex cq-gap">
      <Button variant="outline" size="sm" class="cq-button-sm flex-1" onclick={selectTaskfile} disabled={isRunning}>
        <FolderOpen class="cq-icon mr-1" />选择文件
      </Button>
      <Button variant="outline" size="sm" class="cq-button-sm" onclick={loadTasks} disabled={isRunning || !taskfilePath}>
        <RefreshCw class="cq-icon" />
      </Button>
    </div>
    <Input 
      bind:value={taskfilePath} 
      placeholder="Taskfile.yml 路径" 
      disabled={isRunning} 
      class="cq-text font-mono"
    />
    <div class="flex items-center justify-between cq-text-sm text-muted-foreground">
      <span>
        {#if taskfilePath}
          {taskfilePath.split(/[/\\\\]/).pop()}
        {:else}
          未选择 Taskfile
        {/if}
      </span>
      {#if taskfilePath}
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
        {#if phase === 'completed'}
          <CircleCheck class="cq-icon text-green-500 shrink-0" />
          <span class="cq-text text-green-600 font-medium">完成</span>
        {:else if phase === 'error'}
          <CircleX class="cq-icon text-red-500 shrink-0" />
          <span class="cq-text text-red-600 font-medium">失败</span>
        {:else if isRunning}
          <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
          <div class="flex-1"><Progress value={progress} class="h-1.5" /></div>
        {:else}
          <Rocket class="cq-icon text-muted-foreground/50 shrink-0" />
          <span class="cq-text text-muted-foreground">等待执行</span>
        {/if}
      </div>
      {#if isRunning && progressText}
        <div class="cq-text-sm text-muted-foreground truncate">{progressText}</div>
      {/if}
    </div>
    
    {#if selectedTask}
      <Input 
        bind:value={taskArgs} 
        placeholder="任务参数（可选）" 
        disabled={isRunning} 
        class="cq-text"
      />
    {/if}
    
    {#if phase === 'idle' || phase === 'error'}
      <Button class="w-full cq-button flex-1" onclick={handleExecute} disabled={!canExecute}>
        <Play class="cq-icon mr-1" /><span>执行任务</span>
      </Button>
    {:else if isRunning}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span>执行中</span>
      </Button>
    {:else if phase === 'completed'}
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
      <span class="cq-text-sm text-muted-foreground">{tasks.length} 个</span>
    </div>
    <div class="flex-1 overflow-y-auto space-y-1">
      {#if tasks.length > 0}
        {#each tasks as task}
          <button
            class="w-full text-left p-2 rounded-md border transition-all {selectedTask === task.name ? 'bg-primary/10 border-primary/50 shadow-sm' : 'bg-muted/30 border-transparent hover:bg-muted/50 hover:border-muted'}"
            onclick={() => { selectedTask = task.name; }}
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
            {#if selectedTask === task.name && task.cmds && task.cmds.length > 0}
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
          {#if taskfilePath}
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
      {#if logs.length > 0}
        {#each logs.slice(-10) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'taskfile'}{@render taskfileBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'tasks'}{@render tasksBlock()}
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
    status={phase} 
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
