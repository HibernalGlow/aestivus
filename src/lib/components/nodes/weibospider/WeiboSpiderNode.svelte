<script lang="ts">
  /**
   * WeiboSpiderNode - 微博爬虫节点组件
   * 爬取指定用户的微博数据、图片、视频
   */
  import { Handle, Position, NodeResizer } from '@xyflow/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Progress } from '$lib/components/ui/progress';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Textarea } from '$lib/components/ui/textarea';

  import { NodeLayoutRenderer } from '$lib/components/blocks';
  import { WEIBOSPIDER_DEFAULT_GRID_LAYOUT } from './blocks';
  import { api } from '$lib/services/api';
  import { getNodeState } from '$lib/stores/nodeState.svelte';
  import { getWsBaseUrl } from '$lib/stores/backend';
  import NodeWrapper from '../NodeWrapper.svelte';
  import { 
    Play, LoaderCircle, Users,
    CircleCheck, CircleX, Copy, Check, Plus, Trash2,
    RefreshCw, Image, Video, FileJson, FileText
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

  type Phase = 'idle' | 'running' | 'completed' | 'error';

  interface WeiboSpiderState {
    userIds: string[];
    newUserId: string;
    filterOriginal: boolean;
    sinceDate: string;
    endDate: string;
    picDownload: boolean;
    videoDownload: boolean;
    writeMode: string[];
    outputDir: string;
    cookie: string;
    cookieValid: boolean;
    browser: 'edge' | 'chrome' | 'firefox';
    configPath: string;  // 自定义配置文件路径
    phase: Phase;
    logs: string[];
    progress: number;
    progressText: string;
    crawledUsers: number;
    crawledWeibos: number;
  }

  // 浏览器选项
  const browserOptions = [
    { value: 'edge', label: 'Edge', icon: '🌐' },
    { value: 'chrome', label: 'Chrome', icon: '🔵' },
    { value: 'firefox', label: 'Firefox', icon: '🦊' }
  ] as const;

  // 获取默认日期（一年前）
  function getDefaultSinceDate(): string {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 1);
    return d.toISOString().split('T')[0];
  }

  // 获取共享的响应式状态（直接使用 id，不用 $derived）
  const ns = getNodeState<WeiboSpiderState>(id, {
    userIds: [],
    newUserId: '',
    filterOriginal: true,
    sinceDate: getDefaultSinceDate(),
    endDate: 'now',
    picDownload: true,
    videoDownload: true,
    writeMode: ['json'],
    outputDir: '',
    cookie: '',
    cookieValid: false,
    browser: 'edge',
    configPath: '',
    phase: 'idle',
    logs: [],
    progress: 0,
    progressText: '',
    crawledUsers: 0,
    crawledWeibos: 0
  });

  // 本地 UI 状态
  let copied = $state(false);
  let layoutRenderer = $state<any>(undefined);
  let ws: WebSocket | null = null;

  // 派生状态
  let isRunning = $derived(ns.phase === 'running');
  let canStart = $derived(ns.phase !== 'running' && ns.userIds.length > 0);
  let borderClass = $derived({
    idle: 'border-border',
    running: 'border-primary shadow-sm',
    completed: 'border-green-500/50',
    error: 'border-destructive/50'
  }[ns.phase]);

  function log(msg: string) { ns.logs = [...ns.logs.slice(-50), msg]; }

  // 添加用户ID
  function addUserId() {
    const uid = ns.newUserId.trim();
    if (uid && !ns.userIds.includes(uid)) {
      ns.userIds = [...ns.userIds, uid];
      ns.newUserId = '';
      log(`➕ 添加用户: ${uid}`);
    }
  }

  // 删除用户ID
  function removeUserId(uid: string) {
    ns.userIds = ns.userIds.filter(u => u !== uid);
    log(`➖ 移除用户: ${uid}`);
  }

  // 切换输出格式
  function toggleWriteMode(mode: string) {
    if (ns.writeMode.includes(mode)) {
      ns.writeMode = ns.writeMode.filter(m => m !== mode);
    } else {
      ns.writeMode = [...ns.writeMode, mode];
    }
  }

  // 加载配置
  async function loadConfig(configPath?: string) {
    try {
      log('📂 加载配置...');
      const params: any = { action: 'load_config' };
      if (configPath || ns.configPath) {
        params.config_path = configPath || ns.configPath;
      }
      const response = await api.executeNode('weibospider', params) as any;
      
      if (response.success && response.data) {
        const config = response.data;
        ns.userIds = Array.isArray(config.user_id_list) ? config.user_id_list : [];
        ns.filterOriginal = config.filter === 1;
        ns.sinceDate = config.since_date || getDefaultSinceDate();
        ns.endDate = config.end_date || 'now';
        ns.picDownload = config.pic_download === 1;
        ns.videoDownload = config.video_download === 1;
        ns.writeMode = config.write_mode || ['json'];
        ns.cookie = config.cookie || '';
        log('✅ 配置加载成功');
      } else {
        log(`❌ ${response.message}`);
      }
    } catch (e: any) {
      log(`❌ 加载失败: ${e}`);
    }
  }

  // 导入配置文件
  async function importConfig() {
    try {
      // 使用文件选择器
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.json';
      input.onchange = async (e) => {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (!file) return;
        
        log(`📂 导入配置: ${file.name}`);
        const text = await file.text();
        const imported = JSON.parse(text);
        
        // 如果是纯 cookie 文件
        if (imported.cookie && Object.keys(imported).length === 1) {
          ns.cookie = imported.cookie;
          log('✅ Cookie 导入成功');
          return;
        }
        
        // 完整配置文件
        if (imported.user_id_list) ns.userIds = imported.user_id_list;
        if (imported.filter !== undefined) ns.filterOriginal = imported.filter === 1;
        if (imported.since_date) ns.sinceDate = imported.since_date;
        if (imported.end_date) ns.endDate = imported.end_date;
        if (imported.pic_download !== undefined) ns.picDownload = imported.pic_download === 1;
        if (imported.video_download !== undefined) ns.videoDownload = imported.video_download === 1;
        if (imported.write_mode) ns.writeMode = imported.write_mode;
        if (imported.cookie) ns.cookie = imported.cookie;
        
        log('✅ 配置导入成功');
      };
      input.click();
    } catch (e: any) {
      log(`❌ 导入失败: ${e}`);
    }
  }

  // 导出配置文件
  async function exportConfig() {
    try {
      const config = {
        user_id_list: ns.userIds,
        filter: ns.filterOriginal ? 1 : 0,
        since_date: ns.sinceDate,
        end_date: ns.endDate,
        pic_download: ns.picDownload ? 1 : 0,
        video_download: ns.videoDownload ? 1 : 0,
        write_mode: ns.writeMode,
        cookie: ns.cookie
      };
      
      const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `weibo_config_${new Date().toISOString().slice(0,10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
      log('✅ 配置已导出');
    } catch (e: any) {
      log(`❌ 导出失败: ${e}`);
    }
  }

  // 解析 Cookie（支持 JSON 格式和纯文本）
  function parseCookieInput(input: string): string {
    const trimmed = input.trim();
    if (!trimmed) return '';
    
    // 尝试解析 JSON 格式
    if (trimmed.startsWith('{')) {
      try {
        const json = JSON.parse(trimmed);
        // 支持 {"cookie": "..."} 格式
        if (json.cookie && typeof json.cookie === 'string') {
          return json.cookie;
        }
        // 支持 {"name": "value", ...} 格式，转换为 cookie 字符串
        if (typeof json === 'object' && !Array.isArray(json)) {
          return Object.entries(json)
            .filter(([_, v]) => typeof v === 'string')
            .map(([k, v]) => `${k}=${v}`)
            .join('; ');
        }
      } catch {
        // 不是有效 JSON，当作普通文本处理
      }
    }
    return trimmed;
  }

  // 处理 Cookie 输入变化
  function handleCookieInput(e: Event) {
    const target = e.target as HTMLTextAreaElement;
    const raw = target.value;
    const parsed = parseCookieInput(raw);
    
    // 如果解析出不同的值，说明是 JSON 格式，自动转换
    if (parsed !== raw && parsed) {
      ns.cookie = parsed;
      log('📋 已从 JSON 解析 Cookie');
    } else {
      ns.cookie = raw;
    }
    ns.cookieValid = false;
  }

  // 验证 Cookie
  async function validateCookie() {
    try {
      log('🔍 验证 Cookie...');
      const response = await api.executeNode('weibospider', { 
        action: 'validate_cookie',
        cookie: ns.cookie
      }) as any;
      
      ns.cookieValid = response.cookie_valid ?? false;
      log(response.message);
    } catch (e: any) {
      log(`❌ 验证失败: ${e}`);
      ns.cookieValid = false;
    }
  }

  // 从浏览器获取 Cookie
  async function getBrowserCookie() {
    try {
      log(`🌐 从 ${ns.browser} 浏览器获取 Cookie...`);
      const response = await api.executeNode('weibospider', { 
        action: 'get_browser_cookie',
        browser: ns.browser
      }) as any;
      
      if (response.success && response.data?.cookie) {
        ns.cookie = response.data.cookie;
        ns.cookieValid = response.cookie_valid ?? false;
        log('✅ Cookie 获取成功');
      } else {
        log(`❌ ${response.message}`);
      }
    } catch (e: any) {
      log(`❌ 获取失败: ${e}`);
    }
  }

  // 开始爬取
  async function handleStart() {
    if (isRunning || ns.userIds.length === 0) return;
    
    ns.phase = 'running';
    ns.progress = 0;
    ns.progressText = '启动中...';
    ns.crawledUsers = 0;
    ns.crawledWeibos = 0;
    log('🕷️ 开始爬取微博...');
    
    const taskId = `weibospider-${id}-${Date.now()}`;
    
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
        } catch (e) {
          console.error('解析消息失败:', e);
        }
      };
      
      await new Promise<void>((resolve) => {
        const timeout = setTimeout(resolve, 1000);
        ws!.onopen = () => { clearTimeout(timeout); resolve(); };
        ws!.onerror = () => { clearTimeout(timeout); resolve(); };
      });
      
      const response = await api.executeNode('weibospider', {
        action: 'crawl',
        user_ids: ns.userIds,
        filter_original: ns.filterOriginal,
        since_date: ns.sinceDate,
        end_date: ns.endDate,
        pic_download: ns.picDownload,
        video_download: ns.videoDownload,
        write_mode: ns.writeMode,
        output_dir: ns.outputDir,
        cookie: ns.cookie
      }, { taskId, nodeId: id }) as any;
      
      if (response.success) {
        ns.phase = 'completed';
        ns.progress = 100;
        ns.crawledUsers = response.crawled_users ?? 0;
        ns.crawledWeibos = response.crawled_weibos ?? 0;
        log(`✅ ${response.message}`);
      } else {
        ns.phase = 'error';
        log(`❌ ${response.message}`);
      }
    } catch (error: any) {
      ns.phase = 'error';
      log(`❌ 执行失败: ${error}`);
    } finally {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
      ws = null;
    }
  }

  // 停止爬取
  function handleStop() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
    ns.phase = 'idle';
    log('⏹️ 已停止');
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
</script>

{#snippet usersBlock()}
  <div class="flex flex-col cq-gap h-full">
    <Label class="cq-text font-medium">用户ID列表</Label>
    <div class="flex cq-gap">
      <Input 
        type="text" 
        bind:value={ns.newUserId} 
        placeholder="输入用户ID" 
        class="cq-text flex-1"
        disabled={isRunning}
        onkeydown={(e) => e.key === 'Enter' && addUserId()}
      />
      <Button size="sm" class="cq-button-sm" onclick={addUserId} disabled={isRunning || !ns.newUserId.trim()}>
        <Plus class="cq-icon" />
      </Button>
    </div>
    <div class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding space-y-1 min-h-[60px]">
      {#if ns.userIds.length > 0}
        {#each ns.userIds as uid}
          <div class="flex items-center justify-between bg-background cq-rounded px-2 py-1">
            <span class="cq-text font-mono">{uid}</span>
            <Button variant="ghost" size="icon" class="h-5 w-5" onclick={() => removeUserId(uid)} disabled={isRunning}>
              <Trash2 class="w-3 h-3 text-destructive" />
            </Button>
          </div>
        {/each}
      {:else}
        <div class="text-muted-foreground cq-text-sm text-center py-2">暂无用户</div>
      {/if}
    </div>
    <span class="cq-text-sm text-muted-foreground">共 {ns.userIds.length} 个用户</span>
  </div>
{/snippet}

{#snippet configBlock()}
  <div class="flex flex-col cq-gap h-full">
    <Label class="cq-text font-medium">爬取配置</Label>
    
    <div class="flex cq-gap items-center">
      <div class="flex-1">
        <Label class="cq-text-sm text-muted-foreground">起始日期</Label>
        <Input type="date" bind:value={ns.sinceDate} disabled={isRunning} class="cq-text" />
      </div>
      <div class="flex-1">
        <Label class="cq-text-sm text-muted-foreground">结束日期</Label>
        <Input type="text" bind:value={ns.endDate} placeholder="now" disabled={isRunning} class="cq-text" />
      </div>
    </div>
    
    <div class="space-y-2">
      <label class="flex items-center cq-gap cursor-pointer">
        <Checkbox bind:checked={ns.filterOriginal} disabled={isRunning} />
        <span class="cq-text">只爬取原创微博</span>
      </label>
      
      <label class="flex items-center cq-gap cursor-pointer">
        <Checkbox bind:checked={ns.picDownload} disabled={isRunning} />
        <Image class="cq-icon text-cyan-500" />
        <span class="cq-text">下载图片</span>
      </label>
      
      <label class="flex items-center cq-gap cursor-pointer">
        <Checkbox bind:checked={ns.videoDownload} disabled={isRunning} />
        <Video class="cq-icon text-purple-500" />
        <span class="cq-text">下载视频</span>
      </label>
    </div>
  </div>
{/snippet}

{#snippet cookieBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex items-center justify-between">
      <Label class="cq-text font-medium">Cookie</Label>
      <div class="flex items-center cq-gap">
        {#if ns.cookieValid}
          <span class="cq-text-sm text-green-500 flex items-center"><CircleCheck class="w-3 h-3 mr-1" />有效</span>
        {:else if ns.cookie}
          <span class="cq-text-sm text-yellow-500 flex items-center"><CircleX class="w-3 h-3 mr-1" />未验证</span>
        {/if}
      </div>
    </div>
    <Textarea 
      value={ns.cookie} 
      oninput={handleCookieInput}
      placeholder={'粘贴 Cookie 或 JSON 格式 {"cookie": "..."}'}
      class="cq-text flex-1 font-mono text-xs min-h-[60px]"
      disabled={isRunning}
    />
    <div class="flex cq-gap items-center">
      <select 
        bind:value={ns.browser}
        disabled={isRunning}
        class="cq-text h-8 px-2 rounded border border-input bg-background text-sm"
      >
        {#each browserOptions as opt}
          <option value={opt.value}>{opt.icon} {opt.label}</option>
        {/each}
      </select>
      <Button variant="outline" size="sm" class="cq-button-sm flex-1" onclick={getBrowserCookie} disabled={isRunning}>
        获取 Cookie
      </Button>
      <Button variant="outline" size="sm" class="cq-button-sm" onclick={validateCookie} disabled={isRunning || !ns.cookie}>
        验证
      </Button>
    </div>
  </div>
{/snippet}

{#snippet outputBlock()}
  <div class="flex flex-col cq-gap h-full">
    <Label class="cq-text font-medium">输出格式</Label>
    <div class="space-y-1">
      <label class="flex items-center cq-gap cursor-pointer">
        <input type="checkbox" checked={ns.writeMode.includes('json')} onchange={() => toggleWriteMode('json')} disabled={isRunning} class="w-4 h-4" />
        <FileJson class="cq-icon text-yellow-500" />
        <span class="cq-text-sm">JSON</span>
      </label>
      <label class="flex items-center cq-gap cursor-pointer">
        <input type="checkbox" checked={ns.writeMode.includes('csv')} onchange={() => toggleWriteMode('csv')} disabled={isRunning} class="w-4 h-4" />
        <FileText class="cq-icon text-green-500" />
        <span class="cq-text-sm">CSV</span>
      </label>
      <label class="flex items-center cq-gap cursor-pointer">
        <input type="checkbox" checked={ns.writeMode.includes('txt')} onchange={() => toggleWriteMode('txt')} disabled={isRunning} class="w-4 h-4" />
        <FileText class="cq-icon text-blue-500" />
        <span class="cq-text-sm">TXT</span>
      </label>
    </div>
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    {#if !isRunning}
      <Button class="w-full cq-button flex-1" onclick={handleStart} disabled={!canStart}>
        <Play class="cq-icon mr-1" />开始爬取
      </Button>
    {:else}
      <Button class="w-full cq-button flex-1" variant="destructive" onclick={handleStop}>
        <LoaderCircle class="cq-icon mr-1 animate-spin" />停止
      </Button>
    {/if}
    
    <div class="flex cq-gap">
      <Button variant="outline" class="flex-1 cq-button-sm" onclick={() => loadConfig()} disabled={isRunning}>
        <RefreshCw class="cq-icon mr-1" />加载
      </Button>
      <Button variant="outline" class="flex-1 cq-button-sm" onclick={importConfig} disabled={isRunning}>
        📥 导入
      </Button>
      <Button variant="outline" class="flex-1 cq-button-sm" onclick={exportConfig} disabled={isRunning}>
        📤 导出
      </Button>
    </div>
    
    {#if ns.phase !== 'idle'}
      <div class="space-y-1">
        <Progress value={ns.progress} class="h-1.5" />
        <span class="cq-text-sm text-muted-foreground">{ns.progressText}</span>
      </div>
    {/if}
    
    {#if ns.crawledWeibos > 0}
      <div class="cq-text-sm text-muted-foreground">
        👤 {ns.crawledUsers} 用户 | 📝 {ns.crawledWeibos} 微博
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
      {#if ns.logs.length > 0}
        {#each ns.logs.slice(-20) as logItem}<div class="text-muted-foreground break-all">{logItem}</div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === 'users'}{@render usersBlock()}
  {:else if blockId === 'config'}{@render configBlock()}
  {:else if blockId === 'cookie'}{@render cookieBlock()}
  {:else if blockId === 'output'}{@render outputBlock()}
  {:else if blockId === 'operation'}{@render operationBlock()}
  {:else if blockId === 'log'}{@render logBlock()}
  {/if}
{/snippet}

<div class="h-full w-full flex flex-col overflow-hidden" style={!isFullscreenRender ? 'max-width: 520px;' : ''}>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={400} minHeight={360} maxWidth={520} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper 
    nodeId={id} 
    title="微博爬虫" 
    icon={Users} 
    status={ns.phase} 
    {borderClass} 
    isFullscreenRender={isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="weibospider" 
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
        nodeId={id}
        nodeType="weibospider"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={WEIBOSPIDER_DEFAULT_GRID_LAYOUT}
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
