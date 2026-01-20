<script lang="ts">
  /**
   * FindzNode - 文件搜索节点组件
   *
   * 使用 Container Query 自动响应尺寸
   * - 一套 HTML 结构，CSS 控制尺寸变化
   * - 紧凑模式保留核心功能，详细操作在全屏
   * - 支持 WebSocket 实时进度显示
   */
  import { Handle, Position, NodeResizer } from "@xyflow/svelte";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { Progress } from "$lib/components/ui/progress";
  import { onDestroy } from "svelte";

  import { NodeLayoutRenderer } from "$lib/components/blocks";
  import type { GridItem } from "$lib/components/ui/dashboard-grid";
  import type { NodeConfig, LayoutMode } from "$lib/stores/nodeLayoutStore";
  import { FINDZ_DEFAULT_GRID_LAYOUT } from "$lib/components/blocks/blockRegistry";
  import { api } from "$lib/services/api";
  import { getNodeState, saveNodeState } from "$lib/stores/nodeState.svelte";
  import { getWsBaseUrl } from "$lib/stores/backend";
  import NodeWrapper from "../NodeWrapper.svelte";
  import FilterBuilder from "./FilterBuilder.svelte";
  import AnalysisPanel from "./AnalysisPanel.svelte";
  import type { FileData, SearchResult, FindzNodeState } from "./types";
  import {
    Search,
    LoaderCircle,
    FolderOpen,
    Clipboard,
    CircleCheck,
    CircleX,
    File,
    Folder,
    Archive,
    Copy,
    Check,
    RotateCcw,
    Package,
    Layers,
    Image,
    Plus,
    X,
    Trash2,
    ChevronDown,
    ChevronRight,
    Sparkles,
  } from "@lucide/svelte";
  import {
    buildCompleteFileTree,
    calculateSmartExpansion,
    type TreeNode,
  } from "$lib/utils/treeUtils";

  /** NodeLayoutRenderer 组件实例类型 */
  interface LayoutRendererInstance {
    compact: () => void;
    resetLayout: () => Promise<void>;
    getCurrentLayout: () => GridItem[];
    getCurrentTabGroups: () => {
      id: string;
      blockIds: string[];
      activeIndex: number;
    }[];
    applyLayout: (
      layout: GridItem[],
      tabGroups?:
        | { id: string; blockIds: string[]; activeIndex: number }[]
        | null,
    ) => Promise<void>;
    createTab: (blockIds: string[]) => Promise<string | null>;
    getCurrentMode: () => LayoutMode;
    getConfig: () => NodeConfig;
  }

  interface Props {
    id: string;
    data?: {
      config?: { path?: string; where?: string };
      status?: "idle" | "running" | "completed" | "error";
      hasInputConnection?: boolean;
      logs?: string[];
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = "idle" | "searching" | "completed" | "error";
  type Action = "search" | "nested" | "archives_only";

  // 使用 $derived 确保响应式
  const nodeId = $derived(id);
  const configPath = $derived(data?.config?.path ?? ".");
  const configWhere = $derived(data?.config?.where ?? "1");
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 获取共享的响应式状态
  const ns = getNodeState<FindzNodeState>(id, {
    phase: "idle",
    progress: 0,
    searchResult: null,
    files: [],
    byExtension: {},
    targetPath: configPath || ".",
    targetPaths: [],
    whereClause: configWhere || "1",
    logs: [],
    withImageMeta: false,
  });

  // 本地 UI 状态
  let hasInputConnection = $state(false);
  let layoutRenderer = $state<LayoutRendererInstance | undefined>(undefined);
  let advancedMode = $state(false);
  let pathInput = $state(""); // 新路径输入框

  // 实时进度状态（不需要持久化）
  let progressMessage = $state("");
  let scannedCount = $state(0);
  let matchedCount = $state(0);
  let elapsedTime = $state(0);

  // WebSocket 连接（本地状态）
  let ws: WebSocket | null = null;
  let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null;

  // 复制状态
  let copiedLogs = $state(false);
  let copiedPath = $state(false);

  // 文件树展开状态
  let expandedArchives = $state<Set<string>>(new Set());
  let autoExpandApplied = $state(false);

  // 同步外部状态
  $effect(() => {
    if (dataLogs.length > 0) ns.logs = [...dataLogs];
    hasInputConnection = dataHasInputConnection;

    // 初始化：如果 targetPaths 为空但 targetPath 有值，迁移到 targetPaths
    if (ns.targetPaths.length === 0 && ns.targetPath && ns.targetPath !== ".") {
      ns.targetPaths = [ns.targetPath];
    }
  });

  // WebSocket 连接管理
  function connectWebSocket(tid: string) {
    if (ws) {
      ws.close();
    }

    // WebSocket 路由在 /v1 前缀下
    const wsUrl = `${getWsBaseUrl()}/v1/ws/tasks/${tid}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      log("📡 WebSocket 已连接");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "progress") {
          ns.progress = msg.progress;
          progressMessage = msg.message || "";

          const match = msg.message?.match(/(\d+)\s*文件.*?(\d+)\s*匹配/);
          if (match) {
            scannedCount = parseInt(match[1], 10);
            matchedCount = parseInt(match[2], 10);
          }
        } else if (msg.type === "log") {
          log(msg.message);
        } else if (msg.type === "status") {
          if (msg.status === "completed") {
            ns.phase = "completed";
            ns.progress = 100;
          } else if (msg.status === "error") {
            ns.phase = "error";
          }
        }
      } catch (e) {
        console.error("WebSocket 消息解析失败:", e);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket 错误:", error);
    };

    ws.onclose = () => {
      ws = null;
    };
  }

  function disconnectWebSocket() {
    if (ws) {
      ws.close();
      ws = null;
    }
    if (wsReconnectTimer) {
      clearTimeout(wsReconnectTimer);
      wsReconnectTimer = null;
    }
  }

  // 组件卸载时清理
  onDestroy(() => {
    disconnectWebSocket();
  });

  let canExecute = $derived(
    ns.phase === "idle" && (ns.targetPaths.length > 0 || hasInputConnection),
  );
  let isRunning = $derived(ns.phase === "searching");
  let borderClass = $derived(
    {
      idle: "border-border",
      searching: "border-blue-500 shadow-sm",
      completed: "border-primary/50",
      error: "border-destructive/50",
    }[ns.phase],
  );

  function log(msg: string) {
    ns.logs = [...ns.logs.slice(-30), msg];
  }

  async function selectFolder() {
    try {
      const { platform } = await import("$lib/api/platform");
      const selected = await platform.openFolderDialog("选择搜索目录");
      if (selected) {
        // 添加到路径列表
        if (!ns.targetPaths.includes(selected)) {
          ns.targetPaths = [...ns.targetPaths, selected];
        }
      }
    } catch (e) {
      log(`选择文件夹失败: ${e}`);
    }
  }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import("$lib/api/platform");
      const text = await platform.readClipboard();
      if (text) {
        // 智能解析多路径
        const paths = parseMultiplePaths(text);

        if (paths.length === 0) {
          // 如果解析失败，直接放入输入框
          pathInput = text.trim();
        } else if (paths.length === 1) {
          // 单个路径，放入输入框
          pathInput = paths[0];
        } else {
          // 多个路径，直接添加到列表
          let addedCount = 0;
          for (const path of paths) {
            if (!ns.targetPaths.includes(path)) {
              ns.targetPaths = [...ns.targetPaths, path];
              addedCount++;
            }
          }
          log(`📋 从剪贴板添加了 ${addedCount} 个路径`);
        }
      }
    } catch (e) {
      log(`读取剪贴板失败: ${e}`);
    }
  }

  // 解析多路径文本
  function parseMultiplePaths(text: string): string[] {
    const paths: string[] = [];

    // 按行分割
    const lines = text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line);

    for (const line of lines) {
      // 移除引号（支持双引号和单引号）
      let path = line.replace(/^["']|["']$/g, "").trim();

      // 验证是否是有效路径（Windows 或 Unix 路径格式）
      if (
        path &&
        (/^[a-zA-Z]:[\\\/]/.test(path) || // Windows 绝对路径 C:\ 或 C:/
          /^[\\\/]/.test(path) || // Unix 绝对路径 /
          /^\.\.?[\\\/]/.test(path) || // 相对路径 ./ 或 ../
          /^[^\\\/]+$/.test(path)) // 相对路径（无斜杠）
      ) {
        paths.push(path);
      }
    }

    return paths;
  }

  // 添加路径
  function addPath() {
    const text = pathInput.trim();
    if (!text) return;

    // 尝试解析多路径
    const paths = parseMultiplePaths(text);

    if (paths.length === 0) {
      // 解析失败，作为单个路径处理
      if (!ns.targetPaths.includes(text)) {
        ns.targetPaths = [...ns.targetPaths, text];
      }
    } else {
      // 批量添加
      let addedCount = 0;
      for (const path of paths) {
        if (!ns.targetPaths.includes(path)) {
          ns.targetPaths = [...ns.targetPaths, path];
          addedCount++;
        }
      }
      if (addedCount > 1) {
        log(`➕ 添加了 ${addedCount} 个路径`);
      }
    }

    pathInput = "";
  }

  // 移除路径
  function removePath(index: number) {
    ns.targetPaths = ns.targetPaths.filter((_, i) => i !== index);
  }

  // 清空所有路径
  function clearPaths() {
    ns.targetPaths = [];
  }

  async function executeAction(action: Action) {
    if (!canExecute) return;
    ns.phase = "searching";
    ns.progress = 0;
    progressMessage = "准备中...";
    scannedCount = 0;
    matchedCount = 0;
    elapsedTime = 0;

    // 生成任务 ID 并连接 WebSocket
    const newTaskId = `findz-${nodeId}-${Date.now()}`;
    connectWebSocket(newTaskId);

    // 使用多路径或单路径
    const paths =
      ns.targetPaths.length > 0 ? ns.targetPaths : [ns.targetPath || "."];
    log(`🔍 开始搜索: ${paths.join(", ")}`);

    // 计时器
    const startTime = Date.now();
    const timer = setInterval(() => {
      elapsedTime = (Date.now() - startTime) / 1000;
    }, 100);

    try {
      ns.progress = 10;
      const response = (await api.executeNode(
        "findz",
        {
          paths,
          where: ns.whereClause,
          action,
          long_format: true,
          max_results: 0,
          with_image_meta: ns.withImageMeta,
        },
        { taskId: newTaskId, nodeId },
      )) as any;

      if (response.logs) for (const m of response.logs) log(m);

      // 调试：打印完整响应
      console.log(
        "FindzNode response:",
        JSON.stringify(response, null, 2).slice(0, 2000),
      );

      if (response.success) {
        ns.phase = "completed";
        ns.progress = 100;

        // 兼容多种响应结构：
        // 1. response.data.xxx (标准结构)
        // 2. response.xxx (扁平结构)
        const data = response.data || response;

        // 获取文件列表 - 尝试多个位置
        const returnedFiles = data.files || response.files || [];

        ns.searchResult = {
          total_count: data.total_count ?? response.total_count ?? 0,
          file_count: data.file_count ?? response.file_count ?? 0,
          dir_count: data.dir_count ?? response.dir_count ?? 0,
          archive_count: data.archive_count ?? response.archive_count ?? 0,
          nested_count: data.nested_count ?? response.nested_count ?? 0,
        };

        log(
          `📊 返回文件数: ${returnedFiles.length}, 总计: ${ns.searchResult.total_count}`,
        );

        ns.files = returnedFiles;
        ns.byExtension = data.by_extension ?? response.by_extension ?? {};

        // 更新统计
        scannedCount =
          data.scanned_files ?? response.scanned_files ?? scannedCount;
        elapsedTime = data.elapsed_time ?? response.elapsed_time ?? elapsedTime;

        log(`✅ ${response.message}`);
      } else {
        ns.phase = "error";
        ns.progress = 0;
        log(`❌ 失败: ${response.message}`);
      }
    } catch (error) {
      ns.phase = "error";
      ns.progress = 0;
      log(`❌ 失败: ${error}`);
    } finally {
      clearInterval(timer);
      // 延迟断开 WebSocket，确保最后的消息能收到
      setTimeout(() => disconnectWebSocket(), 1000);
    }
  }

  function handleReset() {
    ns.phase = "idle";
    ns.progress = 0;
    ns.searchResult = null;
    ns.files = [];
    ns.byExtension = {};
    ns.logs = [];
  }

  async function copyToClipboard(text: string, setter: (v: boolean) => void) {
    try {
      await navigator.clipboard.writeText(text);
      setter(true);
      setTimeout(() => setter(false), 2000);
    } catch (e) {
      console.error("复制失败:", e);
    }
  }

  function getOutsideArchiveCount(): number {
    return ns.files.filter((f) => !f.archive && !f.container).length;
  }

  // --- 文件树逻辑 ---
  const filePaths = $derived(
    ns.files.map((f) => (f.container ? `${f.container}//${f.path}` : f.path)),
  );

  // 切换压缩包展开状态
  function toggleArchive(archive: string) {
    if (expandedArchives.has(archive)) {
      expandedArchives.delete(archive);
    } else {
      expandedArchives.add(archive);
    }
    expandedArchives = new Set(expandedArchives);
  }

  // 应用智能展开
  function applySmartExpansion() {
    if (ns.files.length === 0) return;

    const tree = buildCompleteFileTree(filePaths);
    const smartExpanded = calculateSmartExpansion(tree);
    expandedArchives = smartExpanded;
    autoExpandApplied = true;
    log(`✨ 智能展开: 已展开 ${smartExpanded.size} 个节点`);
  }

  // 全部展开
  function expandAll() {
    const tree = buildCompleteFileTree(filePaths);
    const allPaths = new Set<string>();

    function collectPaths(node: TreeNode) {
      if (node.path) {
        allPaths.add(node.path);
      }
      for (const child of node.children) {
        collectPaths(child);
      }
    }

    collectPaths(tree);
    expandedArchives = allPaths;
    log(`📂 全部展开: ${allPaths.size} 个节点`);
  }

  // 全部折叠
  function collapseAll() {
    expandedArchives.clear();
    expandedArchives = new Set();
    log(`📁 全部折叠`);
  }

  // 当文件列表变化时，自动应用智能展开
  $effect(() => {
    if (ns.files.length > 0 && !autoExpandApplied) {
      applySmartExpansion();
    }
  });

  // 当重置时，重置展开状态
  $effect(() => {
    if (ns.files.length === 0) {
      autoExpandApplied = false;
    }
  });
</script>

<!-- ========== 统一 UI 结构的区块 ========== -->

<!-- 路径输入 -->
{#snippet pathBlock()}
  <div class="cq-mb h-full flex flex-col">
    <div class="flex items-center gap-1 mb-1 cq-text">
      <Search class="cq-icon" />
      <span class="font-medium">搜索路径</span>
      {#if ns.targetPaths.length > 0}
        <span class="text-xs text-muted-foreground"
          >({ns.targetPaths.length})</span
        >
      {/if}
    </div>
    {#if !hasInputConnection}
      <!-- 路径输入框 -->
      <div class="flex cq-gap mb-1">
        <textarea
          bind:value={pathInput}
          placeholder="输入路径（支持多行粘贴）..."
          disabled={isRunning}
          class="flex-1 cq-input resize-none"
          rows="1"
          onkeydown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              addPath();
            }
          }}
          oninput={(e) => {
            // 自动调整高度
            const target = e.target as HTMLTextAreaElement;
            target.style.height = "auto";
            target.style.height = Math.min(target.scrollHeight, 100) + "px";
          }}
        ></textarea>
        <Button
          variant="outline"
          size="icon"
          class="cq-button-icon shrink-0"
          onclick={addPath}
          disabled={isRunning || !pathInput.trim()}
        >
          <Plus class="cq-icon" />
        </Button>
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

      <!-- 路径列表 -->
      {#if ns.targetPaths.length > 0}
        <div
          class="flex-1 overflow-y-auto space-y-0.5 cq-padding bg-muted/30 cq-rounded"
        >
          {#each ns.targetPaths as path, index}
            <div
              class="flex items-center gap-1 cq-text-sm bg-background cq-rounded px-1.5 py-0.5 group"
            >
              <Folder class="w-3 h-3 text-yellow-500 shrink-0" />
              <span class="flex-1 truncate" title={path}>{path}</span>
              <button
                onclick={() => removePath(index)}
                disabled={isRunning}
                class="opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X
                  class="w-3 h-3 text-muted-foreground hover:text-destructive"
                />
              </button>
            </div>
          {/each}
        </div>
        <Button
          variant="ghost"
          size="sm"
          class="cq-button-sm mt-1 w-full"
          onclick={clearPaths}
          disabled={isRunning}
        >
          <Trash2 class="cq-icon mr-1" />清空
        </Button>
      {:else}
        <div
          class="cq-text-sm text-muted-foreground text-center py-2 bg-muted/30 cq-rounded"
        >
          添加一个或多个搜索路径
        </div>
      {/if}
    {:else}
      <div
        class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-text"
      >
        <span>←</span><span>输入来自上游节点</span>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 过滤器 -->
{#snippet filterBlock()}
  <div class="h-full flex flex-col overflow-auto">
    <FilterBuilder
      {advancedMode}
      sqlValue={ns.whereClause}
      onchange={(_, sql) => {
        ns.whereClause = sql;
      }}
      onAdvancedChange={(adv) => (advancedMode = adv)}
      onImageMetaChange={(enabled) => {
        ns.withImageMeta = enabled;
      }}
      disabled={isRunning}
    />
    <!-- 图片元数据开关 -->
    <div class="mt-2 pt-2 border-t">
      <label class="flex items-center gap-2 cursor-pointer cq-text-sm">
        <input
          type="checkbox"
          bind:checked={ns.withImageMeta}
          disabled={isRunning}
          class="rounded border-gray-300"
        />
        <Image class="w-3.5 h-3.5 text-blue-500" />
        <span>启用图片元数据</span>
      </label>
      {#if ns.withImageMeta}
        <div class="text-xs text-muted-foreground mt-1 ml-6">
          可用字段: width, height, resolution, megapixels, aspect
        </div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 操作按钮（含状态显示） -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 主按钮 -->
    <Button
      class="w-full cq-button flex-1"
      onclick={() => executeAction("search")}
      disabled={!canExecute || isRunning}
    >
      {#if isRunning}<LoaderCircle
          class="cq-icon mr-1 animate-spin"
        />{:else}<Search class="cq-icon mr-1" />{/if}
      <span>搜索</span>
    </Button>
    <!-- 辅助按钮 -->
    <div class="flex cq-gap">
      <Button
        variant="outline"
        class="flex-1 cq-button-sm"
        onclick={() => executeAction("archives_only")}
        disabled={!canExecute || isRunning}
      >
        <Archive class="cq-icon" /><span class="cq-wide-only ml-1">压缩包</span>
      </Button>
      <Button
        variant="outline"
        class="flex-1 cq-button-sm"
        onclick={() => executeAction("nested")}
        disabled={!canExecute || isRunning}
      >
        <Layers class="cq-icon" /><span class="cq-wide-only ml-1">嵌套</span>
      </Button>
      {#if ns.phase === "completed" || ns.phase === "error"}
        <Button
          variant="ghost"
          size="icon"
          class="cq-button-icon"
          onclick={handleReset}
        >
          <RotateCcw class="cq-icon" />
        </Button>
      {/if}
    </div>

    <!-- 进度条（在按钮下面） -->
    {#if isRunning || ns.phase === "completed" || ns.phase === "error"}
      <div class="flex flex-col cq-gap cq-padding bg-muted/30 cq-rounded">
        <div class="flex items-center cq-gap">
          {#if ns.phase === "completed"}
            <CircleCheck class="cq-icon text-green-500 shrink-0" />
            <span class="cq-text text-green-600 font-medium">完成</span>
            <span class="cq-text-sm text-muted-foreground ml-auto"
              >{ns.searchResult?.total_count ?? 0} 项</span
            >
          {:else if ns.phase === "error"}
            <CircleX class="cq-icon text-red-500 shrink-0" />
            <span class="cq-text text-red-600 font-medium">失败</span>
          {:else if isRunning}
            <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
            <div class="flex-1 flex flex-col gap-0.5">
              <Progress value={ns.progress} class="h-1.5" />
              <div
                class="flex items-center justify-between cq-text-sm text-muted-foreground"
              >
                <span class="truncate">{progressMessage || "搜索中..."}</span>
                <span class="tabular-nums shrink-0">{ns.progress}%</span>
              </div>
            </div>
          {/if}
        </div>

        <!-- 实时统计（搜索中显示） -->
        {#if isRunning && scannedCount > 0}
          <div
            class="flex items-center justify-between cq-text-sm text-muted-foreground border-t pt-1"
          >
            <span
              >扫描: <span class="tabular-nums text-foreground"
                >{scannedCount.toLocaleString()}</span
              ></span
            >
            <span
              >匹配: <span class="tabular-nums text-primary"
                >{matchedCount.toLocaleString()}</span
              ></span
            >
            <span class="tabular-nums">{elapsedTime.toFixed(1)}s</span>
          </div>
        {/if}
      </div>
    {/if}
  </div>
{/snippet}

<!-- 统计 -->
{#snippet statsBlock()}
  {@const outsideCount = getOutsideArchiveCount()}
  {#if ns.searchResult}
    <div class="grid grid-cols-2 cq-gap">
      <div class="cq-stat-card bg-blue-500/10 col-span-2">
        <div class="flex items-center justify-between">
          <span class="cq-stat-label text-muted-foreground">总计</span>
          <span class="cq-stat-value text-blue-600 tabular-nums"
            >{ns.searchResult.total_count}</span
          >
        </div>
      </div>
      <div class="cq-stat-card bg-green-500/10">
        <div class="flex items-center justify-between">
          <File class="cq-icon text-green-600" />
          <span class="cq-stat-value text-green-600 tabular-nums"
            >{outsideCount}</span
          >
        </div>
        <div class="cq-stat-label text-muted-foreground">文件系统</div>
      </div>
      <div class="cq-stat-card bg-purple-500/10">
        <div class="flex items-center justify-between">
          <Package class="cq-icon text-purple-600" />
          <span class="cq-stat-value text-purple-600 tabular-nums"
            >{ns.searchResult.archive_count}</span
          >
        </div>
        <div class="cq-stat-label text-muted-foreground">压缩包内</div>
      </div>
    </div>
    <!-- 扩展名统计（仅宽屏） -->
    {#if Object.keys(ns.byExtension).length > 0}
      <div class="cq-wide-only mt-2">
        <div class="text-xs text-muted-foreground mb-1">按扩展名</div>
        <div class="flex flex-wrap gap-1">
          {#each Object.entries(ns.byExtension)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 8) as [ext, count]}
            <span class="text-xs px-1.5 py-0.5 bg-muted rounded"
              >.{ext || "无"}: {count}</span
            >
          {/each}
        </div>
      </div>
    {/if}
  {:else}
    <div class="cq-text text-muted-foreground text-center py-2">
      搜索后显示统计
    </div>
  {/if}
{/snippet}

<!-- 文件夹树渲染 -->
{#snippet renderTreeNode(node: TreeNode, depth: number = 0)}
  {@const isExpanded = expandedArchives.has(node.path)}
  {@const hasChildren = node.children && node.children.length > 0}

  <div class="select-none">
    <div
      class="flex items-center gap-1 py-0.5 px-1 rounded hover:bg-muted/50 cursor-pointer text-xs"
      style="padding-left: {depth * 12}px"
      onclick={() => hasChildren && toggleArchive(node.path)}
      onkeydown={(e) =>
        e.key === "Enter" && hasChildren && toggleArchive(node.path)}
      role="button"
      tabindex="0"
    >
      {#if hasChildren}
        {#if isExpanded}
          <ChevronDown class="w-3 h-3 text-muted-foreground shrink-0" />
        {:else}
          <ChevronRight class="w-3 h-3 text-muted-foreground shrink-0" />
        {/if}
      {:else}
        <span class="w-3 h-3 shrink-0"></span>
      {/if}

      {#if node.isArchive}
        <Package class="w-3 h-3 text-purple-500 shrink-0" />
      {:else if node.isFolder}
        <span class="text-yellow-500 shrink-0">📁</span>
      {:else}
        <File class="w-3 h-3 text-blue-500 shrink-0" />
      {/if}

      <span class="truncate flex-1" title={node.path}>{node.name}</span>

      {#if !node.isFolder && !node.isArchive && node.fileIndex !== undefined}
        {@const file = ns.files[node.fileIndex]}
        {#if file}
          {#if file.resolution && ns.withImageMeta}
            <span class="cq-text-sm text-blue-600 shrink-0 font-mono"
              >{file.resolution}</span
            >
          {/if}
          <span class="cq-text-sm text-muted-foreground shrink-0"
            >{file.size_formatted}</span
          >
        {/if}
      {:else if hasChildren}
        <span class="text-muted-foreground shrink-0 text-xs"
          >{node.children.length}</span
        >
      {/if}
    </div>

    {#if hasChildren && isExpanded}
      {#each node.children as child}
        {@render renderTreeNode(child, depth + 1)}
      {/each}
    {/if}
  </div>
{/snippet}

<!-- 文件树 -->
{#snippet treeBlock()}
  {@const fileTree = buildCompleteFileTree(filePaths)}
  {@const totalCount = ns.searchResult?.total_count ?? ns.files.length}
  <div class="h-full flex flex-col overflow-hidden">
    <div
      class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0"
    >
      <span class="cq-text font-semibold flex items-center gap-1">
        <Folder class="cq-icon text-yellow-500" />文件树
      </span>
      <div class="flex items-center cq-gap">
        <span class="cq-text-sm text-muted-foreground">
          {#if totalCount > ns.files.length}
            {ns.files.length.toLocaleString()}/{totalCount.toLocaleString()}
          {:else}
            {ns.files.length.toLocaleString()}
          {/if}
        </span>
        <div class="flex items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon"
            class="h-5 w-5"
            onclick={applySmartExpansion}
            title="智能展开"
          >
            <Sparkles class="w-3 h-3 text-yellow-500" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            class="h-5 w-5"
            onclick={expandAll}
            title="全部展开"
          >
            <ChevronDown class="w-3 h-3" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            class="h-5 w-5"
            onclick={collapseAll}
            title="全部折叠"
          >
            <ChevronRight class="w-3 h-3" />
          </Button>

          {#if ns.files.length > 0}
            <Button
              variant="ghost"
              size="icon"
              class="h-5 w-5"
              onclick={() =>
                copyToClipboard(
                  ns.files
                    .map((f) =>
                      f.container ? `${f.container}//${f.path}` : f.path,
                    )
                    .join("\n"),
                  (v) => (copiedPath = v),
                )}
              title="复制路径"
            >
              {#if copiedPath}<Check
                  class="w-3 h-3 text-green-500"
                />{:else}<Copy class="w-3 h-3" />{/if}
            </Button>
          {/if}
        </div>
      </div>
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
      {#if ns.files.length > 0}
        {#each fileTree.children as child}
          {@render renderTreeNode(child)}
        {/each}
        {#if ns.files.length > 500}
          <div
            class="cq-text-sm text-muted-foreground text-center py-2 border-t mt-1"
          >
            共 {ns.files.length.toLocaleString()} 条
            {#if totalCount > ns.files.length}
              <br /><span class="text-orange-500"
                >（总计 {totalCount.toLocaleString()} 条，已截断）</span
              >
            {/if}
          </div>
        {/if}
      {:else}
        <div class="cq-text text-muted-foreground text-center py-4">
          搜索后显示
        </div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 日志 -->
{#snippet logBlock()}
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">日志</span>
      <Button
        variant="ghost"
        size="icon"
        class="h-5 w-5"
        onclick={() =>
          copyToClipboard(ns.logs.join("\n"), (v) => (copiedLogs = v))}
      >
        {#if copiedLogs}<Check class="w-3 h-3 text-green-500" />{:else}<Copy
            class="w-3 h-3"
          />{/if}
      </Button>
    </div>
    <div
      class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding font-mono cq-text-sm space-y-0.5"
    >
      {#if ns.logs.length > 0}
        {#each ns.logs.slice(-10) as logItem}
          <div class="text-muted-foreground break-all">{logItem}</div>
        {/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">暂无日志</div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 分析面板 -->
{#snippet analysisBlock()}
  <AnalysisPanel files={ns.files} />
{/snippet}

<!-- 区块渲染器 -->
{#snippet renderBlockContent(blockId: string)}
  {#if blockId === "path"}{@render pathBlock()}
  {:else if blockId === "filter"}{@render filterBlock()}
  {:else if blockId === "operation"}{@render operationBlock()}
  {:else if blockId === "stats"}{@render statsBlock()}
  {:else if blockId === "log"}{@render logBlock()}
  {:else if blockId === "tree"}{@render treeBlock()}
  {:else if blockId === "analysis"}{@render analysisBlock()}
  {/if}
{/snippet}

<!-- 主渲染 -->
<div
  class="h-full w-full flex flex-col overflow-hidden"
  style={!isFullscreenRender ? "max-width: 420px;" : ""}
>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={300} minHeight={380} maxWidth={420} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper
    {nodeId}
    title="findz"
    icon={Search}
    status={ns.phase}
    {borderClass}
    {isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="findz"
    currentLayout={layoutRenderer?.getCurrentLayout()}
    currentTabGroups={layoutRenderer?.getCurrentTabGroups()}
    onApplyLayout={(layout, tabGroups) =>
      layoutRenderer?.applyLayout(layout, tabGroups)}
    canCreateTab={true}
    onCreateTab={(blockIds) => layoutRenderer?.createTab(blockIds)}
    layoutMode={isFullscreenRender ? "fullscreen" : "normal"}
  >
    {#snippet children()}
      <NodeLayoutRenderer
        bind:this={layoutRenderer}
        {nodeId}
        nodeType="findz"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={FINDZ_DEFAULT_GRID_LAYOUT}
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
