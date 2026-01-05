<script lang="ts">
  /**
   * CleanfNode - 文件清理节点组件
   * 删除空文件夹、备份文件、临时文件夹等
   */
  import { Handle, Position, NodeResizer } from "@xyflow/svelte";
  import { Button } from "$lib/components/ui/button";
  import { Checkbox } from "$lib/components/ui/checkbox";
  import { Progress } from "$lib/components/ui/progress";
  import { Input } from "$lib/components/ui/input";
  import { NodeLayoutRenderer } from "$lib/components/blocks";
  import { CLEANF_DEFAULT_GRID_LAYOUT } from "./blocks";
  import { api } from "$lib/services/api";
  import { getNodeState } from "$lib/stores/nodeState.svelte";
  import { getWsBaseUrl } from "$lib/stores/backend";
  import NodeWrapper from "../NodeWrapper.svelte";
  import {
    Play,
    LoaderCircle,
    Clipboard,
    FolderOpen,
    Trash2,
    CircleCheck,
    CircleX,
    Copy,
    Check,
    RotateCcw,
    Brush,
  } from "@lucide/svelte";

  interface Props {
    id: string;
    data?: {
      config?: {
        paths?: string;
        presets?: string[];
        exclude?: string;
        preview?: boolean;
      };
      status?: "idle" | "running" | "completed" | "error";
      hasInputConnection?: boolean;
      logs?: string[];
      label?: string;
    };
    isFullscreenRender?: boolean;
  }

  let { id, data = {}, isFullscreenRender = false }: Props = $props();

  type Phase = "idle" | "running" | "completed" | "error";

  interface CleanfState {
    phase: Phase;
    progress: number;
    progressText: string;
    pathText: string;
    selectedPresets: string[];
    excludeKeywords: string;
    previewMode: boolean;
    result: CleanfResult | null;
    logs: string[];
    hasInputConnection: boolean;
  }

  interface CleanfResult {
    success: boolean;
    total_removed: number;
    details: Record<string, number>;
    preview_files: string[];
  }

  const nodeId = $derived(id);
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  const ns = getNodeState<CleanfState>(id, {
    phase: "idle",
    progress: 0,
    progressText: "",
    pathText: data?.config?.paths || "",
    selectedPresets: data?.config?.presets || ["empty_folders", "backup_files"],
    excludeKeywords: data?.config?.exclude || "",
    previewMode: data?.config?.preview ?? false,
    result: null,
    logs: [],
    hasInputConnection: false,
  });

  let copied = $state(false);
  let layoutRenderer = $state<any>(undefined);

  $effect(() => {
    ns.logs = [...dataLogs];
    ns.hasInputConnection = dataHasInputConnection;
  });

  const presets = [
    { id: "empty_folders", name: "空文件夹", desc: "递归删除所有空文件夹" },
    { id: "backup_files", name: "备份文件", desc: "删除 .bak 备份文件" },
    { id: "temp_folders", name: "临时文件夹", desc: "删除 temp_ 开头的文件夹" },
    { id: "trash_files", name: "垃圾文件", desc: "删除 .trash 文件" },
    { id: "hb_txt_files", name: "[#hb]文本", desc: "删除 [#hb] 开头的 txt" },
    { id: "log_files", name: "日志文件", desc: "删除 .log 文件" },
    { id: "upscale", name: "Upscale", desc: "删除 .upbak 文件" },
  ];

  let canExecute = $derived(
    ns.phase === "idle" && (ns.pathText.trim() !== "" || ns.hasInputConnection)
  );
  let isRunning = $derived(ns.phase === "running");
  let borderClass = $derived(
    {
      idle: "border-border",
      running: "border-primary shadow-sm",
      completed: "border-primary/50",
      error: "border-destructive/50",
    }[ns.phase]
  );

  function log(msg: string) {
    ns.logs = [...ns.logs.slice(-30), msg];
  }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import("$lib/api/platform");
      const text = await platform.readClipboard();
      if (text) {
        ns.pathText = text.trim();
        log(`📋 从剪贴板读取路径`);
      }
    } catch (e) {
      log(`❌ 读取剪贴板失败: ${e}`);
    }
  }

  async function selectFolder() {
    try {
      const { platform } = await import("$lib/api/platform");
      const selected = await platform.openFolderDialog("选择要处理的文件夹");
      if (selected) {
        if (ns.pathText) ns.pathText += "\n" + selected;
        else ns.pathText = selected;
        log(`📁 选择了文件夹: ${selected.split(/[/\\]/).pop()}`);
      }
    } catch (e) {
      log(`❌ 选择文件夹失败: ${e}`);
    }
  }

  function togglePreset(pid: string) {
    if (ns.selectedPresets.includes(pid)) {
      ns.selectedPresets = ns.selectedPresets.filter((id) => id !== pid);
    } else {
      ns.selectedPresets = [...ns.selectedPresets, pid];
    }
  }

  async function handleExecute() {
    if (!canExecute) return;
    const paths = ns.pathText
      .split("\n")
      .map((p) => p.trim())
      .filter((p) => p);
    if (paths.length === 0 && !ns.hasInputConnection) {
      log("❌ 请输入路径");
      return;
    }

    ns.phase = "running";
    ns.progress = 0;
    ns.progressText = "正在处理...";
    ns.result = null;
    log(`🧹 开始${ns.previewMode ? "预览" : "执行"}文件清理...`);

    const taskId = `cleanf-${nodeId}-${Date.now()}`;
    let ws: WebSocket | null = null;

    try {
      const wsUrl = `${getWsBaseUrl()}/v1/ws/tasks/${taskId}`;
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "progress") {
            ns.progress = msg.progress;
            ns.progressText = msg.message;
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
        "cleanf",
        {
          paths: paths,
          presets: ns.selectedPresets,
          exclude: ns.excludeKeywords || undefined,
          preview: ns.previewMode,
        },
        { taskId, nodeId }
      )) as any;

      if (response.success) {
        ns.phase = "completed";
        ns.progress = 100;
        ns.progressText = "清理完成";
        ns.result = {
          success: true,
          total_removed: response.data?.total_removed ?? 0,
          details: response.data?.removed_details ?? {},
          preview_files: response.data?.preview_files ?? [],
        };
        log(`✅ ${response.message}`);
      } else {
        ns.phase = "error";
        ns.progress = 0;
        log(`❌ 清理失败: ${response.message}`);
      }
    } catch (error) {
      ns.phase = "error";
      ns.progress = 0;
      log(`❌ 清理失败: ${error}`);
    } finally {
      if (ws && ws.readyState === WebSocket.OPEN) ws.close();
    }
  }

  function handleReset() {
    ns.phase = "idle";
    ns.progress = 0;
    ns.progressText = "";
    ns.result = null;
    ns.logs = [];
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
</script>

{#snippet sourceBlock()}
  {#if !ns.hasInputConnection}
    <div class="flex flex-col cq-gap h-full">
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
          onclick={selectFolder}
          disabled={isRunning}
        >
          <FolderOpen class="cq-icon mr-1" />选择
        </Button>
      </div>
      <textarea
        bind:value={ns.pathText}
        placeholder="输入文件夹路径，每行一个"
        disabled={isRunning}
        class="cq-text font-mono w-full flex-1 min-h-[60px] p-2 bg-background border rounded-md resize-none"
      ></textarea>
    </div>
  {:else}
    <div
      class="text-muted-foreground cq-padding bg-muted cq-rounded flex items-center cq-gap cq-text"
    >
      <span>←</span><span>输入来自上游节点</span>
    </div>
  {/if}
{/snippet}

{#snippet presetsBlock()}
  <div class="flex flex-col cq-gap h-full overflow-y-auto pr-1">
    {#each presets as p}
      <div
        class="flex items-center cq-gap cursor-pointer p-1 hover:bg-muted/50 rounded transition-colors"
        onclick={() => !isRunning && togglePreset(p.id)}
      >
        <Checkbox
          checked={ns.selectedPresets.includes(p.id)}
          disabled={isRunning}
        />
        <div class="flex flex-col">
          <span class="cq-text font-medium">{p.name}</span>
          <span class="cq-text-xs text-muted-foreground">{p.desc}</span>
        </div>
      </div>
    {/each}
  </div>
{/snippet}

{#snippet optionsBlock()}
  <div class="flex flex-col cq-gap">
    <div
      class="flex items-center cq-gap cursor-pointer"
      onclick={() => {
        if (!isRunning) ns.previewMode = !ns.previewMode;
      }}
    >
      <Checkbox checked={ns.previewMode} disabled={isRunning} />
      <span class="cq-text">预览模式（不实际删除）</span>
    </div>
    <div class="flex flex-col cq-gap mt-1">
      <span class="cq-text-sm text-muted-foreground">排除关键词</span>
      <Input
        bind:value={ns.excludeKeywords}
        placeholder="逗号分隔，如: node_modules, .git"
        disabled={isRunning}
        class="cq-text-sm"
      />
    </div>
  </div>
{/snippet}

{#snippet operationBlock()}
  <div class="flex flex-col cq-gap h-full">
    <div class="flex items-center cq-gap cq-padding bg-muted/30 cq-rounded">
      {#if ns.result}
        {#if ns.result.success}
          <CircleCheck class="cq-icon text-green-500 shrink-0" />
          <span class="cq-text text-green-600 font-medium">完成</span>
        {:else}
          <CircleX class="cq-icon text-red-500 shrink-0" />
          <span class="cq-text text-red-600 font-medium">失败</span>
        {/if}
      {:else if isRunning}
        <LoaderCircle class="cq-icon text-primary animate-spin shrink-0" />
        <div class="flex-1"><Progress value={ns.progress} class="h-1.5" /></div>
        <span class="cq-text-sm text-muted-foreground">{ns.progress}%</span>
      {:else}
        <Brush class="cq-icon text-muted-foreground/50 shrink-0" />
        <span class="cq-text text-muted-foreground">等待执行</span>
      {/if}
    </div>
    {#if ns.phase === "idle" || ns.phase === "error"}
      <Button
        class="w-full cq-button flex-1"
        onclick={handleExecute}
        disabled={!canExecute}
      >
        <Play class="cq-icon mr-1" /><span
          >{ns.previewMode ? "预览清理" : "立即清理"}</span
        >
      </Button>
    {:else if ns.phase === "running"}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span
          >正在清理...</span
        >
      </Button>
    {:else if ns.phase === "completed"}
      <Button class="w-full cq-button flex-1" onclick={handleReset}>
        <RotateCcw class="cq-icon mr-1" /><span>执行新任务</span>
      </Button>
    {/if}
  </div>
{/snippet}

{#snippet resultBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">清理结果</span>
    </div>
    <div class="flex-1 overflow-y-auto cq-padding bg-muted/30 cq-rounded">
      {#if ns.result}
        <div class="space-y-2">
          <div
            class="flex justify-between items-center bg-background/50 p-2 rounded"
          >
            <span class="cq-text-sm font-bold">总计删除</span>
            <span class="text-green-600 font-bold"
              >{ns.result.total_removed}</span
            >
          </div>

          {#if Object.keys(ns.result.details).length > 0}
            <div class="space-y-1 mt-2">
              <div class="cq-text-xs text-muted-foreground font-semibold px-1">
                详情:
              </div>
              {#each Object.entries(ns.result.details) as [key, count]}
                {#if count > 0}
                  <div class="flex justify-between px-1 cq-text-sm">
                    <span>{presets.find((p) => p.id === key)?.name || key}</span
                    >
                    <span class="text-green-600">{count}</span>
                  </div>
                {/if}
              {/each}
            </div>
          {/if}

          {#if ns.result.preview_files.length > 0}
            <div class="space-y-1 mt-2">
              <div class="cq-text-xs text-muted-foreground font-semibold px-1">
                待删除项目 ({ns.result.preview_files.length}):
              </div>
              <div
                class="max-h-40 overflow-y-auto bg-background/30 p-1 rounded text-[10px] font-mono whitespace-pre-wrap break-all"
              >
                {ns.result.preview_files.join("\n")}
              </div>
            </div>
          {/if}
        </div>
      {:else}
        <div class="cq-text text-muted-foreground text-center py-3">
          暂无结果
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
      style="min-height: 80px;"
    >
      {#if ns.logs.length > 0}
        {#each ns.logs as logItem}<div class="text-muted-foreground break-all">
            {logItem}
          </div>{/each}
      {:else}
        <div class="text-muted-foreground text-center py-2">等待操作...</div>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet renderBlockContent(blockId: string)}
  {#if blockId === "source"}{@render sourceBlock()}
  {:else if blockId === "presets"}{@render presetsBlock()}
  {:else if blockId === "options"}{@render optionsBlock()}
  {:else if blockId === "operation"}{@render operationBlock()}
  {:else if blockId === "result"}{@render resultBlock()}
  {:else if blockId === "log"}{@render logBlock()}
  {/if}
{/snippet}

<div
  class="h-full w-full flex flex-col overflow-hidden"
  style={!isFullscreenRender ? "max-width: 450px;" : ""}
>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={300} minHeight={250} maxWidth={500} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper
    {nodeId}
    title="cleanf"
    icon={Brush}
    status={ns.phase}
    {borderClass}
    {isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="cleanf"
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
        nodeType="cleanf"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={CLEANF_DEFAULT_GRID_LAYOUT}
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
