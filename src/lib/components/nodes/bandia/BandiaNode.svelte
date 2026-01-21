<script lang="ts">
  /**
   * BandiaNode - 批量解压节点组件
   * 使用 Bandizip 批量解压压缩包
   * 支持 WebSocket 实时进度和日志更新
   */
  import { Handle, Position, NodeResizer } from "@xyflow/svelte";
  import { Button } from "$lib/components/ui/button";
  import { Checkbox } from "$lib/components/ui/checkbox";
  import { Progress } from "$lib/components/ui/progress";
  import { Textarea } from "$lib/components/ui/textarea";

  import { NodeLayoutRenderer } from "$lib/components/blocks";
  import { BANDIA_DEFAULT_GRID_LAYOUT } from "./blocks";
  import { api } from "$lib/services/api";
  import { getNodeState, saveNodeState } from "$lib/stores/nodeState.svelte";
  import { getWsBaseUrl } from "$lib/stores/backend";
  import NodeWrapper from "../NodeWrapper.svelte";
  import {
    Play,
    LoaderCircle,
    Clipboard,
    FileArchive,
    CircleCheck,
    CircleX,
    Trash2,
    Copy,
    Check,
    RotateCcw,
    FolderOpen,
    Square,
  } from "@lucide/svelte";

  interface Props {
    id: string;
    data?: {
      config?: {
        paths?: string[];
        delete_after?: boolean;
        use_trash?: boolean;
      };
      status?: "idle" | "running" | "completed" | "error";
      hasInputConnection?: boolean;
      logs?: string[];
      label?: string;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = "idle" | "extracting" | "compressing" | "completed" | "error";
  type Mode = "extract" | "compress";

  interface BandiaState {
    mode: Mode; // 当前模式
    phase: Phase;
    progress: number;
    progressText: string;
    archivePaths: string[];
    deleteAfter: boolean;
    useTrash: boolean;
    parallel: boolean; // 启用并行
    workers: number; // 并行工作线程数
    activeIndices: number[]; // 正在处理的文件索引列表
    completedIndices: number[]; // 已完成的文件索引列表
    extractResult: ExtractResult | null;
    compressResult: CompressResult | null;
    pathMappings: PathMapping[]; // 压缩包到解压目录的映射
    logs: string[];
    hasInputConnection: boolean;
  }

  interface CompressResult {
    success: boolean;
    compressed: number;
    failed: number;
    total: number;
  }

  interface PathMapping {
    archive_path: string;
    extracted_path: string;
  }

  interface ExtractResult {
    success: boolean;
    extracted: number;
    failed: number;
    total: number;
    totalSize?: number; // 总文件大小 (bytes)
  }

  const nodeId = $derived(id);
  const configPaths = $derived(data?.config?.paths ?? []);
  const configDeleteAfter = $derived(data?.config?.delete_after ?? true);
  const configUseTrash = $derived(data?.config?.use_trash ?? true);
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  // 获取共享的响应式状态（节点模式和全屏模式共用同一个对象）
  const ns = getNodeState<BandiaState>(id, {
    mode: "extract",
    phase: "idle",
    progress: 0,
    progressText: "",
    archivePaths: [],
    deleteAfter: configDeleteAfter,
    useTrash: configUseTrash,
    parallel: true,
    workers: 2,
    activeIndices: [],
    completedIndices: [],
    extractResult: null,
    compressResult: null,
    pathMappings: [],
    logs: [],
    hasInputConnection: false,
  });

  // 纯 UI 状态（不需要同步）
  let copied = $state(false);
  let layoutRenderer = $state<any>(undefined);
  // 当前正在处理的文件索引（用于实时显示）
  let currentFileIndex = $state(-1);
  // 文本区域的本地编辑状态
  let pathsText = $state(
    ns.archivePaths.length > 0
      ? ns.archivePaths.join("\n")
      : configPaths.join("\n"),
  );

  // 持续同步外部数据
  $effect(() => {
    ns.logs = [...dataLogs];
    ns.hasInputConnection = dataHasInputConnection;
  });

  let canExtract = $derived(
    ns.phase === "idle" &&
      ns.mode === "extract" &&
      (pathsText.trim() !== "" || ns.hasInputConnection),
  );
  let canCompress = $derived(
    ns.phase === "idle" && ns.mode === "compress" && ns.pathMappings.length > 0,
  );
  let isRunning = $derived(
    ns.phase === "extracting" || ns.phase === "compressing",
  );
  let borderClass = $derived(
    {
      idle: "border-border",
      extracting: "border-primary shadow-sm",
      compressing: "border-primary shadow-sm",
      completed: "border-primary/50",
      error: "border-destructive/50",
    }[ns.phase],
  );

  function log(msg: string) {
    ns.logs = [...ns.logs.slice(-30), msg];
  }

  function parsePaths(text: string): string[] {
    return text
      .split("\n")
      .map((line) => line.trim().replace(/^["']|["']$/g, ""))
      .filter((line) => line && /\.(zip|7z|rar|tar|gz|bz2|xz)$/i.test(line));
  }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import("$lib/api/platform");
      const text = await platform.readClipboard();
      if (text) {
        pathsText = text.trim();
        log(`📋 从剪贴板读取 ${parsePaths(pathsText).length} 个压缩包路径`);
      }
    } catch (e) {
      log(`❌ 读取剪贴板失败: ${e}`);
    }
  }

  async function selectFiles() {
    try {
      const { platform } = await import("$lib/api/platform");
      const selected = await platform.openFileDialog("选择压缩包", [
        {
          name: "压缩文件",
          extensions: ["zip", "7z", "rar", "tar", "gz", "bz2", "xz"],
        },
      ]);
      if (selected) {
        pathsText = pathsText ? pathsText + "\n" + selected : selected;
        log(`📁 选择了文件: ${selected.split(/[/\\]/).pop()}`);
      }
    } catch (e) {
      log(`❌ 选择文件失败: ${e}`);
    }
  }

  async function handleExtract() {
    if (!canExtract) return;
    const paths = parsePaths(pathsText);
    if (paths.length === 0) {
      log("❌ 没有有效的压缩包路径");
      return;
    }
    ns.archivePaths = paths;
    ns.phase = "extracting";
    ns.progress = 0;
    ns.progressText = "正在解压...";
    ns.extractResult = null;
    currentFileIndex = -1;
    log(`📦 开始解压 ${paths.length} 个压缩包...`);

    // 生成任务 ID 用于 WebSocket 连接
    const taskId = `bandia-${nodeId}-${Date.now()}`;
    let ws: WebSocket | null = null;

    try {
      // 建立 WebSocket 连接接收实时进度和日志
      const wsUrl = `${getWsBaseUrl()}/v1/ws/tasks/${taskId}`;
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "progress") {
            ns.progress = msg.progress;

            // 进度消息格式改进: "解压 X/Y|filename" 或 "STARTED:idx|filename"
            const parts = msg.message.split("|");
            const statusMsg = parts[0];
            const currentFileName = parts[1] || "";

            if (statusMsg.startsWith("STARTED:")) {
              const startIdx = parseInt(statusMsg.split(":")[1]);
              if (!ns.activeIndices.includes(startIdx)) {
                ns.activeIndices = [...ns.activeIndices, startIdx];
              }
              if (currentFileName) log(`🔄 正在解压: ${currentFileName}`);
              return;
            }

            if (statusMsg.startsWith("FINISHED:")) {
              const finishedIdx = parseInt(statusMsg.split(":")[1]);
              ns.activeIndices = ns.activeIndices.filter(
                (i) => i !== finishedIdx,
              );
              if (!ns.completedIndices.includes(finishedIdx)) {
                ns.completedIndices = [...ns.completedIndices, finishedIdx];
              }
              // 处理进度文本
              const pMsg = parts[1] || "";
              if (pMsg) ns.progressText = pMsg;
              return;
            }

            ns.progressText = statusMsg;

            // 从进度消息中解析已处理数量: "解压 2/10"
            const match = statusMsg.match(/解压 (\d+)\/(\d+)/);
            if (match) {
              const processedCount = parseInt(match[1]);
              currentFileIndex = processedCount - 1;

              // 维护并行活动列表：如果 X 完成了，从活动列表中移除对应项是不太准确的
              // 这里的策略是：X 完成的消息到达时，我们可以根据文件名或索引清理
              // 实际上后端目前完成时发送的是 "解压 X/Y"，我们可以认为 [0...X-1] 已经完成
              ns.activeIndices = ns.activeIndices.filter(
                (i) => i >= processedCount,
              );

              if (
                processedCount > 0 &&
                !ns.completedIndices.includes(currentFileIndex)
              ) {
                ns.completedIndices = [
                  ...ns.completedIndices,
                  currentFileIndex,
                ];
              }
            }

            if (currentFileName) {
              ns.progressText = `${statusMsg}: ${currentFileName}`;
            }
          } else if (msg.type === "log") {
            log(msg.message);
          } else if (msg.type === "status" && msg.status === "error") {
            log(`❌ ${msg.message}`);
          }
        } catch (e) {
          console.error("解析 WebSocket 消息失败:", e);
        }
      };

      ws.onerror = (e) => {
        console.error("WebSocket 错误:", e);
      };

      // 等待 WebSocket 连接建立
      await new Promise<void>((resolve) => {
        const timeout = setTimeout(() => {
          resolve(); // 超时也继续执行，只是没有实时更新
        }, 2000);
        ws!.onopen = () => {
          clearTimeout(timeout);
          resolve();
        };
        ws!.onerror = () => {
          clearTimeout(timeout);
          resolve(); // 连接失败也继续执行
        };
      });

      // 发送执行请求，带上 task_id 和 parallel 参数
      const response = (await api.executeNode(
        "bandia",
        {
          action: "extract",
          paths,
          delete_after: ns.deleteAfter,
          use_trash: ns.useTrash,
          parallel: ns.parallel,
          workers: ns.workers,
        },
        { taskId, nodeId },
      )) as any;

      if (response.success) {
        ns.phase = "completed";
        ns.progress = 100;
        ns.progressText = "解压完成";
        ns.extractResult = {
          success: true,
          extracted: response.data?.extracted_count ?? 0,
          failed: response.data?.failed_count ?? 0,
          total: response.data?.total_count ?? paths.length,
        };
        // 保存路径映射
        ns.pathMappings = response.data?.path_mappings ?? [];
        log(`✅ ${response.message}`);
        log(
          `📊 成功: ${ns.extractResult.extracted}, 失败: ${ns.extractResult.failed}`,
        );
        if (ns.pathMappings.length > 0) {
          log(`📂 已记录 ${ns.pathMappings.length} 个路径映射`);
        }
      } else {
        ns.phase = "error";
        ns.progress = 0;
        log(`❌ 解压失败: ${response.message}`);
      }
    } catch (error) {
      ns.phase = "error";
      ns.progress = 0;
      log(`❌ 解压失败: ${error}`);
    } finally {
      // 关闭 WebSocket 连接
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    }
  }

  function handleReset() {
    ns.mode = "extract";
    ns.phase = "idle";
    ns.progress = 0;
    ns.progressText = "";
    ns.extractResult = null;
    ns.compressResult = null;
    ns.archivePaths = [];
    ns.pathMappings = [];
    ns.logs = [];
    currentFileIndex = -1;
    ns.activeIndices = [];
    ns.completedIndices = [];
  }

  async function handleStop() {
    log("⏹️ 用户请求停止");
    try {
      await api.executeNode("bandia", { action: "stop" }, { nodeId });
    } catch (e) {
      log(`❌ 发送停止指令失败: ${e}`);
    }
    ns.phase = "error";
    ns.progressText = "已停止";
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

  let exportCopied = $state(false);

  async function exportPathMappings() {
    if (ns.pathMappings.length === 0) {
      log("❌ 没有可导出的路径映射");
      return;
    }

    try {
      // 导出为 JSON 格式
      const exportData = {
        exported_at: new Date().toISOString(),
        total: ns.pathMappings.length,
        mappings: ns.pathMappings,
      };
      const jsonStr = JSON.stringify(exportData, null, 2);
      await navigator.clipboard.writeText(jsonStr);
      exportCopied = true;
      log(`📋 已复制 ${ns.pathMappings.length} 个路径映射到剪贴板`);
      setTimeout(() => {
        exportCopied = false;
      }, 2000);
    } catch (e) {
      log(`❌ 导出失败: ${e}`);
    }
  }

  async function importPathMappings() {
    try {
      const { platform } = await import("$lib/api/platform");
      const text = await platform.readClipboard();
      if (!text) {
        log("❌ 剪贴板为空");
        return;
      }

      const data = JSON.parse(text);
      let mappings: PathMapping[] = [];

      if (Array.isArray(data)) {
        mappings = data;
      } else if (data.mappings && Array.isArray(data.mappings)) {
        mappings = data.mappings;
      }

      // 验证并过滤有效映射
      const validMappings = mappings.filter(
        (m) => m.archive_path && m.extracted_path,
      );

      if (validMappings.length === 0) {
        log("❌ 没有有效的路径映射");
        return;
      }

      ns.pathMappings = validMappings;
      ns.mode = "compress";
      log(`📥 已导入 ${validMappings.length} 个路径映射`);
    } catch (e) {
      log(`❌ 导入失败: ${e}`);
    }
  }

  async function handleCompress() {
    if (ns.pathMappings.length === 0) {
      log("❌ 没有路径映射可压缩");
      return;
    }

    ns.phase = "compressing";
    ns.progress = 0;
    ns.progressText = "正在压缩...";
    ns.compressResult = null;
    log(`📦 开始压缩 ${ns.pathMappings.length} 个目录...`);

    const taskId = `bandia-compress-${nodeId}-${Date.now()}`;
    let ws: WebSocket | null = null;

    try {
      const wsUrl = `${getWsBaseUrl()}/v1/ws/tasks/${taskId}`;
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "progress") {
            ns.progress = msg.progress;
            const parts = msg.message.split("|");
            ns.progressText = parts[0];
          } else if (msg.type === "log") {
            log(msg.message);
          }
        } catch (e) {
          console.error("解析 WebSocket 消息失败:", e);
        }
      };

      await new Promise<void>((resolve) => {
        const timeout = setTimeout(() => resolve(), 2000);
        ws!.onopen = () => {
          clearTimeout(timeout);
          resolve();
        };
        ws!.onerror = () => {
          clearTimeout(timeout);
          resolve();
        };
      });

      const response = (await api.executeNode(
        "bandia",
        {
          action: "compress",
          mappings: ns.pathMappings,
          delete_source: ns.deleteAfter,
        },
        { taskId, nodeId },
      )) as any;

      if (response.success) {
        ns.phase = "completed";
        ns.progress = 100;
        ns.progressText = "压缩完成";
        ns.compressResult = {
          success: true,
          compressed: response.data?.compressed_count ?? 0,
          failed: response.data?.failed_count ?? 0,
          total: response.data?.total_count ?? ns.pathMappings.length,
        };
        log(`✅ ${response.message}`);
        log(
          `📊 成功: ${ns.compressResult.compressed}, 失败: ${ns.compressResult.failed}`,
        );
      } else {
        ns.phase = "error";
        ns.progress = 0;
        log(`❌ 压缩失败: ${response.message}`);
      }
    } catch (error) {
      ns.phase = "error";
      ns.progress = 0;
      log(`❌ 压缩失败: ${error}`);
    } finally {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    }
  }
</script>

{#snippet sourceBlock()}
  {#if !ns.hasInputConnection}
    <div class="flex flex-col cq-gap h-full">
      <!-- 模式切换 -->
      <div class="flex cq-gap">
        <Button
          variant={ns.mode === "extract" ? "default" : "outline"}
          size="sm"
          class="cq-button-sm flex-1"
          onclick={() => (ns.mode = "extract")}
          disabled={isRunning}
        >
          <FileArchive class="cq-icon mr-1" />解压
        </Button>
        <Button
          variant={ns.mode === "compress" ? "default" : "outline"}
          size="sm"
          class="cq-button-sm flex-1"
          onclick={() => (ns.mode = "compress")}
          disabled={isRunning}
        >
          <FileArchive class="cq-icon mr-1" />压缩
        </Button>
      </div>

      {#if ns.mode === "extract"}
        <!-- 解压模式 -->
        <div class="flex cq-gap">
          <Button
            variant="outline"
            size="sm"
            class="cq-button-sm flex-1"
            onclick={pasteFromClipboard}
            disabled={isRunning}
          >
            <Clipboard class="cq-icon mr-1" />剪贴板
          </Button>
          <Button
            variant="outline"
            size="sm"
            class="cq-button-sm flex-1"
            onclick={selectFiles}
            disabled={isRunning}
          >
            <FolderOpen class="cq-icon mr-1" />选择文件
          </Button>
        </div>
        <Textarea
          bind:value={pathsText}
          placeholder="粘贴压缩包路径（每行一个）&#10;支持: .zip .7z .rar .tar .gz .bz2 .xz"
          disabled={isRunning}
          class="flex-1 cq-text font-mono resize-none min-h-[60px]"
        />
        <div class="cq-text-sm text-muted-foreground">
          已识别 {parsePaths(pathsText).length} 个压缩包
        </div>
      {:else}
        <!-- 压缩模式 -->
        <div class="flex cq-gap">
          <Button
            variant="outline"
            size="sm"
            class="cq-button-sm flex-1"
            onclick={importPathMappings}
            disabled={isRunning}
          >
            <Clipboard class="cq-icon mr-1" />导入映射
          </Button>
        </div>
        <div class="flex-1 cq-padding bg-muted/30 cq-rounded overflow-y-auto">
          {#if ns.pathMappings.length > 0}
            <div class="space-y-1">
              {#each ns.pathMappings.slice(0, 10) as mapping, idx}
                <div class="cq-text-sm truncate" title={mapping.extracted_path}>
                  {idx + 1}. {mapping.extracted_path.split(/[/\\]/).pop()} → {mapping.archive_path
                    .split(/[/\\]/)
                    .pop()}
                </div>
              {/each}
              {#if ns.pathMappings.length > 10}
                <div class="cq-text-sm text-muted-foreground">
                  还有 {ns.pathMappings.length - 10} 个...
                </div>
              {/if}
            </div>
          {:else}
            <div class="cq-text text-muted-foreground text-center py-2">
              点击"导入映射"从剪贴板读取路径映射
            </div>
          {/if}
        </div>
        <div class="cq-text-sm text-muted-foreground">
          已导入 {ns.pathMappings.length} 个映射
        </div>
      {/if}
    </div>
  {:else}
    <div
      class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-text"
    >
      <span>←</span><span>输入来自上游节点</span>
    </div>
  {/if}
{/snippet}

{#snippet optionsBlock()}
  <div class="flex flex-col cq-gap">
    <label class="flex items-center cq-gap cursor-pointer">
      <Checkbox bind:checked={ns.deleteAfter} disabled={isRunning} />
      <span class="cq-text">解压后删除源文件</span>
    </label>
    {#if ns.deleteAfter}
      <label class="flex items-center cq-gap cursor-pointer ml-4">
        <Checkbox bind:checked={ns.useTrash} disabled={isRunning} />
        <span class="cq-text flex items-center gap-1"
          ><Trash2 class="cq-icon text-orange-500" />移入回收站</span
        >
      </label>
    {/if}
    <div class="border-t border-border my-1"></div>
    <label class="flex items-center cq-gap cursor-pointer">
      <Checkbox bind:checked={ns.parallel} disabled={isRunning} />
      <span class="cq-text">启用并行解压 ⚡</span>
    </label>
    {#if ns.parallel}
      <div class="flex items-center cq-gap ml-4">
        <span class="cq-text-sm text-muted-foreground">工作线程:</span>
        <input
          type="number"
          min="1"
          max="8"
          bind:value={ns.workers}
          disabled={isRunning}
          class="w-14 h-6 px-1 cq-text-sm border rounded bg-background text-center"
        />
      </div>
    {/if}
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex flex-col cq-gap cq-padding bg-muted/30 cq-rounded">
      <div class="flex items-center cq-gap">
        {#if ns.extractResult}
          {#if ns.extractResult.success && ns.extractResult.failed === 0}
            <CircleCheck class="cq-icon text-green-500 shrink-0" />
            <span class="cq-text text-green-600 font-medium">完成</span>
            <span class="cq-text-sm text-muted-foreground ml-auto"
              >{ns.extractResult.extracted} 成功</span
            >
          {:else if ns.extractResult.success}
            <CircleCheck class="cq-icon text-yellow-500 shrink-0" />
            <span class="cq-text text-yellow-600 font-medium">部分完成</span>
          {:else}
            <CircleX class="cq-icon text-red-500 shrink-0" />
            <span class="cq-text text-red-600 font-medium">失败</span>
          {/if}
        {:else if isRunning}
          <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
          <div class="flex-1">
            <Progress value={ns.progress} class="h-1.5" />
          </div>
          <span class="cq-text-sm text-muted-foreground">{ns.progress}%</span>
        {:else}
          <FileArchive class="cq-icon text-muted-foreground/50 shrink-0" />
          <span class="cq-text text-muted-foreground">等待解压</span>
        {/if}
      </div>
      {#if isRunning && ns.progressText}
        <div
          class="cq-text-sm text-muted-foreground truncate"
          title={ns.progressText}
        >
          {ns.progressText}
        </div>
      {/if}
    </div>
    {#if ns.phase === "idle" || ns.phase === "error"}
      {#if ns.mode === "extract"}
        <Button
          class="w-full cq-button flex-1"
          onclick={handleExtract}
          disabled={!canExtract}
        >
          <Play class="cq-icon mr-1" /><span>开始解压</span>
        </Button>
      {:else}
        <Button
          class="w-full cq-button flex-1"
          onclick={handleCompress}
          disabled={!canCompress}
        >
          <Play class="cq-icon mr-1" /><span>开始压缩</span>
        </Button>
      {/if}
    {:else if ns.phase === "extracting" || ns.phase === "compressing"}
      <Button
        class="w-full cq-button flex-1 bg-destructive hover:bg-destructive/90"
        onclick={handleStop}
      >
        <Square class="cq-icon mr-1" /><span>停止</span>
      </Button>
    {:else if ns.phase === "completed"}
      <Button class="w-full cq-button flex-1" onclick={handleReset}>
        <Play class="cq-icon mr-1" /><span>重新开始</span>
      </Button>
    {/if}
    {#if ns.phase === "completed" && ns.mode === "extract" && ns.pathMappings.length > 0}
      <Button
        variant="outline"
        class="w-full cq-button-sm"
        onclick={exportPathMappings}
      >
        {#if exportCopied}
          <Check class="cq-icon mr-1 text-green-500" /><span>已复制</span>
        {:else}
          <Copy class="cq-icon mr-1" /><span
            >导出路径映射 ({ns.pathMappings.length})</span
          >
        {/if}
      </Button>
    {/if}
    <Button
      variant="ghost"
      class="w-full cq-button-sm"
      onclick={handleReset}
      disabled={isRunning}
    >
      <RotateCcw class="cq-icon mr-1" />重置
    </Button>
  </div>
{/snippet}

{#snippet filesBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold flex items-center gap-1"
        ><FileArchive class="cq-icon text-blue-500" />待解压文件</span
      >
      <span class="cq-text-sm text-muted-foreground">
        {#if isRunning && currentFileIndex >= 0}
          {currentFileIndex + 1}/{ns.archivePaths.length}
        {:else}
          {ns.archivePaths.length || parsePaths(pathsText).length} 个
        {/if}
      </span>
    </div>
    <div class="flex-1 overflow-y-auto cq-padding bg-muted/30 cq-rounded">
      {#if ns.archivePaths.length > 0 || parsePaths(pathsText).length > 0}
        {#each ns.archivePaths.length > 0 ? ns.archivePaths : parsePaths(pathsText) as filePath, idx}
          {@const isActive = ns.activeIndices.includes(idx)}
          {@const isCompleted =
            ns.phase === "completed" || ns.completedIndices.includes(idx)}
          <div
            class="cq-text-sm truncate py-0.5 flex items-center gap-1 transition-colors"
            class:text-muted-foreground={!isRunning ||
              (!isActive && !isCompleted)}
            class:text-primary={isActive}
            class:text-green-600={isCompleted}
            title={filePath}
          >
            {#if isCompleted}
              <CircleCheck class="w-3 h-3 text-green-500 shrink-0" />
            {:else if isActive}
              <LoaderCircle
                class="w-3 h-3 text-primary animate-spin shrink-0"
              />
            {:else}
              <span class="w-3 h-3 shrink-0 text-center">{idx + 1}.</span>
            {/if}
            <span class="truncate">{filePath.split(/[/\\]/).pop()}</span>
          </div>
        {/each}
      {:else}
        <div class="cq-text text-muted-foreground text-center py-3">
          暂无文件
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

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === "source"}{@render sourceBlock()}
  {:else if blockId === "options"}{@render optionsBlock()}
  {:else if blockId === "operation"}{@render operationBlock()}
  {:else if blockId === "files"}{@render filesBlock()}
  {:else if blockId === "log"}{@render logBlock()}
  {/if}
{/snippet}

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
    title="bandia"
    icon={FileArchive}
    status={ns.phase}
    {borderClass}
    {isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="bandia"
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
        nodeType="bandia"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={BANDIA_DEFAULT_GRID_LAYOUT}
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
