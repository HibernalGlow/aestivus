<script lang="ts">
  /**
   * TrenameFullscreen - 批量重命名全屏内容组件
   * 
   * 与 TrenameNode 共享逻辑，但不包含 NodeWrapper 外壳
   */
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Input } from '$lib/components/ui/input';
  import { api } from '$lib/services/api';
  import { 
    LoaderCircle, FolderOpen, Clipboard, Search, Undo2, Copy, Check,
    Download, Upload, AlertTriangle, Play, RefreshCw, ChevronDown, ChevronRight,
    File, Folder, Trash2, Settings2
  } from '@lucide/svelte';

  interface Props {
    nodeId: string;
    data?: { config?: { path?: string }; logs?: string[]; showTree?: boolean };
  }

  let { nodeId, data = {} }: Props = $props();

  // 文件树类型
  interface FileNode { src: string; tgt: string; }
  interface DirNode { src_dir: string; tgt_dir: string; children: (FileNode | DirNode)[]; }
  type TreeNode = FileNode | DirNode;

  // 状态
  type Phase = 'idle' | 'scanning' | 'ready' | 'renaming' | 'completed' | 'error';
  let phase = $state<Phase>('idle');
  let logs: string[] = $state(data?.logs ? [...data.logs] : []);
  let copied = $state(false);
  let showOptions = $state(false);
  
  // 配置
  let scanPath = $state(data?.config?.path ?? '');
  let includeHidden = $state(false);
  let excludeExts = $state('.json,.txt,.html,.htm,.md,.log');
  let maxLines = $state(1000);
  let useCompact = $state(true);
  let basePath = $state('');
  let dryRun = $state(false);
  
  // 数据
  let treeData: TreeNode[] = $state([]);
  let segments: string[] = $state([]);
  let currentSegment = $state(0);
  let stats = $state({ total: 0, pending: 0, ready: 0, conflicts: 0 });
  let conflicts: string[] = $state([]);
  let lastOperationId = $state('');
  let expandedPaths: Set<string> = $state(new Set());

  // 计算
  let isRunning = $derived(phase === 'scanning' || phase === 'renaming');
  let canRename = $derived(phase === 'ready' && stats.ready > 0);

  function log(msg: string) { logs = [...logs.slice(-50), msg]; }
  function isDir(node: TreeNode): node is DirNode { return 'src_dir' in node; }
  function getStatus(node: TreeNode): 'pending' | 'ready' | 'same' {
    const tgt = isDir(node) ? node.tgt_dir : node.tgt;
    const src = isDir(node) ? node.src_dir : node.src;
    if (!tgt || tgt === '') return 'pending';
    if (tgt === src) return 'same';
    return 'ready';
  }
  function toggleExpand(path: string) {
    if (expandedPaths.has(path)) {
      expandedPaths.delete(path);
    } else {
      expandedPaths.add(path);
    }
    expandedPaths = new Set(expandedPaths);
  }
  function parseTree(json: string): TreeNode[] {
    try { return JSON.parse(json).root || []; } catch { return []; }
  }

  async function selectFolder() {
    try {
      if (window.pywebview?.api?.open_folder_dialog) {
        const s = await window.pywebview.api.open_folder_dialog();
        if (s) scanPath = s;
      } else log('⚠️ 需要桌面应用');
    } catch (e) { log(`选择失败: ${e}`); }
  }
  
  async function pastePath() {
    try { scanPath = (await navigator.clipboard.readText()).trim(); } catch (e) { log(`粘贴失败: ${e}`); }
  }
  
  async function handleScan(merge = false) {
    if (!scanPath.trim()) { log('❌ 请输入路径'); return; }
    phase = 'scanning';
    log(`🔍 ${merge ? '合并' : '替换'}扫描: ${scanPath}`);
    try {
      const r = await api.executeNode('trename', {
        action: 'scan', paths: [scanPath], include_hidden: includeHidden,
        exclude_exts: excludeExts, max_lines: maxLines, compact: useCompact
      }) as any;
      if (r.success && r.data) {
        const segs = r.data.segments || [];
        if (merge && segments.length > 0) {
          segments = [...segments, ...segs];
          stats.total += r.data.total_items || 0;
          stats.pending += r.data.pending_count || 0;
          stats.ready += r.data.ready_count || 0;
        } else {
          segments = segs;
          stats = { total: r.data.total_items || 0, pending: r.data.pending_count || 0, ready: r.data.ready_count || 0, conflicts: 0 };
          basePath = r.data.base_path || '';
        }
        if (segs.length > 0) treeData = parseTree(segs[0]);
        currentSegment = 0; conflicts = []; phase = 'ready';
        log(`✅ ${r.data.total_items} 项, ${segs.length} 段`);
      } else { phase = 'error'; log(`❌ ${r.message}`); }
    } catch (e) { phase = 'error'; log(`❌ ${e}`); }
  }

  async function importJson(replace = false) {
    try {
      const text = await navigator.clipboard.readText();
      if (!text.trim()) { log('❌ 剪贴板为空'); return; }
      log('📋 导入中...');
      const r = await api.executeNode('trename', { action: 'import', json_content: text }) as any;
      if (r.success && r.data) {
        if (replace || segments.length === 0) {
          segments = [text];
          stats = { total: r.data.total_items || 0, pending: r.data.pending_count || 0, ready: r.data.ready_count || 0, conflicts: 0 };
        } else {
          segments = [...segments, text];
          stats.total += r.data.total_items || 0;
          stats.pending += r.data.pending_count || 0;
          stats.ready += r.data.ready_count || 0;
        }
        treeData = parseTree(text);
        currentSegment = segments.length - 1; phase = 'ready';
        log(`✅ 导入 ${r.data.total_items} 项`);
      } else log(`❌ ${r.message}`);
    } catch (e) { log(`❌ ${e}`); }
  }
  
  async function copySegment(i: number) {
    if (i >= segments.length) return;
    try { 
      await navigator.clipboard.writeText(segments[i]); 
      copied = true; 
      log(`📋 段${i+1}已复制`); 
      setTimeout(() => copied = false, 2000); 
    } catch (e) { log(`复制失败: ${e}`); }
  }
  
  async function validate() {
    if (!segments.length) return;
    log('🔍 检测冲突...');
    try {
      const r = await api.executeNode('trename', { action: 'validate', json_content: segments[currentSegment], base_path: basePath }) as any;
      if (r.success) { 
        conflicts = r.data?.conflicts || []; 
        stats.conflicts = conflicts.length; 
        log(conflicts.length ? `⚠️ ${conflicts.length} 冲突` : '✅ 无冲突'); 
      } else log(`❌ ${r.message}`);
    } catch (e) { log(`❌ ${e}`); }
  }
  
  async function handleRename() {
    if (!segments.length || !stats.ready) { log('❌ 无可重命名项'); return; }
    phase = 'renaming'; 
    log(`${dryRun ? '🔍 模拟' : '▶️ 执行'}重命名...`);
    try {
      const r = await api.executeNode('trename', { action: 'rename', json_content: segments[currentSegment], base_path: basePath, dry_run: dryRun }) as any;
      if (r.success) {
        lastOperationId = r.data?.operation_id || ''; 
        phase = 'completed';
        log(`✅ 成功${r.data?.success_count || 0} 失败${r.data?.failed_count || 0}`);
        if (lastOperationId) log(`🔄 撤销ID: ${lastOperationId}`);
      } else { phase = 'error'; log(`❌ ${r.message}`); }
    } catch (e) { phase = 'error'; log(`❌ ${e}`); }
  }
  
  async function handleUndo() {
    log('🔄 撤销...');
    try {
      const r = await api.executeNode('trename', { action: 'undo', batch_id: lastOperationId }) as any;
      if (r.success) { log(`✅ ${r.message}`); lastOperationId = ''; phase = 'ready'; }
      else log(`❌ ${r.message}`);
    } catch (e) { log(`❌ ${e}`); }
  }
  
  function clear() {
    treeData = []; segments = []; currentSegment = 0;
    stats = { total: 0, pending: 0, ready: 0, conflicts: 0 };
    conflicts = []; lastOperationId = ''; phase = 'idle'; 
    expandedPaths.clear();
    log('🗑️ 已清空');
  }
  
  async function copyLogs() { 
    try { await navigator.clipboard.writeText(logs.join('\n')); } catch {} 
  }

  // 忽略未使用警告
  void nodeId;
</script>

<!-- 递归渲染文件树 -->
{#snippet treeNode(node: TreeNode, path: string, depth: number)}
  {@const dir = isDir(node)}
  {@const status = getStatus(node)}
  {@const exp = expandedPaths.has(path)}
  {@const name = dir ? node.src_dir : node.src}
  {@const tgt = dir ? node.tgt_dir : node.tgt}
  
  <div class="flex items-center gap-1 py-0.5 hover:bg-muted/50 rounded text-sm" style="padding-left: {depth * 16}px">
    {#if dir}
      <button class="p-0.5 hover:bg-muted rounded" onclick={() => toggleExpand(path)}>
        {#if exp}<ChevronDown class="w-4 h-4" />{:else}<ChevronRight class="w-4 h-4" />{/if}
      </button>
      <Folder class="w-4 h-4 text-yellow-500 shrink-0" />
    {:else}
      <span class="w-5"></span>
      <File class="w-4 h-4 text-blue-500 shrink-0" />
    {/if}
    <span class="truncate flex-1 min-w-0" title={name}>{name}</span>
    {#if tgt && tgt !== name}
      <span class="text-muted-foreground shrink-0">→</span>
      <span class="truncate text-green-600 max-w-48" title={tgt}>{tgt}</span>
    {/if}
    <span class="w-2.5 h-2.5 rounded-full shrink-0 {status === 'ready' ? 'bg-green-500' : status === 'pending' ? 'bg-yellow-500' : 'bg-gray-300'}"></span>
  </div>
  {#if dir && exp && node.children}
    {#each node.children as child, i}{@render treeNode(child, `${path}/${i}`, depth + 1)}{/each}
  {/if}
{/snippet}

<div class="h-full flex">
  <!-- 左侧：操作区 -->
  <div class="w-80 border-r flex flex-col p-4 space-y-3 overflow-y-auto">
    <!-- 路径输入 -->
    <div class="flex gap-2">
      <Input bind:value={scanPath} placeholder="目录路径..." disabled={isRunning} class="flex-1" />
      <Button variant="outline" size="icon" onclick={selectFolder} disabled={isRunning}><FolderOpen class="h-4 w-4" /></Button>
      <Button variant="outline" size="icon" onclick={pastePath} disabled={isRunning}><Clipboard class="h-4 w-4" /></Button>
    </div>
    
    <!-- 扫描按钮 -->
    <div class="flex gap-2">
      <Button variant="outline" class="flex-1" onclick={() => handleScan(false)} disabled={isRunning}>
        {#if isRunning && phase === 'scanning'}<LoaderCircle class="h-4 w-4 mr-2 animate-spin" />{:else}<RefreshCw class="h-4 w-4 mr-2" />{/if}替换扫描
      </Button>
      <Button variant="outline" class="flex-1" onclick={() => handleScan(true)} disabled={isRunning}>
        <Download class="h-4 w-4 mr-2" />合并扫描
      </Button>
    </div>
    
    <!-- 导入/导出 -->
    <div class="flex gap-2">
      <Button variant="ghost" class="flex-1" onclick={() => importJson(false)} disabled={isRunning}>
        <Upload class="h-4 w-4 mr-2" />导入
      </Button>
      <Button variant="ghost" class="flex-1" onclick={() => importJson(true)} disabled={isRunning}>
        <Copy class="h-4 w-4 mr-2" />替换
      </Button>
      <Button variant="ghost" class="flex-1" onclick={() => copySegment(currentSegment)} disabled={!segments.length}>
        {#if copied}<Check class="h-4 w-4 mr-2 text-green-500" />{:else}<Clipboard class="h-4 w-4 mr-2" />{/if}复制
      </Button>
    </div>
    
    <!-- 分段选择器 -->
    {#if segments.length > 1}
      <div class="flex items-center gap-2 flex-wrap">
        <span class="text-sm text-muted-foreground">分段:</span>
        {#each segments as _, i}
          <Button 
            variant={currentSegment === i ? 'default' : 'outline'} 
            size="sm"
            onclick={() => { currentSegment = i; treeData = parseTree(segments[i]); }}
          >{i + 1}</Button>
        {/each}
      </div>
    {/if}
    
    <!-- 统计信息 -->
    {#if stats.total > 0}
      <div class="flex gap-3 text-sm flex-wrap p-2 bg-muted/50 rounded">
        <span>总计: <span class="font-semibold">{stats.total}</span></span>
        <span class="text-yellow-600">待翻译: {stats.pending}</span>
        <span class="text-green-600">就绪: {stats.ready}</span>
        {#if stats.conflicts > 0}<span class="text-red-600">冲突: {stats.conflicts}</span>{/if}
      </div>
    {/if}
    
    <!-- 操作按钮 -->
    <div class="flex gap-2">
      <Button variant="outline" class="flex-1" onclick={validate} disabled={isRunning || !segments.length}>
        <Search class="h-4 w-4 mr-2" />检测冲突
      </Button>
      <Button variant={canRename ? 'default' : 'outline'} class="flex-1" onclick={handleRename} disabled={isRunning || !canRename}>
        {#if phase === 'renaming'}<LoaderCircle class="h-4 w-4 mr-2 animate-spin" />{:else}<Play class="h-4 w-4 mr-2" />{/if}执行
      </Button>
    </div>
    
    <div class="flex gap-2">
      <Button variant="ghost" class="flex-1" onclick={handleUndo} disabled={!lastOperationId}>
        <Undo2 class="h-4 w-4 mr-2" />撤销
      </Button>
      <Button variant="ghost" class="flex-1" onclick={clear}>
        <Trash2 class="h-4 w-4 mr-2" />清空
      </Button>
      <Button variant="ghost" size="icon" onclick={() => showOptions = !showOptions}>
        <Settings2 class="h-4 w-4" />
      </Button>
    </div>
    
    <!-- 高级选项 -->
    {#if showOptions}
      <div class="border rounded p-3 space-y-3 bg-muted/20">
        <div class="flex flex-wrap gap-3">
          <label class="flex items-center gap-2">
            <Checkbox bind:checked={includeHidden} />
            <span class="text-sm">隐藏文件</span>
          </label>
          <label class="flex items-center gap-2">
            <Checkbox bind:checked={dryRun} />
            <span class="text-sm">模拟执行</span>
          </label>
          <label class="flex items-center gap-2">
            <Checkbox bind:checked={useCompact} />
            <span class="text-sm">紧凑格式</span>
          </label>
        </div>
        <div class="flex gap-3">
          <label class="flex items-center gap-2 flex-1">
            <span class="text-sm text-muted-foreground whitespace-nowrap">排除:</span>
            <Input bind:value={excludeExts} class="flex-1" placeholder=".json,.txt" />
          </label>
          <label class="flex items-center gap-2">
            <span class="text-sm text-muted-foreground whitespace-nowrap">分段:</span>
            <Input type="number" bind:value={maxLines} class="w-20" min={50} max={5000} step={100} />
          </label>
        </div>
      </div>
    {/if}
    
    <!-- 冲突列表 -->
    {#if conflicts.length > 0}
      <div class="border border-red-500/30 rounded p-3 bg-red-500/5 max-h-32 overflow-y-auto">
        <div class="text-sm text-red-500 font-medium mb-2 flex items-center gap-2">
          <AlertTriangle class="h-4 w-4" />冲突 ({conflicts.length})
        </div>
        {#each conflicts as c}
          <div class="text-sm text-red-400 truncate" title={c}>{c}</div>
        {/each}
      </div>
    {/if}
    
    <!-- 日志区域 -->
    {#if logs.length > 0}
      <div class="border rounded bg-muted/20 flex-1 min-h-24 overflow-hidden flex flex-col">
        <div class="flex items-center justify-between px-2 py-1 border-b bg-muted/30 shrink-0">
          <span class="text-sm text-muted-foreground">日志</span>
          <Button variant="ghost" size="sm" class="h-6 px-2" onclick={copyLogs}>
            <Clipboard class="h-3 w-3 mr-1" />复制
          </Button>
        </div>
        <div class="p-2 space-y-1 overflow-y-auto flex-1">
          {#each logs as logItem}
            <div class="text-sm font-mono text-muted-foreground">{logItem}</div>
          {/each}
        </div>
      </div>
    {/if}
  </div>
  
  <!-- 右侧：文件树 -->
  <div class="flex-1 flex flex-col overflow-hidden">
    <div class="text-sm font-medium p-3 border-b bg-muted/30 flex items-center justify-between shrink-0">
      <span>文件树预览</span>
      <span class="text-muted-foreground">{stats.total} 项</span>
    </div>
    <div class="flex-1 overflow-y-auto p-3">
      {#if treeData.length > 0}
        {#each treeData as node, i}
          {@render treeNode(node, `root_${i}`, 0)}
        {/each}
      {:else}
        <div class="text-muted-foreground text-center py-8">
          扫描目录或导入 JSON 以查看文件树
        </div>
      {/if}
    </div>
  </div>
</div>
