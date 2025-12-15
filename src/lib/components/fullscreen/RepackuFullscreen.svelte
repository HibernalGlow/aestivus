<script lang="ts">
  /**
   * RepackuFullscreen - 文件重打包全屏内容组件
   */
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Label } from '$lib/components/ui/label';
  import { Input } from '$lib/components/ui/input';
  import { Progress } from '$lib/components/ui/progress';
  import { api } from '$lib/services/api';
  import { 
    Play, LoaderCircle, FolderOpen, Clipboard,
    CheckCircle, XCircle, FileArchive, Search, FolderTree, Trash2, Copy, Check
  } from '@lucide/svelte';

  interface Props {
    nodeId: string;
    data?: {
      config?: { path?: string; types?: string[]; delete_after?: boolean };
      logs?: string[];
    };
  }

  let { nodeId, data = {} }: Props = $props();

  type Phase = 'idle' | 'analyzing' | 'analyzed' | 'compressing' | 'completed' | 'error';
  
  let path = $state(data?.config?.path ?? '');
  let deleteAfter = $state(data?.config?.delete_after ?? false);
  let phase = $state<Phase>('idle');
  let logs: string[] = $state(data?.logs ? [...data.logs] : []);
  let copied = $state(false);
  
  let progress = $state(0);
  let progressText = $state('');
  
  let analysisResult: {
    configPath: string;
    totalFolders: number;
    entireCount: number;
    selectiveCount: number;
    skipCount: number;
  } | null = $state(null);
  
  let compressionResult: {
    success: boolean;
    compressed: number;
    failed: number;
    total: number;
  } | null = $state(null);

  const typeOptions = [
    { value: 'image', label: '图片' },
    { value: 'document', label: '文档' },
    { value: 'video', label: '视频' },
    { value: 'audio', label: '音频' }
  ];
  
  let selectedTypes: string[] = $state([]);

  let canAnalyze = $derived(phase === 'idle' && path.trim() !== '');
  let canCompress = $derived(phase === 'analyzed' && analysisResult !== null);
  let isRunning = $derived(phase === 'analyzing' || phase === 'compressing');

  async function selectFolder() {
    try {
      if (window.pywebview?.api?.open_folder_dialog) {
        const selected = await window.pywebview.api.open_folder_dialog();
        if (selected) path = selected;
      } else {
        logs = [...logs, '⚠️ 文件夹选择功能需要在桌面应用中使用'];
      }
    } catch (e) {
      logs = [...logs, `选择文件夹失败: ${e}`];
    }
  }

  async function pasteFromClipboard() {
    try {
      const text = await navigator.clipboard.readText();
      path = text.trim();
    } catch (e) {
      logs = [...logs, `读取剪贴板失败: ${e}`];
    }
  }

  function toggleType(type: string) {
    if (selectedTypes.includes(type)) {
      selectedTypes = selectedTypes.filter(t => t !== type);
    } else {
      selectedTypes = [...selectedTypes, type];
    }
  }

  async function handleAnalyze() {
    if (!canAnalyze) return;
    
    phase = 'analyzing';
    progress = 0;
    progressText = '正在扫描目录结构...';
    analysisResult = null;
    compressionResult = null;
    logs = [...logs, `🔍 开始分析目录: ${path}`];
    
    if (selectedTypes.length > 0) {
      logs = [...logs, `📋 类型过滤: ${selectedTypes.join(', ')}`];
    }
    
    try {
      progress = 30;
      progressText = '正在分析文件类型分布...';
      
      const response = await api.executeNode('repacku', {
        action: 'analyze',
        path: path,
        types: selectedTypes.length > 0 ? selectedTypes : [],
        display_tree: true
      }) as any;
      
      if (response.success && response.data) {
        phase = 'analyzed';
        progress = 100;
        progressText = '分析完成';
        
        analysisResult = {
          configPath: response.data.config_path ?? '',
          totalFolders: response.data.total_folders ?? 0,
          entireCount: response.data.entire_count ?? 0,
          selectiveCount: response.data.selective_count ?? 0,
          skipCount: response.data.skip_count ?? 0
        };
        
        logs = [...logs, `✅ 分析完成`];
        logs = [...logs, `📊 整体压缩: ${analysisResult.entireCount}, 选择性: ${analysisResult.selectiveCount}, 跳过: ${analysisResult.skipCount}`];
      } else {
        phase = 'error';
        progress = 0;
        logs = [...logs, `❌ 分析失败: ${response.message}`];
      }
    } catch (error) {
      phase = 'error';
      progress = 0;
      logs = [...logs, `❌ 分析失败: ${error}`];
    }
  }

  async function handleCompress() {
    if (!canCompress || !analysisResult) return;
    
    phase = 'compressing';
    progress = 0;
    progressText = '正在压缩文件...';
    logs = [...logs, `📦 开始压缩...`];
    
    try {
      progress = 20;
      
      const response = await api.executeNode('repacku', {
        action: 'compress',
        config_path: analysisResult.configPath,
        delete_after: deleteAfter
      }) as any;
      
      if (response.success) {
        phase = 'completed';
        progress = 100;
        progressText = '压缩完成';
        
        compressionResult = {
          success: true,
          compressed: response.data?.compressed_count ?? 0,
          failed: response.data?.failed_count ?? 0,
          total: response.data?.total_folders ?? 0
        };
        
        logs = [...logs, `✅ ${response.message}`];
        logs = [...logs, `📊 成功: ${compressionResult.compressed}, 失败: ${compressionResult.failed}`];
      } else {
        phase = 'error';
        progress = 0;
        logs = [...logs, `❌ 压缩失败: ${response.message}`];
      }
    } catch (error) {
      phase = 'error';
      progress = 0;
      logs = [...logs, `❌ 压缩失败: ${error}`];
    }
  }

  function handleReset() {
    phase = 'idle';
    progress = 0;
    progressText = '';
    analysisResult = null;
    compressionResult = null;
    logs = [];
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

  // 忽略未使用警告
  void nodeId;
</script>

<div class="h-full flex">
  <!-- 左侧：操作区 -->
  <div class="w-96 border-r flex flex-col p-6 space-y-4 overflow-y-auto">
    <!-- 路径输入 -->
    <div class="space-y-2">
      <Label>目标路径</Label>
      <div class="flex gap-2">
        <Input 
          bind:value={path}
          placeholder="输入或选择文件夹路径..."
          disabled={isRunning}
          class="flex-1"
        />
        <Button variant="outline" size="icon" onclick={selectFolder} disabled={isRunning}>
          <FolderOpen class="h-4 w-4" />
        </Button>
        <Button variant="outline" size="icon" onclick={pasteFromClipboard} disabled={isRunning}>
          <Clipboard class="h-4 w-4" />
        </Button>
      </div>
    </div>
    
    <!-- 文件类型过滤 -->
    <div class="space-y-2">
      <Label>文件类型过滤（留空处理全部）</Label>
      <div class="flex flex-wrap gap-2">
        {#each typeOptions as option}
          <button
            class="px-3 py-1.5 rounded border transition-colors {selectedTypes.includes(option.value) ? 'bg-primary text-primary-foreground border-primary' : 'bg-background border-border hover:border-primary'}"
            onclick={() => toggleType(option.value)}
            disabled={isRunning}
          >
            {option.label}
          </button>
        {/each}
      </div>
    </div>
    
    <!-- 选项 -->
    <div class="flex items-center gap-2">
      <Checkbox 
        id="delete-after-fullscreen" 
        bind:checked={deleteAfter}
        disabled={isRunning}
      />
      <Label for="delete-after-fullscreen" class="cursor-pointer flex items-center gap-2">
        <Trash2 class="w-4 h-4" />
        压缩成功后删除源文件
      </Label>
    </div>
    
    <!-- 进度条 -->
    {#if isRunning}
      <div class="space-y-2">
        <div class="flex justify-between text-sm text-muted-foreground">
          <span>{progressText}</span>
          <span>{progress}%</span>
        </div>
        <Progress value={progress} class="h-2" />
      </div>
    {/if}
    
    <!-- 分析结果 -->
    {#if analysisResult && phase !== 'idle'}
      <div class="p-4 rounded-lg bg-muted space-y-3">
        <div class="flex items-center gap-2 font-medium">
          <FolderTree class="w-5 h-5 text-yellow-500" />
          <span>分析结果</span>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div class="text-center p-3 bg-background rounded-lg">
            <div class="text-2xl font-bold text-green-600">{analysisResult.entireCount}</div>
            <div class="text-sm text-muted-foreground">整体压缩</div>
          </div>
          <div class="text-center p-3 bg-background rounded-lg">
            <div class="text-2xl font-bold text-yellow-600">{analysisResult.selectiveCount}</div>
            <div class="text-sm text-muted-foreground">选择性</div>
          </div>
          <div class="text-center p-3 bg-background rounded-lg">
            <div class="text-2xl font-bold text-gray-500">{analysisResult.skipCount}</div>
            <div class="text-sm text-muted-foreground">跳过</div>
          </div>
        </div>
      </div>
    {/if}
    
    <!-- 压缩结果 -->
    {#if compressionResult}
      <div class="p-4 rounded-lg bg-muted space-y-2">
        <div class="flex items-center gap-2">
          {#if compressionResult.success}
            <CheckCircle class="w-5 h-5 text-green-500" />
            <span class="text-green-600 font-medium">压缩完成</span>
          {:else}
            <XCircle class="w-5 h-5 text-red-500" />
            <span class="text-red-600 font-medium">压缩失败</span>
          {/if}
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="text-center p-3 bg-background rounded-lg">
            <div class="text-2xl font-bold text-green-600">{compressionResult.compressed}</div>
            <div class="text-sm text-muted-foreground">成功</div>
          </div>
          <div class="text-center p-3 bg-background rounded-lg">
            <div class="text-2xl font-bold text-red-600">{compressionResult.failed}</div>
            <div class="text-sm text-muted-foreground">失败</div>
          </div>
        </div>
      </div>
    {/if}
    
    <!-- 操作按钮 -->
    <div class="flex gap-3">
      {#if phase === 'idle' || phase === 'error'}
        <Button class="flex-1" onclick={handleAnalyze} disabled={!canAnalyze}>
          <Search class="h-4 w-4 mr-2" />
          扫描分析
        </Button>
      {:else if phase === 'analyzing'}
        <Button class="flex-1" disabled>
          <LoaderCircle class="h-4 w-4 mr-2 animate-spin" />
          分析中...
        </Button>
      {:else if phase === 'analyzed'}
        <Button class="flex-1" onclick={handleCompress} disabled={!canCompress}>
          <FileArchive class="h-4 w-4 mr-2" />
          开始压缩
        </Button>
        <Button variant="outline" onclick={handleReset}>重置</Button>
      {:else if phase === 'compressing'}
        <Button class="flex-1" disabled>
          <LoaderCircle class="h-4 w-4 mr-2 animate-spin" />
          压缩中...
        </Button>
      {:else if phase === 'completed'}
        <Button class="flex-1" variant="outline" onclick={handleReset}>
          <Play class="h-4 w-4 mr-2" />
          重新开始
        </Button>
      {/if}
    </div>
  </div>
  
  <!-- 右侧：日志 -->
  <div class="flex-1 flex flex-col overflow-hidden">
    <div class="flex items-center justify-between px-4 py-3 border-b bg-muted/30 shrink-0">
      <span class="font-medium">执行日志</span>
      <Button variant="ghost" size="sm" onclick={copyLogs}>
        {#if copied}
          <Check class="h-4 w-4 mr-2 text-green-500" />
        {:else}
          <Copy class="h-4 w-4 mr-2" />
        {/if}
        复制
      </Button>
    </div>
    <div class="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-1">
      {#if logs.length > 0}
        {#each logs as log}
          <div class="text-muted-foreground">{log}</div>
        {/each}
      {:else}
        <div class="text-muted-foreground text-center py-8">
          暂无日志
        </div>
      {/if}
    </div>
  </div>
</div>
