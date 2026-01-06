<script lang="ts">
  /**
   * MarkuNode - Markdown 模块化处理节点
   * 支持: 独立模式、Pipeline 模式、剪贴板粘贴、文件/文件夹输入、Diff 预览、撤销
   */
  import { Handle, Position, NodeResizer } from "@xyflow/svelte";
  import { Button } from "$lib/components/ui/button";
  import { Checkbox } from "$lib/components/ui/checkbox";
  import { Progress } from "$lib/components/ui/progress";
  import { Input } from "$lib/components/ui/input";
  import { Textarea } from "$lib/components/ui/textarea";
  import { NodeLayoutRenderer } from "$lib/components/blocks";
  import {
    MARKU_DEFAULT_GRID_LAYOUT,
    MARKU_MODULES,
    MARKT_CONFIG_FIELDS,
    COMMON_CONFIG_FIELDS,
  } from "./blocks";
  import { api } from "$lib/services/api";
  import { getNodeState } from "$lib/stores/nodeState.svelte";
  import { getWsBaseUrl } from "$lib/stores/backend";
  import NodeWrapper from "../NodeWrapper.svelte";
  import {
    Play,
    LoaderCircle,
    Clipboard,
    FolderOpen,
    CircleCheck,
    CircleX,
    Copy,
    Check,
    RotateCcw,
    FileText,
    Undo2,
    FileCode,
    Diff,
  } from "@lucide/svelte";

  interface Props {
    id: string;
    data?: {
      config?: {
        paths?: string;
        module?: string;
        stepConfig?: Record<string, any>;
        recursive?: boolean;
        dryRun?: boolean;
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
  type InputMode = "path" | "paste" | "upstream";

  interface MarkuState {
    phase: Phase;
    progress: number;
    progressText: string;
    pathText: string;
    pasteText: string;
    inputMode: InputMode;
    selectedModule: string;
    stepConfig: Record<string, any>;
    recursive: boolean;
    dryRun: boolean;
    enableUndo: boolean;
    result: MarkuResult | null;
    diffs: DiffItem[];
    logs: string[];
    hasInputConnection: boolean;
  }

  interface DiffItem {
    file: string;
    diff: string[];
  }

  interface MarkuResult {
    success: boolean;
    files_processed: number;
    files_changed: number;
    message: string;
  }

  const nodeId = $derived(id);
  const dataLogs = $derived(data?.logs ?? []);
  const dataHasInputConnection = $derived(data?.hasInputConnection ?? false);

  const ns = getNodeState<MarkuState>(id, {
    phase: "idle",
    progress: 0,
    progressText: "",
    pathText: data?.config?.paths || "",
    pasteText: "",
    inputMode: "path",
    selectedModule: data?.config?.module || "markt",
    stepConfig: data?.config?.stepConfig || {
      mode: "h2l",
      bullet: "- ",
      indent: 4,
    },
    recursive: data?.config?.recursive ?? false,
    dryRun: true,
    enableUndo: true,
    result: null,
    diffs: [],
    logs: [],
    hasInputConnection: false,
  });

  let copied = $state(false);
  let layoutRenderer = $state<any>(undefined);

  $effect(() => {
    ns.logs = [...dataLogs];
    ns.hasInputConnection = dataHasInputConnection;
    if (dataHasInputConnection) ns.inputMode = "upstream";
  });

  // 当前模块的配置字段
  let currentConfigFields = $derived(
    ns.selectedModule === "markt" ? MARKT_CONFIG_FIELDS : []
  );

  let canExecute = $derived(
    ns.phase === "idle" &&
      (ns.pathText.trim() !== "" ||
        ns.pasteText.trim() !== "" ||
        ns.hasInputConnection)
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
    ns.logs = [...ns.logs.slice(-50), msg];
  }

  async function pasteFromClipboard() {
    try {
      const { platform } = await import("$lib/api/platform");
      const text = await platform.readClipboard();
      if (text) {
        ns.pasteText = text.trim();
        ns.inputMode = "paste";
        log(`📋 从剪贴板读取 ${text.length} 字符`);
      }
    } catch (e) {
      log(`❌ 读取剪贴板失败: ${e}`);
    }
  }

  async function selectPath(isFolder: boolean) {
    try {
      const { platform } = await import("$lib/api/platform");
      let selected: string | null = null;
      if (isFolder) {
        selected = await platform.openFolderDialog("选择要处理的文件夹");
      } else {
        const files = await platform.openFileDialog(
          "选择 Markdown 文件",
          [{ name: "Markdown", extensions: ["md"] }],
          true
        );
        if (files && files.length > 0) selected = files.join("\n");
      }
      if (selected) {
        if (ns.pathText) ns.pathText += "\n" + selected;
        else ns.pathText = selected;
        ns.inputMode = "path";
        log(`📂 选择了: ${selected.split(/[\\/]/).pop()}`);
      }
    } catch (e) {
      log(`❌ 选择失败: ${e}`);
    }
  }

  function updateStepConfig(key: string, value: any) {
    ns.stepConfig = { ...ns.stepConfig, [key]: value };
  }

  async function handleExecute() {
    if (!canExecute) return;

    ns.phase = "running";
    ns.progress = 0;
    ns.progressText = "正在处理...";
    ns.result = null;
    ns.diffs = [];
    log(`🚀 开始${ns.dryRun ? "预览" : "执行"} ${ns.selectedModule}...`);

    const taskId = `marku-${nodeId}-${Date.now()}`;
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

      // 构建请求
      const paths = ns.pathText
        .split("\n")
        .map((p) => p.trim())
        .filter((p) => p);
      const requestData: any = {
        module: ns.selectedModule,
        paths: paths,
        paste_content: ns.inputMode === "paste" ? ns.pasteText : undefined,
        step_config: ns.stepConfig,
        recursive: ns.recursive,
        dry_run: ns.dryRun,
        enable_undo: ns.enableUndo,
      };

      const response = (await api.executeNode("marku", requestData, {
        taskId,
        nodeId,
      })) as any;

      if (response.success) {
        ns.phase = "completed";
        ns.progress = 100;
        ns.progressText = "处理完成";
        ns.result = {
          success: true,
          files_processed: response.data?.files_processed ?? 0,
          files_changed: response.data?.files_changed ?? 0,
          message: response.message,
        };
        ns.diffs = response.data?.diffs ?? [];
        log(`✅ ${response.message}`);
      } else {
        ns.phase = "error";
        ns.progress = 0;
        log(`❌ 处理失败: ${response.message}`);
      }
    } catch (error) {
      ns.phase = "error";
      ns.progress = 0;
      log(`❌ 处理失败: ${error}`);
    } finally {
      if (ws && ws.readyState === WebSocket.OPEN) ws.close();
    }
  }

  async function handleUndo() {
    log("⏪ 执行撤销...");
    try {
      const response = (await api.executeNode(
        "marku",
        { action: "undo" },
        { nodeId }
      )) as any;
      if (response.success) {
        log(`✅ ${response.message}`);
      } else {
        log(`❌ ${response.message}`);
      }
    } catch (e) {
      log(`❌ 撤销失败: ${e}`);
    }
  }

  function handleReset() {
    ns.phase = "idle";
    ns.progress = 0;
    ns.progressText = "";
    ns.result = null;
    ns.diffs = [];
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
  <div class="flex flex-col cq-gap h-full">
    {#if !ns.hasInputConnection}
      <div class="flex cq-gap flex-wrap">
        <Button
          variant={ns.inputMode === "path" ? "default" : "outline"}
          size="sm"
          class="cq-button-sm"
          onclick={() => (ns.inputMode = "path")}
        >
          <FolderOpen class="cq-icon mr-1" />路径
        </Button>
        <Button
          variant={ns.inputMode === "paste" ? "default" : "outline"}
          size="sm"
          class="cq-button-sm"
          onclick={() => (ns.inputMode = "paste")}
        >
          <Clipboard class="cq-icon mr-1" />粘贴
        </Button>
      </div>

      {#if ns.inputMode === "path"}
        <div class="flex cq-gap">
          <Button
            variant="outline"
            size="sm"
            class="cq-button-sm flex-1"
            onclick={() => selectPath(true)}
            disabled={isRunning}
          >
            <FolderOpen class="cq-icon mr-1" />文件夹
          </Button>
          <Button
            variant="outline"
            size="sm"
            class="cq-button-sm flex-1"
            onclick={() => selectPath(false)}
            disabled={isRunning}
          >
            <FileText class="cq-icon mr-1" />文件
          </Button>
        </div>
        <textarea
          bind:value={ns.pathText}
          placeholder="输入文件或文件夹路径，每行一个"
          disabled={isRunning}
          class="cq-text font-mono w-full flex-1 min-h-[60px] p-2 bg-background border rounded-md resize-none"
        ></textarea>
      {:else}
        <div class="flex cq-gap">
          <Button
            variant="outline"
            size="sm"
            class="cq-button-sm flex-1"
            onclick={pasteFromClipboard}
            disabled={isRunning}
          >
            <Clipboard class="cq-icon mr-1" />从剪贴板读取
          </Button>
        </div>
        <textarea
          bind:value={ns.pasteText}
          placeholder="粘贴 Markdown 内容直接处理"
          disabled={isRunning}
          class="cq-text font-mono w-full flex-1 min-h-[80px] p-2 bg-background border rounded-md resize-none"
        ></textarea>
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

{#snippet moduleBlock()}
  <div class="flex flex-col cq-gap h-full overflow-y-auto pr-1">
    {#each MARKU_MODULES as m}
      <div
        class="flex items-center cq-gap cursor-pointer p-1 hover:bg-muted/50 rounded transition-colors {ns.selectedModule ===
        m.id
          ? 'bg-primary/10 border border-primary/30'
          : ''}"
        onclick={() => !isRunning && (ns.selectedModule = m.id)}
      >
        <div class="flex flex-col">
          <span class="cq-text font-medium">{m.name}</span>
          <span class="cq-text-xs text-muted-foreground">{m.desc}</span>
        </div>
      </div>
    {/each}
  </div>
{/snippet}

{#snippet configBlock()}
  <div class="flex flex-col cq-gap h-full overflow-y-auto pr-1">
    <div class="cq-text-sm font-semibold text-muted-foreground mb-1">
      {ns.selectedModule} 配置
    </div>
    {#each currentConfigFields as field}
      <div class="flex items-center justify-between cq-gap">
        <span class="cq-text-sm">{field.label}</span>
        {#if field.type === "boolean"}
          <Checkbox
            checked={ns.stepConfig[field.key] ?? field.default}
            onCheckedChange={(v) => updateStepConfig(field.key, v)}
            disabled={isRunning}
          />
        {:else if field.type === "select"}
          <select
            class="cq-text-sm bg-background border rounded px-2 py-1"
            value={ns.stepConfig[field.key] ?? field.default}
            onchange={(e) => updateStepConfig(field.key, e.currentTarget.value)}
            disabled={isRunning}
          >
            {#each field.options as opt}
              <option value={opt}>{opt}</option>
            {/each}
          </select>
        {:else if field.type === "number"}
          <Input
            type="number"
            class="w-16 cq-text-sm"
            value={ns.stepConfig[field.key] ?? field.default}
            oninput={(e) =>
              updateStepConfig(
                field.key,
                parseInt(e.currentTarget.value) || field.default
              )}
            disabled={isRunning}
          />
        {/if}
      </div>
    {/each}
    {#if currentConfigFields.length === 0}
      <div class="cq-text-sm text-muted-foreground">该模块无需额外配置</div>
    {/if}
  </div>
{/snippet}

{#snippet optionsBlock()}
  <div class="flex flex-col cq-gap">
    <div
      class="flex items-center cq-gap cursor-pointer"
      onclick={() => {
        if (!isRunning) ns.recursive = !ns.recursive;
      }}
    >
      <Checkbox checked={ns.recursive} disabled={isRunning} />
      <span class="cq-text">递归处理子目录</span>
    </div>
    <div
      class="flex items-center cq-gap cursor-pointer"
      onclick={() => {
        if (!isRunning) ns.dryRun = !ns.dryRun;
      }}
    >
      <Checkbox checked={ns.dryRun} disabled={isRunning} />
      <span class="cq-text">预览模式 (Dry Run)</span>
    </div>
    <div
      class="flex items-center cq-gap cursor-pointer"
      onclick={() => {
        if (!isRunning) ns.enableUndo = !ns.enableUndo;
      }}
    >
      <Checkbox checked={ns.enableUndo} disabled={isRunning} />
      <span class="cq-text">启用 Git 撤销</span>
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
        <FileCode class="cq-icon text-muted-foreground/50 shrink-0" />
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
          >{ns.dryRun ? "预览处理" : "立即执行"}</span
        >
      </Button>
    {:else if ns.phase === "running"}
      <Button class="w-full cq-button flex-1" disabled>
        <LoaderCircle class="cq-icon mr-1 animate-spin" /><span>处理中...</span>
      </Button>
    {:else if ns.phase === "completed"}
      <div class="flex cq-gap">
        <Button class="flex-1 cq-button" onclick={handleReset}>
          <RotateCcw class="cq-icon mr-1" /><span>重置</span>
        </Button>
        <Button variant="outline" class="flex-1 cq-button" onclick={handleUndo}>
          <Undo2 class="cq-icon mr-1" /><span>撤销</span>
        </Button>
      </div>
    {/if}
  </div>
{/snippet}

{#snippet diffBlock()}
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex items-center justify-between mb-1 shrink-0">
      <span class="cq-text font-semibold">Diff 预览</span>
      <span class="cq-text-xs text-muted-foreground"
        >{ns.diffs.length} 个文件</span
      >
    </div>
    <div
      class="flex-1 overflow-y-auto bg-muted/30 cq-rounded cq-padding font-mono text-[10px]"
      style="min-height: 100px;"
    >
      {#if ns.diffs.length > 0}
        {#each ns.diffs as d}
          <div class="mb-2">
            <div class="text-primary font-semibold truncate">
              {d.file.split(/[\\/]/).pop()}
            </div>
            <div class="whitespace-pre-wrap break-all text-muted-foreground">
              {#each d.diff.slice(0, 30) as line}
                <div
                  class={line.startsWith("+")
                    ? "text-green-500"
                    : line.startsWith("-")
                      ? "text-red-500"
                      : ""}
                >
                  {line}
                </div>
              {/each}
              {#if d.diff.length > 30}
                <div class="text-muted-foreground">... (截断)</div>
              {/if}
            </div>
          </div>
        {/each}
      {:else}
        <div class="text-muted-foreground text-center py-3">
          {ns.dryRun ? "执行预览后将在此显示变更" : "暂无变更"}
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
  {:else if blockId === "module"}{@render moduleBlock()}
  {:else if blockId === "config"}{@render configBlock()}
  {:else if blockId === "options"}{@render optionsBlock()}
  {:else if blockId === "operation"}{@render operationBlock()}
  {:else if blockId === "diff"}{@render diffBlock()}
  {:else if blockId === "log"}{@render logBlock()}
  {/if}
{/snippet}

<div
  class="h-full w-full flex flex-col overflow-hidden"
  style={!isFullscreenRender ? "max-width: 500px;" : ""}
>
  {#if !isFullscreenRender}
    <NodeResizer minWidth={350} minHeight={300} maxWidth={600} />
    <Handle type="target" position={Position.Left} class="bg-primary!" />
  {/if}

  <NodeWrapper
    {nodeId}
    title="marku"
    icon={FileCode}
    status={ns.phase}
    {borderClass}
    {isFullscreenRender}
    onCompact={() => layoutRenderer?.compact()}
    onResetLayout={() => layoutRenderer?.resetLayout()}
    nodeType="marku"
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
        nodeType="marku"
        isFullscreen={isFullscreenRender}
        defaultFullscreenLayout={MARKU_DEFAULT_GRID_LAYOUT}
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
