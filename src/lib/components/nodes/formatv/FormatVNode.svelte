<script lang="ts">
  /**
   * FormatVNode - 视频格式过滤节点组件
   * 添加/移除 .nov 后缀，检查重复项（支持 #hb 等多前缀）
   *
   * 功能：
   * 1. 扫描并分类视频文件（普通、.nov、[#hb] 前缀）
   * 2. 添加/移除 .nov 后缀
   * 3. 检查带前缀文件对应的原始重复文件
   * 4. 显示前缀文件体积比原文件大的警告
   */
  import { Handle, Position, NodeResizer } from "@xyflow/svelte";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { Progress } from "$lib/components/ui/progress";
  import { Switch } from "$lib/components/ui/switch";
  import { Label } from "$lib/components/ui/label";
  import * as TreeView from "$lib/components/ui/tree-view";
  import * as Select from "$lib/components/ui/select";

  import { NodeLayoutRenderer } from "$lib/components/blocks";
  import { FORMATV_DEFAULT_GRID_LAYOUT } from "$lib/components/blocks/blockRegistry";
  import { api } from "$lib/services/api";
  import { getApiV1Url } from "$lib/stores/backend";
  import { getNodeState, saveNodeState } from "$lib/stores/nodeState.svelte";
  import NodeWrapper from "../NodeWrapper.svelte";
  import {
    LoaderCircle,
    FolderOpen,
    Clipboard,
    Video,
    CircleCheck,
    CircleX,
    Plus,
    Minus,
    Search,
    Copy,
    Check,
    RotateCcw,
    RefreshCw,
    Folder,
    AlertTriangle,
    FileVideo,
    ArrowRight,
    Tag,
  } from "@lucide/svelte";

  /** NodeLayoutRenderer 组件实例类型 */
  interface LayoutRendererInstance {
    compact: () => void;
    resetLayout: () => Promise<void>;
    getCurrentLayout: () => import("$lib/components/ui/dashboard-grid").GridItem[];
    getCurrentTabGroups: () => {
      id: string;
      blockIds: string[];
      activeIndex: number;
    }[];
    applyLayout: (
      layout: import("$lib/components/ui/dashboard-grid").GridItem[],
      tabGroups?:
        | { id: string; blockIds: string[]; activeIndex: number }[]
        | null
    ) => Promise<void>;
    createTab: (blockIds: string[]) => Promise<string | null>;
  }

  interface Props {
    id: string;
    data?: {
      config?: { path?: string };
      status?: "idle" | "running" | "completed" | "error";
      hasInputConnection?: boolean;
      logs?: string[];
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = "idle" | "scanning" | "processing" | "completed" | "error";
  type Action = "scan" | "add_nov" | "remove_nov" | "check_duplicates";
  type FileCategory = "normal" | "nov" | string;

  /** 前缀配置 */
  interface PrefixConfig {
    name: string;
    prefix: string;
    description: string;
  }

  /** 文件树节点 */
  interface FileTreeNode {
    name: string;
    path: string;
    isDir: boolean;
    children?: FileTreeNode[];
    category?: FileCategory;
  }

  /** 扫描结果 */
  interface ScanResult {
    normal_count: number;
    nov_count: number;
    prefixed_counts: Record<string, number>;
  }

  /** 文件列表数据 */
  interface FileListData {
    normal_files: string[];
    nov_files: string[];
    prefixed_files: Record<string, string[]>;
  }

  /** 重复文件对 */
  interface DuplicatePair {
    prefixed: string;
    original: string;
    prefixed_size: number;
    original_size: number;
  }

  /** 重复检测结果 */
  interface DuplicateResult {
    duplicates: string[];
    prefixed_larger: DuplicatePair[];
  }

  interface FormatVNodeState {
    phase: Phase;
    progress: number;
    progressText: string;
    scanResult: ScanResult | null;
    duplicateResult: DuplicateResult | null;
    fileListData: FileListData | null;
    targetPath: string;
    selectedPrefix: string;
    recursive: boolean;
    logs: string[];
    prefixes: PrefixConfig[];
  }

  // 使用 $derived 确保响应式
  const nodeId = $derived(id);
  const configPath = $derived(data?.config?.path ?? "E:\\1Hub\\EH\\1EHV");
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 默认前缀配置
  const defaultPrefixes: PrefixConfig[] = [
    { name: "hb", prefix: "[#hb]", description: "HandBrake转码文件" },
  ];

  // 获取共享的响应式状态
  const ns = getNodeState<FormatVNodeState>(id, {
    phase: "idle",
    progress: 0,
    progressText: "",
    scanResult: null,
    duplicateResult: null,
    fileListData: null,
    targetPath: configPath || "E:\\1Hub\\EH\\1EHV",
    selectedPrefix: "hb",
    recursive: false,
    logs: [],
    prefixes: defaultPrefixes,
  });

  // 本地 UI 状态
  let hasInputConnection = $state(false);
  let copiedLogs = $state(false);
  let copiedDuplicates = $state(false);
  let layoutRenderer = $state<LayoutRendererInstance | undefined>(undefined);
  let selectedFile = $state<string | null>(null);

  // 同步外部状态
  $effect(() => {
    if (dataLogs.length > 0) ns.logs = [...dataLogs];
    hasInputConnection = dataHasInputConnection;
  });

  // 获取视频缩略图 URL（使用系统缩略图）
  function getThumbnailUrl(filePath: string): string {
    return `${getApiV1Url()}/file?path=${encodeURIComponent(filePath)}&thumbnail=true`;
  }

  let canExecute = $derived(
    ns.phase === "idle" && (ns.targetPath.trim() !== "" || hasInputConnection)
  );
  let isRunning = $derived(
    ns.phase === "scanning" || ns.phase === "processing"
  );
  let borderClass = $derived(
    {
      idle: "border-border",
      scanning: "border-blue-500 shadow-sm",
      processing: "border-primary shadow-sm",
      completed: "border-primary/50",
      error: "border-destructive/50",
    }[ns.phase]
  );

  // 当前选中前缀的显示信息
  let currentPrefixInfo = $derived(
    ns.prefixes.find((p) => p.name === ns.selectedPrefix) ?? ns.prefixes[0]
  );

  function log(msg: string) {
    ns.logs = [...ns.logs.slice(-30), msg];
  }

  /** 格式化文件大小 */
  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    if (bytes < 1024 * 1024 * 1024)
      return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)}GB`;
  }

  /**
   * 构建完整的文件树结构
   */
  function buildFullFileTree(fileListData: FileListData): FileTreeNode[] {
    const nodeMap = new Map<string, FileTreeNode>();

    function addFile(filePath: string, category: FileCategory) {
      const parts = filePath.split(/[/\\]/);
      let currentPath = "";

      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        const parentPath = currentPath;
        currentPath = currentPath ? `${currentPath}\\${part}` : part;

        if (!nodeMap.has(currentPath)) {
          const dirNode: FileTreeNode = {
            name: part,
            path: currentPath,
            isDir: true,
            children: [],
          };
          nodeMap.set(currentPath, dirNode);
          if (parentPath && nodeMap.has(parentPath)) {
            const parent = nodeMap.get(parentPath)!;
            if (!parent.children!.find((c) => c.path === currentPath))
              parent.children!.push(dirNode);
          }
        }
      }

      const fileName = parts[parts.length - 1];
      const fileNode: FileTreeNode = {
        name: fileName,
        path: filePath,
        isDir: false,
        category,
      };
      nodeMap.set(filePath, fileNode);
      if (currentPath && nodeMap.has(currentPath)) {
        const parent = nodeMap.get(currentPath)!;
        if (!parent.children!.find((c) => c.path === filePath))
          parent.children!.push(fileNode);
      }
    }

    for (const file of fileListData.normal_files ?? []) addFile(file, "normal");
    for (const file of fileListData.nov_files ?? []) addFile(file, "nov");
    for (const [prefix, files] of Object.entries(
      fileListData.prefixed_files ?? {}
    )) {
      for (const file of files ?? []) addFile(file, prefix);
    }

    const rootNodes: FileTreeNode[] = [];
    for (const [path, node] of nodeMap) {
      if (node.isDir) {
        const parentPath = path.split(/[/\\]/).slice(0, -1).join("\\");
        if (!parentPath || !nodeMap.has(parentPath)) rootNodes.push(node);
      }
    }

    function sortChildren(node: FileTreeNode) {
      if (node.children && node.children.length > 0) {
        node.children.sort((a, b) => {
          if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
          return a.name.localeCompare(b.name);
        });
        for (const child of node.children) sortChildren(child);
      }
    }

    for (const root of rootNodes) sortChildren(root);
    rootNodes.sort((a, b) => a.name.localeCompare(b.name));
    return rootNodes;
  }

  async function selectFolder() {
    try {
      const { platform } = await import("$lib/api/platform");
      const selected = await platform.openFolderDialog("选择目录");
      if (selected) ns.targetPath = selected;
    } catch (e) {
      log(`选择文件夹失败: ${e}`);
    }
  }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import("$lib/api/platform");
      const text = await platform.readClipboard();
      if (text) ns.targetPath = text.trim();
    } catch (e) {
      log(`读取剪贴板失败: ${e}`);
    }
  }

  async function executeAction(action: Action) {
    if (!canExecute && action !== "scan") return;

    ns.phase = action === "scan" ? "scanning" : "processing";
    ns.progress = 0;
    ns.progressText = action === "scan" ? "扫描中..." : "处理中...";

    const actionText = {
      scan: "扫描",
      add_nov: "添加 .nov",
      remove_nov: "移除 .nov",
      check_duplicates: "检查重复",
    }[action];
    log(`🎬 开始${actionText}: ${ns.targetPath}`);

    try {
      ns.progress = 10;
      const requestData: any = {
        path: ns.targetPath,
        action,
        recursive: ns.recursive,
        prefix_name: ns.selectedPrefix,
      };

      const response = (await api.executeNode("formatv", requestData)) as any;

      if (response.success) {
        ns.phase = "completed";
        ns.progress = 100;
        ns.progressText = "完成";

        // 更新前缀列表（如果后端返回）
        if (response.data?.prefixes) {
          ns.prefixes = response.data.prefixes;
        }

        if (action === "scan") {
          ns.scanResult = {
            normal_count: response.data?.normal_count ?? 0,
            nov_count: response.data?.nov_count ?? 0,
            prefixed_counts: response.data?.prefixed_counts ?? {},
          };
          ns.fileListData = {
            normal_files: response.data?.normal_files ?? [],
            nov_files: response.data?.nov_files ?? [],
            prefixed_files: response.data?.prefixed_files ?? {},
          };
        } else if (action === "check_duplicates") {
          ns.duplicateResult = {
            duplicates: response.data?.duplicates ?? [],
            prefixed_larger: response.data?.prefixed_larger ?? [],
          };
          log(`✅ 发现 ${ns.duplicateResult.duplicates.length} 个重复文件`);
          if (ns.duplicateResult.prefixed_larger.length > 0) {
            log(
              `⚠️ ${ns.duplicateResult.prefixed_larger.length} 个前缀文件体积更大`
            );
          }
        }
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
    }
  }

  function handleReset() {
    ns.phase = "idle";
    ns.progress = 0;
    ns.progressText = "";
    ns.scanResult = null;
    ns.duplicateResult = null;
    ns.fileListData = null;
    selectedFile = null;
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

  function copyDuplicatesToClipboard() {
    if (!ns.duplicateResult?.duplicates.length) return;
    const text = ns.duplicateResult.duplicates.join("\n");
    copyToClipboard(text, (v) => (copiedDuplicates = v));
    log(
      `📋 已复制 ${ns.duplicateResult.duplicates.length} 个重复文件路径到剪贴板`
    );
  }
</script>

<!-- ========== 统一 UI 结构的区块 ========== -->

<!-- 路径输入区块 -->
{#snippet pathBlock()}
  <div class="cq-mb">
    <div class="flex items-center gap-1 mb-1 cq-text">
      <Video class="cq-icon" />
      <span class="font-medium">目标目录</span>
    </div>
    {#if !hasInputConnection}
      <div class="flex cq-gap">
        <Input
          bind:value={ns.targetPath}
          placeholder="输入或选择目录..."
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
        class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-text"
      >
        <span>←</span><span>输入来自上游节点</span>
      </div>
    {/if}
  </div>
{/snippet}

<!-- 配置区块（前缀选择、递归选项） -->
{#snippet configBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 前缀选择 -->
    <div class="flex flex-col gap-1">
      <div class="flex items-center gap-1 cq-text">
        <Tag class="cq-icon text-orange-500" />
        <span class="font-medium text-xs">检查前缀</span>
      </div>
      <Select.Root type="single" bind:value={ns.selectedPrefix}>
        <Select.Trigger class="w-full h-8 text-xs">
          {currentPrefixInfo?.prefix ?? "选择前缀"}
        </Select.Trigger>
        <Select.Content>
          {#each ns.prefixes as prefix}
            <Select.Item value={prefix.name} label={prefix.prefix}>
              <div class="flex items-center gap-2">
                <span class="font-mono text-xs">{prefix.prefix}</span>
                <span class="text-muted-foreground text-xs"
                  >({prefix.description})</span
                >
              </div>
            </Select.Item>
          {/each}
        </Select.Content>
      </Select.Root>
    </div>

    <!-- 递归选项 -->
    <div class="flex items-center gap-2 cq-padding bg-muted/30 rounded">
      <Switch
        id="recursive-switch"
        bind:checked={ns.recursive}
        disabled={isRunning}
      />
      <Label for="recursive-switch" class="text-xs cursor-pointer"
        >递归子目录</Label
      >
    </div>
  </div>
{/snippet}

<!-- 操作区块（含状态显示） -->
{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <!-- 状态指示 -->
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if ns.phase === "completed"}
        <CircleCheck class="cq-icon text-green-500 shrink-0" />
        <span class="cq-text text-green-600 font-medium">完成</span>
        <span class="cq-text-sm text-muted-foreground ml-auto"
          >{ns.scanResult?.normal_count ?? 0} 项</span
        >
      {:else if ns.phase === "error"}
        <CircleX class="cq-icon text-red-500 shrink-0" />
        <span class="cq-text text-red-600 font-medium">失败</span>
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1">
          <Progress value={ns.progress} class="h-1.5" />
        </div>
        <span class="cq-text-sm text-muted-foreground">{ns.progress}%</span>
      {:else}
        <Video class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待执行</span>
      {/if}
    </div>
    <!-- 主按钮 -->
    <Button
      class="w-full cq-button flex-1"
      onclick={() => executeAction("scan")}
      disabled={!canExecute || isRunning}
    >
      {#if ns.phase === "scanning"}<LoaderCircle
          class="cq-icon mr-1 animate-spin"
        />{:else}<RefreshCw class="cq-icon mr-1" />{/if}
      <span>扫描</span>
    </Button>
    <!-- 辅助按钮 -->
    <div class="flex cq-gap">
      <Button
        variant="outline"
        class="flex-1 cq-button-sm"
        onclick={() => executeAction("add_nov")}
        disabled={!canExecute || isRunning}
      >
        <Plus class="cq-icon" /><span class="cq-wide-only ml-1">.nov</span>
      </Button>
      <Button
        variant="outline"
        class="flex-1 cq-button-sm"
        onclick={() => executeAction("remove_nov")}
        disabled={!canExecute || isRunning}
      >
        <Minus class="cq-icon" /><span class="cq-wide-only ml-1">.nov</span>
      </Button>
    </div>
    <div class="flex cq-gap">
      <Button
        variant="secondary"
        class="flex-1 cq-button-sm"
        onclick={() => executeAction("check_duplicates")}
        disabled={!canExecute || isRunning}
      >
        <Search class="cq-icon" /><span class="ml-1 truncate"
          >检查 {currentPrefixInfo?.prefix}</span
        >
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
  </div>
{/snippet}

<!-- 递归渲染文件树节点 -->
{#snippet renderTreeNode(node: FileTreeNode)}
  {#if node.isDir}
    <TreeView.Folder name={node.name} open={true} class="text-xs">
      {#snippet icon()}
        <Folder class="w-3 h-3 text-yellow-500" />
      {/snippet}
      {#snippet children()}
        {#if node.children}
          {#each node.children as child}
            {@render renderTreeNode(child)}
          {/each}
        {/if}
      {/snippet}
    </TreeView.Folder>
  {:else}
    {@const categoryColor =
      node.category === "normal"
        ? "text-green-500"
        : node.category === "nov"
          ? "text-yellow-500"
          : "text-blue-500"}
    {@const categoryBg =
      node.category === "normal"
        ? ""
        : node.category === "nov"
          ? "bg-yellow-500/20 text-yellow-600"
          : "bg-blue-500/20 text-blue-600"}
    <button
      class="flex items-center gap-2 py-1 px-1 w-full text-left hover:bg-muted/50 rounded transition-colors {selectedFile ===
      node.path
        ? 'bg-primary/10'
        : ''}"
      onclick={() => (selectedFile = node.path)}
    >
      <div
        class="w-10 h-7 rounded bg-muted/50 overflow-hidden shrink-0 flex items-center justify-center relative"
      >
        <img
          src={getThumbnailUrl(node.path)}
          alt=""
          class="w-full h-full object-cover"
          loading="lazy"
          onerror={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
        <Video class="w-3 h-3 {categoryColor} absolute" />
      </div>
      <span class="truncate flex-1 text-xs" title={node.path}>{node.name}</span>
      {#if node.category && node.category !== "normal"}
        <span class="text-[10px] px-1 rounded {categoryBg}">
          {node.category === "nov" ? ".nov" : `[${node.category}]`}
        </span>
      {/if}
    </button>
  {/if}
{/snippet}

<!-- 文件树区块（含统计信息） -->
{#snippet treeBlock()}
  {@const fileTree = ns.fileListData ? buildFullFileTree(ns.fileListData) : []}
  <div class="h-full flex flex-col overflow-hidden">
    <div
      class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0"
    >
      <span class="cq-text font-semibold flex items-center gap-1">
        <Folder class="cq-icon text-yellow-500" />文件树
      </span>
      {#if ns.scanResult}
        <div class="flex items-center gap-2 cq-text-sm">
          <span class="flex items-center gap-1 text-green-600" title="普通视频">
            <span class="w-2 h-2 rounded-full bg-green-500"></span>
            {ns.scanResult.normal_count}
          </span>
          <span
            class="flex items-center gap-1 text-yellow-600"
            title=".nov 文件"
          >
            <span class="w-2 h-2 rounded-full bg-yellow-500"></span>
            {ns.scanResult.nov_count}
          </span>
          {#each Object.entries(ns.scanResult.prefixed_counts) as [name, count]}
            {#if count > 0}
              <span
                class="flex items-center gap-1 text-blue-600"
                title="[{name}] 前缀"
              >
                <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                {count}
              </span>
            {/if}
          {/each}
        </div>
      {:else}
        <span class="cq-text-sm text-muted-foreground">扫描后显示</span>
      {/if}
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
      {#if fileTree.length > 0}
        <TreeView.Root class="text-sm">
          {#each fileTree as node}
            {@render renderTreeNode(node)}
          {/each}
        </TreeView.Root>
      {:else if ns.fileListData}
        <div class="text-center text-muted-foreground py-8">
          没有找到视频文件
        </div>
      {:else}
        <div class="text-center text-muted-foreground py-8">
          扫描后显示文件树
        </div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 重复检测区块 -->
{#snippet duplicatesBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div
      class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0"
    >
      <span class="cq-text font-semibold flex items-center gap-1">
        <AlertTriangle class="cq-icon text-yellow-500" />重复检测
      </span>
      {#if ns.duplicateResult}
        <div class="flex items-center gap-2">
          <span class="cq-text-sm text-muted-foreground">
            {ns.duplicateResult.duplicates.length} 个重复
          </span>
          <Button
            variant="ghost"
            size="icon"
            class="h-5 w-5"
            onclick={copyDuplicatesToClipboard}
          >
            {#if copiedDuplicates}<Check
                class="w-3 h-3 text-green-500"
              />{:else}<Copy class="w-3 h-3" />{/if}
          </Button>
        </div>
      {/if}
    </div>
    <div class="flex-1 overflow-y-auto cq-padding">
      {#if ns.duplicateResult}
        {#if ns.duplicateResult.prefixed_larger.length > 0}
          <!-- 警告：前缀文件更大 -->
          <div class="mb-4">
            <div
              class="flex items-center gap-1 text-yellow-600 cq-text font-medium mb-2"
            >
              <AlertTriangle class="w-4 h-4" />
              <span
                >前缀文件体积更大 ({ns.duplicateResult.prefixed_larger
                  .length})</span
              >
            </div>
            <div class="space-y-2">
              {#each ns.duplicateResult.prefixed_larger as pair}
                <div
                  class="bg-yellow-500/10 border border-yellow-500/30 rounded p-2 text-xs"
                >
                  <div class="flex items-center gap-1 mb-1">
                    <FileVideo class="w-3 h-3 text-blue-500" />
                    <span
                      class="font-mono truncate flex-1"
                      title={pair.prefixed}
                      >{pair.prefixed.split(/[/\\]/).pop()}</span
                    >
                    <span class="text-yellow-600 font-medium"
                      >{formatSize(pair.prefixed_size)}</span
                    >
                  </div>
                  <div class="flex items-center gap-1 text-muted-foreground">
                    <ArrowRight class="w-3 h-3" />
                    <FileVideo class="w-3 h-3 text-green-500" />
                    <span
                      class="font-mono truncate flex-1"
                      title={pair.original}
                      >{pair.original.split(/[/\\]/).pop()}</span
                    >
                    <span class="text-green-600"
                      >{formatSize(pair.original_size)}</span
                    >
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        {#if ns.duplicateResult.duplicates.length > 0}
          <!-- 重复文件列表 -->
          <div>
            <div
              class="flex items-center gap-1 text-muted-foreground cq-text font-medium mb-2"
            >
              <Search class="w-4 h-4" />
              <span
                >可删除的原视频 ({ns.duplicateResult.duplicates.length})</span
              >
            </div>
            <div class="space-y-1 max-h-40 overflow-y-auto">
              {#each ns.duplicateResult.duplicates.slice(0, 20) as dup}
                <div
                  class="flex items-center gap-1 text-xs bg-muted/30 rounded px-2 py-1"
                >
                  <FileVideo class="w-3 h-3 text-red-500 shrink-0" />
                  <span class="font-mono truncate" title={dup}>{dup}</span>
                </div>
              {/each}
              {#if ns.duplicateResult.duplicates.length > 20}
                <div class="text-center text-muted-foreground text-xs py-1">
                  ... 还有 {ns.duplicateResult.duplicates.length - 20} 个
                </div>
              {/if}
            </div>
          </div>
        {:else}
          <div class="text-center text-green-600 py-4">
            <CircleCheck class="w-6 h-6 mx-auto mb-1" />
            <span class="cq-text">未发现重复文件</span>
          </div>
        {/if}
      {:else}
        <div class="text-center text-muted-foreground py-8">
          <Search class="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p class="cq-text">执行"检查重复"后显示结果</p>
          <p class="cq-text-sm mt-1">
            将检查 {currentPrefixInfo?.prefix} 前缀文件
          </p>
        </div>
      {/if}
    </div>
  </div>
{/snippet}

<!-- 日志区块 -->
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

<!-- 区块渲染器 -->
{#snippet renderBlockContent(blockId: string)}
  {#if blockId === "path"}{@render pathBlock()}
  {:else if blockId === "config"}{@render configBlock()}
  {:else if blockId === "operation"}{@render operationBlock()}
  {:else if blockId === "tree"}{@render treeBlock()}
  {:else if blockId === "duplicates"}{@render duplicatesBlock()}
  {:else if blockId === "log"}{@render logBlock()}
  {/if}
{/snippet}

<!-- 主渲染 -->
<div
  class="h-full w-full flex flex-col overflow-hidden"
  style={!isFullscreenRender ? "max-width: 400px;" : ""}
>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={280} minHeight={350} maxWidth={400} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper
    {nodeId}
    title="formatv"
    icon={Video}
    status={ns.phase}
    {borderClass}
    {isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="formatv"
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
        nodeType="formatv"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={FORMATV_DEFAULT_GRID_LAYOUT}
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
