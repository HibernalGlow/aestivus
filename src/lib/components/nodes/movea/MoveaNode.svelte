<script lang="ts">
  /**
   * MoveaNode - 压缩包分类移动节点
   * 
   * 功能：扫描目录并将压缩包/文件夹移动到对应的二级文件夹
   * 参考 streamlit UI 设计
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import * as Select from '$lib/components/ui/select';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { MOVEA_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState, setNodeState } from '$lib/stores/nodeStateStore';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Package, FolderSearch, Play, RotateCcw, Copy, Check,
    FolderOpen, ChevronLeft, ChevronRight, Loader2
  } from '@lucide/svelte';

  interface Props {
    id: string;
    data?: {
      config?: Record<string, any>;
      status?: 'idle' | 'running' | 'completed' | 'error';
      logs?: string[];
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = 'idle' | 'scanning' | 'scanned' | 'moving' | 'completed' | 'error';

  /** 扫描结果项 */
  interface ScanResultItem {
    path: string;
    subfolders: string[];
    archives: string[];
    movable_folders: string[];
    warning?: string;
  }

  interface MoveaState {
    rootPath: string;
    regexPatterns: string;
    allowMoveToUnnumbered: boolean;
    enableFolderMoving: boolean;
  }

  const nodeId = $derived(id);
  const savedState = $derived(getNodeState<MoveaState>(nodeId));
  const dataLogs = $derived(data?.logs ?? []);

  // 状态变量
  let rootPath = $state('E:\\1Hub\\EH\\1EHV');
  let regexPatterns = $state('');
  let allowMoveToUnnumbered = $state(false);
  let enableFolderMoving = $state(true);
  
  let phase = $state<Phase>('idle');
  let logs = $state<string[]>([]);
  let copied = $state(false);
  let layoutRenderer = $state<any>(undefined);
  
  // 扫描结果
  let scanResults = $state<Record<string, ScanResultItem>>({});
  let totalFolders = $state(0);
  let totalArchives = $state(0);
  let totalMovableFolders = $state(0);
  
  // 分页
  let currentPage = $state(0);
  let itemsPerPage = $state(5);
  
  // 移动计划：{ level1Name: { archiveName: targetFolder } }
  let movePlan = $state<Record<string, Record<string, string | null>>>({});
  
  // 跳过标记
  let skipAll = $state<Record<string, boolean>>({});

  let initialized = $state(false);
  
  $effect(() => {
    if (initialized) return;
    
    if (savedState) {
      rootPath = savedState.rootPath ?? 'E:\\1Hub\\EH\\1EHV';
      regexPatterns = savedState.regexPatterns ?? '';
      allowMoveToUnnumbered = savedState.allowMoveToUnnumbered ?? false;
      enableFolderMoving = savedState.enableFolderMoving ?? true;
    }
    initialized = true;
  });
  
  $effect(() => { logs = [...dataLogs]; });

  function saveState() {
    if (!initialized) return;
    setNodeState<MoveaState>(nodeId, { 
      rootPath, regexPatterns, allowMoveToUnnumbered, enableFolderMoving 
    });
  }

  // 派生状态
  let isScanning = $derived(phase === 'scanning');
  let isMoving = $derived(phase === 'moving');
  let hasResults = $derived(Object.keys(scanResults).length > 0);
  let level1Names = $derived(Object.keys(scanResults));
  let totalPages = $derived(Math.ceil(level1Names.length / itemsPerPage));
  let currentLevel1Names = $derived(
    level1Names.slice(currentPage * itemsPerPage, (currentPage + 1) * itemsPerPage)
  );
  
  let borderClass = $derived({
    idle: 'border-border',
    scanning: 'border-primary shadow-sm',
    scanned: 'border-blue-500/50',
    moving: 'border-orange-500/50',
    completed: 'border-green-500/50',
    error: 'border-destructive/50'
  }[phase]);

  $effect(() => { if (rootPath || regexPatterns) saveState(); });

  function log(msg: string) { logs = [...logs.slice(-100), msg]; }

  // 扫描目录
  async function handleScan() {
    if (!rootPath) {
      log('❌ 请输入根路径');
      return;
    }
    
    phase = 'scanning';
    scanResults = {};
    movePlan = {};
    skipAll = {};
    log(`📂 开始扫描: ${rootPath}`);
    
    try {
      const response = await api.executeNode('movea', {
        action: 'scan',
        root_path: rootPath,
        regex_patterns: regexPatterns.split('\n').filter(s => s.trim()),
        allow_move_to_unnumbered: allowMoveToUnnumbered,
        enable_folder_moving: enableFolderMoving
      }) as any;
      
      if (response.logs) for (const m of response.logs) log(m);
      
      if (response.success) {
        phase = 'scanned';
        scanResults = response.data?.scan_results ?? {};
        totalFolders = response.data?.total_folders ?? 0;
        totalArchives = response.data?.total_archives ?? 0;
        totalMovableFolders = response.data?.total_movable_folders ?? 0;
        
        // 初始化移动计划
        initMovePlan();
        
        log(`✅ ${response.message}`);
      } else {
        phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (error) {
      phase = 'error';
      log(`❌ 扫描失败: ${error}`);
    }
  }

  // 初始化移动计划（默认选择第一个二级文件夹）
  function initMovePlan() {
    const plan: Record<string, Record<string, string | null>> = {};
    
    for (const [level1Name, data] of Object.entries(scanResults)) {
      plan[level1Name] = {};
      const defaultTarget = data.subfolders[0] ?? null;
      
      // 压缩包
      for (const archive of data.archives) {
        plan[level1Name][archive] = defaultTarget;
      }
      
      // 可移动文件夹
      if (enableFolderMoving) {
        for (const folder of data.movable_folders) {
          plan[level1Name][`folder_${folder}`] = defaultTarget;
        }
      }
    }
    
    movePlan = plan;
  }

  // 执行单个文件夹的移动
  async function handleMoveSingle(level1Name: string) {
    const plan = movePlan[level1Name];
    if (!plan || Object.values(plan).every(v => v === null)) {
      log(`⚠️ ${level1Name} 没有移动计划`);
      return;
    }
    
    phase = 'moving';
    log(`🚀 开始移动 ${level1Name}...`);
    
    try {
      const response = await api.executeNode('movea', {
        action: 'move_single',
        root_path: rootPath,
        level1_name: level1Name,
        move_plan: plan
      }) as any;
      
      if (response.logs) for (const m of response.logs) log(m);
      
      if (response.success) {
        log(`✅ ${response.message}`);
        // 从结果中移除已处理的文件夹
        const newResults = { ...scanResults };
        delete newResults[level1Name];
        scanResults = newResults;
        
        const newPlan = { ...movePlan };
        delete newPlan[level1Name];
        movePlan = newPlan;
        
        totalFolders = Object.keys(scanResults).length;
      } else {
        log(`❌ ${response.message}`);
      }
      
      phase = hasResults ? 'scanned' : 'completed';
    } catch (error) {
      phase = 'error';
      log(`❌ 移动失败: ${error}`);
    }
  }

  // 执行当前页的移动
  async function handleMoveCurrentPage() {
    for (const level1Name of currentLevel1Names) {
      await handleMoveSingle(level1Name);
    }
  }

  // 执行所有移动
  async function handleMoveAll() {
    for (const level1Name of level1Names) {
      await handleMoveSingle(level1Name);
    }
  }

  // 切换跳过状态
  function toggleSkipAll(level1Name: string) {
    skipAll[level1Name] = !skipAll[level1Name];
    
    // 更新移动计划
    if (skipAll[level1Name]) {
      const plan = { ...movePlan[level1Name] };
      for (const key of Object.keys(plan)) {
        plan[key] = null;
      }
      movePlan[level1Name] = plan;
    } else {
      // 恢复默认
      const data = scanResults[level1Name];
      const defaultTarget = data.subfolders[0] ?? null;
      const plan = { ...movePlan[level1Name] };
      for (const key of Object.keys(plan)) {
        plan[key] = defaultTarget;
      }
      movePlan[level1Name] = plan;
    }
  }

  // 更新单个项目的目标
  function updateTarget(level1Name: string, itemKey: string, target: string | null) {
    if (!movePlan[level1Name]) movePlan[level1Name] = {};
    movePlan[level1Name][itemKey] = target;
    movePlan = { ...movePlan };
  }

  // 切换单个项目的启用状态
  function toggleItemEnabled(level1Name: string, itemKey: string) {
    const current = movePlan[level1Name]?.[itemKey];
    if (current === null) {
      // 启用：设置为第一个目标
      const data = scanResults[level1Name];
      updateTarget(level1Name, itemKey, data.subfolders[0] ?? null);
    } else {
      // 禁用
      updateTarget(level1Name, itemKey, null);
    }
  }

  function handleReset() {
    phase = 'idle';
    scanResults = {};
    movePlan = {};
    skipAll = {};
    currentPage = 0;
    logs = [];
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(logs.join('\n'));
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  // 打开文件夹
  async function openFolder(path: string) {
    try {
      const { platform } = await import('$lib/api/platform');
      await platform.openPath(path);
      log(`📂 已打开: ${path}`);
    } catch (e) {
      log(`❌ 打开失败: ${e}`);
    }
  }
</script>

{#snippet configBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex flex-col cq-gap">
      <Label class="cq-text font-medium">根目录路径</Label>
      <Input 
        bind:value={rootPath}
        placeholder="E:\1Hub\EH\1EHV"
        disabled={isScanning || isMoving}
        class="cq-input font-mono text-xs"
      />
    </div>
    
    <div class="flex flex-col cq-gap">
      <Label class="cq-text font-medium">正则表达式（每行一个）</Label>
      <textarea 
        bind:value={regexPatterns}
        placeholder="用于匹配压缩包到文件夹..."
        disabled={isScanning || isMoving}
        class="flex-1 cq-input font-mono text-xs resize-none min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2"
      ></textarea>
    </div>
    
    <div class="flex flex-col cq-gap">
      <div class="flex items-center cq-gap">
        <Checkbox 
          id="allowUnnumbered"
          checked={allowMoveToUnnumbered}
          onCheckedChange={(v) => allowMoveToUnnumbered = !!v}
          disabled={isScanning || isMoving}
        />
        <Label for="allowUnnumbered" class="cq-text-sm">允许无编号文件夹作为目标</Label>
      </div>
      
      <div class="flex items-center cq-gap">
        <Checkbox 
          id="enableFolder"
          checked={enableFolderMoving}
          onCheckedChange={(v) => enableFolderMoving = !!v}
          disabled={isScanning || isMoving}
        />
        <Label for="enableFolder" class="cq-text-sm">启用文件夹移动</Label>
      </div>
    </div>
  </div>
{/snippet}

{#snippet scanBlock()}
  <div class="flex flex-col cq-gap h-full">
    <Button 
      class="w-full cq-button" 
      onclick={handleScan}
      disabled={isScanning || isMoving || !rootPath}
    >
      {#if isScanning}
        <Loader2 class="cq-icon mr-1 animate-spin" />
      {:else}
        <FolderSearch class="cq-icon mr-1" />
      {/if}
      扫描目录
    </Button>
    
    {#if hasResults}
      <div class="p-2 rounded bg-muted/50 cq-text-sm space-y-1">
        <div>📁 文件夹: {totalFolders}</div>
        <div>📦 压缩包: {totalArchives}</div>
        <div>📂 可移动: {totalMovableFolders}</div>
      </div>
    {/if}
    
    <Button variant="ghost" class="w-full cq-button-sm mt-auto" onclick={handleReset}>
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <Button 
      class="w-full cq-button" 
      variant="default"
      onclick={handleMoveCurrentPage}
      disabled={!hasResults || isMoving || isScanning}
    >
      <Play class="cq-icon mr-1" />
      执行本页
    </Button>
    
    <Button 
      class="w-full cq-button" 
      variant="secondary"
      onclick={handleMoveAll}
      disabled={!hasResults || isMoving || isScanning}
    >
      <Play class="cq-icon mr-1" />
      执行全部
    </Button>
    
    {#if totalPages > 1}
      <div class="flex items-center justify-between cq-gap mt-auto">
        <Button 
          variant="outline" 
          size="icon"
          class="cq-button-icon"
          onclick={() => currentPage = Math.max(0, currentPage - 1)}
          disabled={currentPage === 0}
        >
          <ChevronLeft class="cq-icon" />
        </Button>
        <span class="cq-text-sm">{currentPage + 1}/{totalPages}</span>
        <Button 
          variant="outline" 
          size="icon"
          class="cq-button-icon"
          onclick={() => currentPage = Math.min(totalPages - 1, currentPage + 1)}
          disabled={currentPage >= totalPages - 1}
        >
          <ChevronRight class="cq-icon" />
        </Button>
      </div>
    {/if}
  </div>
{/snippet}

{#snippet foldersBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    {#if !hasResults}
      <div class="flex-1 flex items-center justify-center text-muted-foreground cq-text">
        点击"扫描目录"开始
      </div>
    {:else}
      <div class="flex-1 overflow-y-auto space-y-3 cq-padding">
        {#each currentLevel1Names as level1Name (level1Name)}
          {@const data = scanResults[level1Name]}
          {@const plan = movePlan[level1Name] ?? {}}
          {@const isSkipped = skipAll[level1Name] ?? false}
          
          <div class="border rounded-lg p-2 bg-card/50">
            <!-- 标题行 -->
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center cq-gap">
                <span class="font-semibold cq-text truncate max-w-[200px]" title={level1Name}>
                  📁 {level1Name}
                </span>
                <span class="cq-text-sm text-muted-foreground">
                  ({data.archives.length}📦 {data.movable_folders.length}📂)
                </span>
              </div>
              <div class="flex items-center cq-gap">
                <Button 
                  variant="ghost" 
                  size="icon"
                  class="h-6 w-6"
                  onclick={() => openFolder(data.path)}
                >
                  <FolderOpen class="w-3 h-3" />
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  class="h-6 text-xs"
                  onclick={() => handleMoveSingle(level1Name)}
                  disabled={isMoving || Object.values(plan).every(v => v === null)}
                >
                  执行
                </Button>
              </div>
            </div>
            
            <!-- 警告 -->
            {#if data.warning}
              <div class="text-yellow-600 cq-text-sm mb-2">{data.warning}</div>
            {/if}
            
            <!-- 跳过全部 -->
            <div class="flex items-center cq-gap mb-2">
              <Checkbox 
                checked={isSkipped}
                onCheckedChange={() => toggleSkipAll(level1Name)}
              />
              <span class="cq-text-sm text-muted-foreground">跳过全部</span>
            </div>
            
            <!-- 压缩包列表 -->
            {#each data.archives as archive (archive)}
              {@const target = plan[archive]}
              {@const enabled = target !== null}
              <div class="flex items-center cq-gap py-1 border-t border-border/50">
                <Checkbox 
                  checked={enabled}
                  onCheckedChange={() => toggleItemEnabled(level1Name, archive)}
                />
                <span class="cq-text-sm truncate flex-1" title={archive}>📦 {archive}</span>
                {#if enabled && data.subfolders.length > 0}
                  <Select.Root 
                    type="single"
                    value={{ value: target ?? '', label: target ?? '' }}
                    onValueChange={(v) => updateTarget(level1Name, archive, v?.value ?? null)}
                  >
                    <Select.Trigger class="h-6 w-[120px] text-xs">
                      {target ?? '选择目标'}
                    </Select.Trigger>
                    <Select.Content>
                      {#each data.subfolders as folder}
                        <Select.Item value={folder} label={folder}>{folder}</Select.Item>
                      {/each}
                    </Select.Content>
                  </Select.Root>
                {/if}
              </div>
            {/each}
            
            <!-- 可移动文件夹列表 -->
            {#if enableFolderMoving && data.movable_folders.length > 0}
              {#each data.movable_folders as folder (folder)}
                {@const itemKey = `folder_${folder}`}
                {@const target = plan[itemKey]}
                {@const enabled = target !== null}
                <div class="flex items-center cq-gap py-1 border-t border-border/50">
                  <Checkbox 
                    checked={enabled}
                    onCheckedChange={() => toggleItemEnabled(level1Name, itemKey)}
                  />
                  <span class="cq-text-sm truncate flex-1" title={folder}>📂 {folder}</span>
                  {#if enabled && data.subfolders.length > 0}
                    <Select.Root 
                      type="single"
                      value={{ value: target ?? '', label: target ?? '' }}
                      onValueChange={(v) => updateTarget(level1Name, itemKey, v?.value ?? null)}
                    >
                      <Select.Trigger class="h-6 w-[120px] text-xs">
                        {target ?? '选择目标'}
                      </Select.Trigger>
                      <Select.Content>
                        {#each data.subfolders as subfolder}
                          <Select.Item value={subfolder} label={subfolder}>{subfolder}</Select.Item>
                        {/each}
                      </Select.Content>
                    </Select.Root>
                  {/if}
                </div>
              {/each}
            {/if}
          </div>
        {/each}
      </div>
    {/if}
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
        {#each logs.slice(-30) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'config'}{@render configBlock()}
  {:else if blockId === 'scan'}{@render scanBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'folders'}{@render foldersBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 520px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={400} minHeight={350} maxWidth={520} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={nodeId} 
    title="movea" 
    icon={Package} 
    status={phase === 'idle' ? 'idle' : phase === 'scanning' || phase === 'moving' ? 'running' : phase === 'completed' ? 'completed' : phase === 'error' ? 'error' : 'idle'} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="movea" 
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
        nodeType="movea"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={MOVEA_DEFAULT_GRID_LAYOUT}
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
