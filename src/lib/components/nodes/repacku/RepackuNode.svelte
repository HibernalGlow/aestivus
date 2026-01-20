<script lang="ts">
  /**
   * RepackuNode - 文件重打包节点组件
   * 使用 NodeLayoutRenderer 统一布局，支持节点模式和全屏模式
   */
  import { Handle, Position, NodeResizer } from "@xyflow/svelte";
  import { Button } from "$lib/components/ui/button";
  import { Checkbox } from "$lib/components/ui/checkbox";
  import { Input } from "$lib/components/ui/input";
  import { Progress } from "$lib/components/ui/progress";

  import { NodeLayoutRenderer } from "$lib/components/blocks";
  import { REPACKU_DEFAULT_GRID_LAYOUT } from "$lib/components/blocks/blockRegistry";
  import { api } from "$lib/services/api";
  import { getWsBaseUrl } from "$lib/stores/backend";
  import { getNodeState, saveNodeState } from "$lib/stores/nodeState.svelte";
  import NodeWrapper from "../NodeWrapper.svelte";
  import type { FolderNode, CompressionStats } from "$lib/types/repacku";
  import {
    getModeColorClass,
    getModeName,
    countCompressionModes,
  } from "./utils";
  import {
    Play,
    LoaderCircle,
    FolderOpen,
    Clipboard,
    Package,
    CircleCheck,
    CircleX,
    FileArchive,
    Search,
    FolderTree,
    Trash2,
    Copy,
    Check,
    Folder,
    Image,
    FileText,
    Video,
    Music,
    ChevronRight,
    ChevronDown,
    RotateCcw,
  } from "@lucide/svelte";
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu";

  interface Props {
    id: string;
    data?: {
      config?: { path?: string; types?: string[]; delete_after?: boolean };
      status?: "idle" | "running" | "completed" | "error";
      hasInputConnection?: boolean;
      logs?: string[];
      label?: string;
      showTree?: boolean;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase =
    | "idle"
    | "analyzing"
    | "analyzed"
    | "compressing"
    | "completed"
    | "error";

  interface AnalysisResult {
    configPath: string;
    totalFolders: number;
    entireCount: number;
    selectiveCount: number;
    skipCount: number;
    folderTree?: FolderNode;
  }

  interface CompressionResultData {
    success: boolean;
    compressed: number;
    failed: number;
    total: number;
  }

  interface RepackuState {
    phase: Phase;
    progress: number;
    progressText: string;
    folderTree: FolderNode | null;
    analysisResult: AnalysisResult | null;
    compressionResult: CompressionResultData | null;
    selectedTypes: string[];
    expandedFolders: string[];
    path: string;
    deleteAfter: boolean;
    logs: string[];
    hasInputConnection: boolean;
  }

  // 使用 $derived 确保响应式
  const nodeId = $derived(id);
  const configPath = $derived(data?.config?.path ?? "");
  const configDeleteAfter = $derived(data?.config?.delete_after ?? false);
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 获取共享的响应式状态
  const ns = getNodeState<RepackuState>(id, {
    phase: "idle",
    progress: 0,
    progressText: "",
    folderTree: null,
    analysisResult: null,
    compressionResult: null,
    selectedTypes: [],
    expandedFolders: [],
    path: configPath || "",
    deleteAfter: configDeleteAfter,
    logs: [],
    hasInputConnection: false,
  });

  // 本地 UI 状态
  let copied = $state(false);
  let layoutRenderer = $state<any>(undefined);
  // ws removed from state

  // 文件树统计（派生状态）
  let stats = $state<CompressionStats>({
    total: 0,
    entire: 0,
    selective: 0,
    skip: 0,
  });
  let expandedFoldersSet = $state<Set<string>>(new Set());

  // 同步 configPath
  $effect(() => {
    if (configPath && !ns.path) {
      ns.path = configPath;
    }
  });

  // 同步外部数据
  $effect(() => {
    if (dataLogs.length > 0) {
      ns.logs = [...dataLogs];
    }
    ns.hasInputConnection = dataHasInputConnection;
  });

  // 同步 expandedFolders
  $effect(() => {
    expandedFoldersSet = new Set(ns.expandedFolders);
  });

  const typeOptions = [
    { value: "image", label: "图片" },
    { value: "document", label: "文档" },
    { value: "video", label: "视频" },
    { value: "audio", label: "音频" },
  ];

  // 响应式派生值
  let canAnalyze = $derived(
    ns.phase === "idle" && (ns.path.trim() !== "" || ns.hasInputConnection),
  );
  let canCompress = $derived(
    ns.phase === "analyzed" && ns.analysisResult !== null,
  );
  let isRunning = $derived(
    ns.phase === "analyzing" || ns.phase === "compressing",
  );
  let borderClass = $derived(
    {
      idle: "border-border",
      analyzing: "border-primary shadow-sm",
      analyzed: "border-primary/50",
      compressing: "border-primary shadow-sm",
      completed: "border-primary/50",
      error: "border-destructive/50",
    }[ns.phase],
  );

  // 状态变化时自动保存
  $effect(() => {
    ns.phase;
    ns.folderTree;
    ns.analysisResult;
    ns.compressionResult;
    saveNodeState(nodeId);
  });

  // 当 folderTree 更新时，重新计算统计
  $effect(() => {
    if (ns.folderTree) stats = countCompressionModes(ns.folderTree);
  });

  function log(msg: string) {
    ns.logs = [...ns.logs.slice(-30), msg];
  }

  function toggleFolder(folderPath: string) {
    if (expandedFoldersSet.has(folderPath))
      expandedFoldersSet.delete(folderPath);
    else expandedFoldersSet.add(folderPath);
    expandedFoldersSet = new Set(expandedFoldersSet);
    ns.expandedFolders = Array.from(expandedFoldersSet);
  }

  async function selectFolder() {
    try {
      const { platform } = await import("$lib/api/platform");
      const selected = await platform.openFolderDialog("选择文件夹");
      if (selected) ns.path = selected;
    } catch (e) {
      log(`选择文件夹失败: ${e}`);
    }
  }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import("$lib/api/platform");
      const text = await platform.readClipboard();
      if (text) ns.path = text.trim();
    } catch (e) {
      log(`读取剪贴板失败: ${e}`);
    }
  }

  function toggleType(type: string) {
    if (ns.selectedTypes.includes(type))
      ns.selectedTypes = ns.selectedTypes.filter((t) => t !== type);
    else ns.selectedTypes = [...ns.selectedTypes, type];
  }

  async function handleAnalyze() {
    if (!canAnalyze) return;
    ns.phase = "analyzing";
    ns.progress = 0;
    ns.progressText = "正在扫描目录结构...";
    ns.analysisResult = null;
    ns.compressionResult = null;
    ns.folderTree = null;
    log(`🔍 开始分析目录: ${ns.path}`);
    if (ns.selectedTypes.length > 0)
      log(`📋 类型过滤: ${ns.selectedTypes.join(", ")}`);

    try {
      ns.progress = 30;
      ns.progressText = "正在分析文件类型分布...";
      const response = (await api.executeNode("repacku", {
        action: "analyze",
        path: ns.path,
        types: ns.selectedTypes.length > 0 ? ns.selectedTypes : [],
        display_tree: true,
      })) as any;

      if (response.success && response.data) {
        ns.phase = "analyzed";
        ns.progress = 100;
        ns.progressText = "分析完成";
        ns.folderTree = response.data.folder_tree || null;
        ns.analysisResult = {
          configPath: response.data.config_path ?? "",
          totalFolders: response.data.total_folders ?? 0,
          entireCount: response.data.entire_count ?? 0,
          selectiveCount: response.data.selective_count ?? 0,
          skipCount: response.data.skip_count ?? 0,
          folderTree: response.data.folder_tree,
        };
        log(`✅ 分析完成`);
        log(
          `📊 整体压缩: ${ns.analysisResult.entireCount}, 选择性: ${ns.analysisResult.selectiveCount}, 跳过: ${ns.analysisResult.skipCount}`,
        );
      } else {
        ns.phase = "error";
        ns.progress = 0;
        log(`❌ 分析失败: ${response.message}`);
      }
    } catch (error) {
      ns.phase = "error";
      ns.progress = 0;
      log(`❌ 分析失败: ${error}`);
    }
  }

  async function handleCompress() {
    if (!canCompress || !ns.analysisResult) return;
    ns.phase = "compressing";
    ns.progress = 0;
    ns.progressText = "正在压缩文件...";
    log(`📦 开始压缩...`);

    // 生成任务 ID 并建立 WebSocket 连接
    const taskId = `repacku-${nodeId}-${Date.now()}`;
    let ws: WebSocket | null = null;

    try {
      const wsUrl = `${getWsBaseUrl()}/v1/ws/tasks/${taskId}`;
      console.log("[Repacku] Connecting to WebSocket:", wsUrl);
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          console.log("[Repacku] WS Message:", msg);
          if (msg.type === "progress" && ns.phase === "compressing") {
            ns.progress = msg.progress;
            ns.progressText = msg.message;
          }
        } catch (e) {
          /* ignore parse errors */
        }
      };

      ws.onerror = (e) => {
        console.error("[Repacku] WebSocket error event:", e);
      };

      // 等待 WebSocket 连接成功（最多 2 秒）
      await new Promise<void>((resolve) => {
        const timeout = setTimeout(() => {
          log("⚠️ WebSocket 连接超时");
          resolve();
        }, 2000);

        ws!.onopen = () => {
          clearTimeout(timeout);
          log("✅ WebSocket 已连接");
          resolve();
        };

        ws!.onerror = () => {
          clearTimeout(timeout);
          log("⚠️ WebSocket 连接错误");
          resolve();
        };
      });
    } catch (err) {
      console.error("[Repacku] WebSocket initialization failed:", err);
      log("⚠️ WebSocket 初始化失败");
    }

    try {
      ns.progress = 10;
      const response = (await api.executeNode(
        "repacku",
        {
          action: "compress",
          config_path: ns.analysisResult.configPath,
          delete_after: ns.deleteAfter,
        },
        { taskId, nodeId },
      )) as any;

      // 关闭 WebSocket
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }

      if (response.success) {
        ns.phase = "completed";
        ns.progress = 100;
        ns.progressText = "压缩完成";
        ns.compressionResult = {
          success: true,
          compressed: response.data?.compressed_count ?? 0,
          failed: response.data?.failed_count ?? 0,
          total: response.data?.total_folders ?? 0,
        };
        log(`✅ ${response.message}`);
        log(
          `📊 成功: ${ns.compressionResult.compressed}, 失败: ${ns.compressionResult.failed}`,
        );
      } else {
        ns.phase = "error";
        ns.progress = 0;
        log(`❌ 压缩失败: ${response.message}`);
      }
    } catch (error) {
      if (ws) {
        ws.close();
        ws = null;
      }
      ns.phase = "error";
      ns.progress = 0;
      log(`❌ 压缩失败: ${error}`);
    }
  }

  function handleReset() {
    ns.phase = "idle";
    ns.progress = 0;
    ns.progressText = "";
    ns.analysisResult = null;
    ns.compressionResult = null;
    ns.folderTree = null;
    ns.logs = [];
    expandedFoldersSet.clear();
    ns.expandedFolders = [];
  }

  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(ns.logs.join("\n"));
      copied = true;
      setTimeout(() => {
        copied = false;
      }, 2000);
    } catch (e) {
      console.error("复制失败:", e);
    }
  }

  function getFileTypeIcon(type: string) {
    switch (type.toLowerCase()) {
      case "image":
        return Image;
      case "document":
        return FileText;
      case "video":
        return Video;
      case "audio":
        return Music;
      default:
        return FileText;
    }
  }
</script>

<!-- 递归渲染文件夹树节点 -->
{#snippet renderFolderNode(node: FolderNode, depth: number = 0)}
  {@const isExpanded = expandedFoldersSet.has(node.path)}
  {@const hasChildren = node.children && node.children.length > 0}
  {@const modeColor = getModeColorClass(node.compress_mode)}
  {@const modeText = getModeName(node.compress_mode)}

  <div class="select-none">
    <div
      class="flex items-center gap-1 py-0.5 px-1 rounded hover:bg-muted/50 cursor-pointer text-xs"
      style="padding-left: {depth * 12}px"
      onclick={() => hasChildren && toggleFolder(node.path)}
      onkeydown={(e) =>
        e.key === "Enter" && hasChildren && toggleFolder(node.path)}
      role="button"
      tabindex="0"
    >
      {#if hasChildren}
        {#if isExpanded}<ChevronDown
            class="w-3 h-3 text-muted-foreground shrink-0"
          />
        {:else}<ChevronRight
            class="w-3 h-3 text-muted-foreground shrink-0"
          />{/if}
      {:else}<span class="w-3 h-3 shrink-0"></span>{/if}

      <Folder class="w-3 h-3 text-yellow-500 shrink-0" />
      <span class="w-2 h-2 rounded-full shrink-0 {modeColor}" title={modeText}
      ></span>
      <span class="truncate flex-1" title={node.name}>{node.name}</span>
      <span class="text-muted-foreground shrink-0">{node.total_files}</span>

      {#if node.dominant_types && node.dominant_types.length > 0}
        <div class="flex gap-0.5 shrink-0">
          {#each node.dominant_types.slice(0, 2) as type}
            {@const IconComponent = getFileTypeIcon(type)}
            <IconComponent class="w-3 h-3 text-muted-foreground" />
          {/each}
        </div>
      {/if}
    </div>

    {#if hasChildren && isExpanded}
      {#each node.children as child}
        {@render renderFolderNode(child, depth + 1)}
      {/each}
    {/if}
  </div>
{/snippet}

<!-- ========== 区块内容 Snippets（使用 Container Query CSS） ========== -->

<!-- 路径输入区块 -->
{#snippet pathBlock()}
  {#if !ns.hasInputConnection}
    <div class="flex cq-gap cq-mb">
      <Input
        bind:value={ns.path}
        placeholder="输入或选择文件夹路径..."
        disabled={isRunning}
        class="flex-1 cq-input"
      />
      <Button
        variant="outline"
        size="icon"
        class="cq-button-icon shrink-0"
        onclick={selectFolder}
        disabled={isRunning}
      >
        <FolderOpen class="cq-icon" />
      </Button>
      <Button
        variant="outline"
        size="icon"
        class="cq-button-icon shrink-0"
        onclick={pasteFromClipboard}
        disabled={isRunning}
      >
        <Clipboard class="cq-icon" />
      </Button>
    </div>
  {:else}
    <div
      class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-mb cq-text"
    >
      <span>←</span><span>输入来自上游节点</span>
    </div>
  {/if}
{/snippet}

<!-- 类型过滤区块 -->
{#snippet typesBlock()}
  <div class="flex flex-wrap cq-gap">
    {#each typeOptions as option}
      <button
        class="cq-px cq-py cq-text cq-rounded border transition-colors {ns.selectedTypes.includes(
          option.value,
        )
          ? 'bg-primary text-primary-foreground border-primary'
          : 'bg-background border-border hover:border-primary'}"
        onclick={() => toggleType(option.value)}
        disabled={isRunning}>{option.label}</button
      >
    {/each}
  </div>
  <label
    class="cq-wide-only-flex items-center cq-gap mt-auto pt-3 border-t cursor-pointer"
  >
    <Checkbox
      id="delete-after-fs-{nodeId}"
      bind:checked={ns.deleteAfter}
      disabled={isRunning}
    />
    <span class="cq-text flex items-center gap-1"
      ><Trash2 class="cq-icon" />压缩后删除源文件</span
    >
  </label>
{/snippet}

<!-- 操作区块 -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 状态指示 -->
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if ns.compressionResult}
        {#if ns.compressionResult.success}
          <CircleCheck class="cq-icon text-green-500 shrink-0" />
          <span class="cq-text text-green-600 font-medium">完成</span>
          <span class="cq-text-sm text-muted-foreground ml-auto"
            >{ns.compressionResult.compressed} 成功</span
          >
        {:else}
          <CircleX class="cq-icon text-red-500 shrink-0" />
          <span class="cq-text text-red-600 font-medium">失败</span>
        {/if}
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1"><Progress value={ns.progress} class="h-1.5" /></div>
        <span class="cq-text-sm text-muted-foreground">{ns.progress}%</span>
      {:else}
        <Package class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待扫描</span>
      {/if}
    </div>
    <!-- 主按钮 -->
    {#if ns.phase === "idle" || ns.phase === "error"}
      <Button
        class="w-full cq-button flex-1"
        onclick={handleAnalyze}
        disabled={!canAnalyze}
      >
        <Search class="cq-icon mr-1" /><span>扫描分析</span>
      </Button>
    {:else if ns.phase === "analyzing"}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span>分析中</span>
      </Button>
    {:else if ns.phase === "analyzed"}
      <Button
        class="w-full cq-button flex-1"
        onclick={handleCompress}
        disabled={!canCompress}
      >
        <FileArchive class="cq-icon mr-1" /><span>开始压缩</span>
      </Button>
    {:else if ns.phase === "compressing"}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span>压缩中</span>
      </Button>
    {:else if ns.phase === "completed"}
      <Button class="w-full cq-button flex-1" onclick={handleReset}>
        <Play class="cq-icon mr-1" /><span>重新开始</span>
      </Button>
    {/if}
    <!-- 辅助按钮 -->
    <div class="flex cq-gap">
      <Button
        variant="ghost"
        class="flex-1 cq-button-sm"
        onclick={handleReset}
        disabled={isRunning}
      >
        <RotateCcw class="cq-icon mr-1" />重置
      </Button>
      <!-- 紧凑模式下的删除选项 -->
      <label class="cq-compact-only-flex items-center gap-2 cursor-pointer">
        <Checkbox
          id="delete-after-compact-{nodeId}"
          bind:checked={ns.deleteAfter}
          disabled={isRunning}
          class="h-3 w-3"
        />
        <span class="cq-text-sm flex items-center gap-1"
          ><Trash2 class="cq-icon-sm text-orange-500" />删除源</span
        >
      </label>
    </div>
  </div>
{/snippet}

<!-- 统计区块 -->
{#snippet statsBlock()}
  <div class="grid grid-cols-3 cq-gap">
    <div class="cq-stat-card bg-green-500/10">
      <div class="flex flex-col items-center">
        <span class="cq-stat-value text-green-600 tabular-nums"
          >{ns.analysisResult?.entireCount ?? "-"}</span
        >
        <span class="cq-stat-label text-muted-foreground">整体</span>
      </div>
    </div>
    <div class="cq-stat-card bg-yellow-500/10">
      <div class="flex flex-col items-center">
        <span class="cq-stat-value text-yellow-600 tabular-nums"
          >{ns.analysisResult?.selectiveCount ?? "-"}</span
        >
        <span class="cq-stat-label text-muted-foreground">选择</span>
      </div>
    </div>
    <div class="cq-stat-card bg-muted/40">
      <div class="flex flex-col items-center">
        <span class="cq-stat-value text-gray-500 tabular-nums"
          >{ns.analysisResult?.skipCount ?? "-"}</span
        >
        <span class="cq-stat-label text-muted-foreground">跳过</span>
      </div>
    </div>
  </div>
{/snippet}

<!-- 进度/状态区块 -->
{#snippet progressBlock()}
  <div class="h-full flex items-center cq-gap">
    {#if ns.compressionResult}
      {#if ns.compressionResult.success}
        <CircleCheck class="cq-icon-lg text-green-500 shrink-0" />
        <div class="flex-1">
          <span class="font-semibold text-green-600 cq-text">压缩完成</span>
          <div class="flex cq-gap cq-text-sm mt-1">
            <span class="text-green-600"
              >成功: {ns.compressionResult.compressed}</span
            >
            <span class="text-red-600">失败: {ns.compressionResult.failed}</span
            >
          </div>
        </div>
      {:else}
        <CircleX class="cq-icon-lg text-red-500 shrink-0" />
        <span class="font-semibold text-red-600 cq-text">压缩失败</span>
      {/if}
    {:else if isRunning}
      <LoaderCircle class="cq-icon-lg text-primary animate-spin shrink-0" />
      <div class="flex-1">
        <div class="flex justify-between cq-text-sm mb-1">
          <span>{ns.progressText}</span><span>{ns.progress}%</span>
        </div>
        <Progress value={ns.progress} class="h-2" />
      </div>
    {:else}
      <Package class="cq-icon-lg text-muted-foreground/50 shrink-0" />
      <div class="flex-1">
        <span class="text-muted-foreground cq-text">等待扫描</span>
        <div class="cq-text-sm text-muted-foreground/70 mt-1">
          扫描完成后可开始压缩
        </div>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 文件树区块 -->
{#snippet treeBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold flex items-center gap-1">
        <FolderTree class="cq-icon text-yellow-500" />文件树
      </span>
      <div class="flex items-center cq-gap cq-text-sm">
        <span class="flex items-center gap-0.5"
          ><span class="w-1.5 h-1.5 rounded-full bg-green-500"
          ></span>{stats.entire}</span
        >
        <span class="flex items-center gap-0.5"
          ><span class="w-1.5 h-1.5 rounded-full bg-yellow-500"
          ></span>{stats.selective}</span
        >
        <span class="flex items-center gap-0.5"
          ><span class="w-1.5 h-1.5 rounded-full bg-gray-400"
          ></span>{stats.skip}</span
        >
      </div>
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
      {#if ns.folderTree}{@render renderFolderNode(ns.folderTree)}
      {:else}<div class="cq-text text-muted-foreground text-center py-3">
          扫描后显示
        </div>{/if}
    </div>
  </div>
{/snippet}

<!-- 日志区块 -->
{#snippet logBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">日志</span>
      <Button variant="ghost" size="icon" class="h-5 w-5" onclick={copyLogs}>
        {#if copied}<Check class="w-3 h-3 text-green-500" />{:else}<Copy
            class="w-3 h-3"
          />{/if}
      </Button>
    </div>
    <div
      class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding font-mono cq-text-sm space-y-0.5"
    >
      {#if ns.logs.length > 0}
        {#each ns.logs.slice(-10) as logItem}<div
            class="text-muted-foreground break-all"
          >
            {logItem}
          </div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 通用区块渲染器 -->
{#snippet renderBlockContent(blockId: string)}
  {#if blockId === "path"}{@render pathBlock()}{@render typesBlock()}
  {:else if blockId === "types"}{@render typesBlock()}
  {:else if blockId === "operation"}{@render operationBlock()}
  {:else if blockId === "stats"}{@render statsBlock()}
  {:else if blockId === "progress"}{@render progressBlock()}
  {:else if blockId === "tree"}{@render treeBlock()}
  {:else if blockId === "log"}{@render logBlock()}
  {/if}
{/snippet}

<!-- ========== 主渲染 ========== -->
<div
  class="h-full w-full flex flex-col overflow-hidden"
  style={!isFullscreenRender ? "max-width: 400px;" : ""}
>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={200} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper
    {nodeId}
    title="repacku"
    icon={Package}
    status={ns.phase}
    {borderClass}
    {isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="repacku"
    currentLayout={layoutRenderer?.getCurrentLayout()}
    currentTabGroups={layoutRenderer?.getCurrentTabGroups()}
    onApplyLayout={(layout, tabGroups) =>
      layoutRenderer?.applyLayout(layout, tabGroups)}
    canCreateTab={true}
    onCreateTab={(blockIds) => layoutRenderer?.createTab(blockIds)}
    layoutMode={isFullscreenRender ? "fullscreen" : "normal"}
    menuItems={nodeMenuItems}
  >
    {#snippet nodeMenuItems(DefaultItems: any)}
      <DropdownMenu.Item
        onclick={handleAnalyze}
        disabled={!canAnalyze || isRunning}
      >
        <Search class="mr-2 h-4 w-4" />
        <span>扫描分析</span>
      </DropdownMenu.Item>
      <DropdownMenu.Item
        onclick={handleCompress}
        disabled={!canCompress || isRunning}
      >
        <FileArchive class="mr-2 h-4 w-4" />
        <span>开始压缩</span>
      </DropdownMenu.Item>
      <DropdownMenu.Separator />
      <DropdownMenu.Item onclick={handleReset} disabled={isRunning}>
        <RotateCcw class="mr-2 h-4 w-4" />
        <span>重置状态</span>
      </DropdownMenu.Item>
      <DropdownMenu.Separator />
      {@render DefaultItems()}
    {/snippet}

    {#snippet children()}
      <NodeLayoutRenderer
        bind:this={layoutRenderer}
        {nodeId}
        nodeType="repacku"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={REPACKU_DEFAULT_GRID_LAYOUT}
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
