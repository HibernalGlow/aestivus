<script lang="ts">
  /**
   * Aestivus - 开发者设置面板
   * 包含 Dev Mode 切换等开发调试功能
   */
  import { Code, RefreshCw, ExternalLink } from "@lucide/svelte";
  import { Switch } from "$lib/components/ui/switch";
  import { Input } from "$lib/components/ui/input";
  import { Button } from "$lib/components/ui/button";
  import * as Card from "$lib/components/ui/card";
  import {
    switchToDevMode,
    switchToReleaseMode,
    getDevModeStatus,
    setDevUrl,
  } from "$lib/api/devMode";

  let isDevMode = $state(false);
  let devUrl = $state("http://localhost:1096");
  let isLoading = $state(false);
  let statusMessage = $state("");

  // 初始化时获取当前状态
  $effect(() => {
    loadDevModeStatus();
  });

  async function loadDevModeStatus() {
    try {
      isDevMode = await getDevModeStatus();
    } catch (e) {
      console.error("Failed to load dev mode status:", e);
    }
  }

  async function handleDevModeToggle(checked: boolean) {
    isLoading = true;
    statusMessage = "";
    try {
      if (checked) {
        // 先设置 URL，再切换模式
        await setDevUrl(devUrl);
        const result = await switchToDevMode();
        statusMessage = result;
        isDevMode = true;
      } else {
        const result = await switchToReleaseMode();
        statusMessage = result;
        isDevMode = false;
      }
    } catch (e) {
      statusMessage = `错误: ${e}`;
      console.error("Failed to toggle dev mode:", e);
    } finally {
      isLoading = false;
    }
  }

  async function handleRefresh() {
    isLoading = true;
    try {
      if (isDevMode) {
        await setDevUrl(devUrl);
        await switchToDevMode();
        statusMessage = "已刷新到开发服务器";
      } else {
        await switchToReleaseMode();
        statusMessage = "已刷新到打包版本";
      }
    } catch (e) {
      statusMessage = `刷新失败: ${e}`;
    } finally {
      isLoading = false;
    }
  }
</script>

<div class="space-y-6 p-6">
  <div class="space-y-2">
    <h3 class="text-lg font-semibold">开发者设置</h3>
    <p class="text-sm text-muted-foreground">调试和开发相关的设置选项</p>
  </div>

  <Card.Root>
    <Card.Header>
      <Card.Title class="flex items-center gap-2">
        <Code class="h-5 w-5" />
        Dev Mode
      </Card.Title>
      <Card.Description>
        启用后，webview 将从本地开发服务器加载，而不是使用打包的静态文件。
        <br />
        <span class="text-amber-500">注意：需要先启动开发服务器 (yarn dev)</span
        >
      </Card.Description>
    </Card.Header>
    <Card.Content class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium">启用 Dev Mode</span>
          {#if isDevMode}
            <span
              class="inline-flex items-center rounded-full bg-green-500/10 px-2 py-0.5 text-xs font-medium text-green-500"
            >
              开发模式
            </span>
          {:else}
            <span
              class="inline-flex items-center rounded-full bg-blue-500/10 px-2 py-0.5 text-xs font-medium text-blue-500"
            >
              正式模式
            </span>
          {/if}
        </div>
        <Switch
          checked={isDevMode}
          onCheckedChange={handleDevModeToggle}
          disabled={isLoading}
        />
      </div>

      <div class="space-y-2">
        <label for="dev-url" class="text-sm font-medium">开发服务器 URL</label>
        <div class="flex gap-2">
          <Input
            id="dev-url"
            bind:value={devUrl}
            placeholder="http://localhost:1096"
            class="flex-1"
          />
          <Button
            variant="outline"
            size="icon"
            onclick={handleRefresh}
            disabled={isLoading}
            title="刷新"
          >
            <RefreshCw class="h-4 w-4 {isLoading ? 'animate-spin' : ''}" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onclick={() => window.open(devUrl, "_blank")}
            title="在浏览器中打开"
          >
            <ExternalLink class="h-4 w-4" />
          </Button>
        </div>
        <p class="text-xs text-muted-foreground">
          默认端口: 1096 (Vite dev server)
        </p>
      </div>

      {#if statusMessage}
        <div
          class="rounded-md p-3 text-sm {statusMessage.startsWith('错误')
            ? 'bg-destructive/10 text-destructive'
            : 'bg-green-500/10 text-green-600'}"
        >
          {statusMessage}
        </div>
      {/if}
    </Card.Content>
  </Card.Root>

  <Card.Root>
    <Card.Header>
      <Card.Title>使用说明</Card.Title>
    </Card.Header>
    <Card.Content class="space-y-2 text-sm text-muted-foreground">
      <ol class="list-inside list-decimal space-y-1">
        <li>
          在终端运行 <code class="rounded bg-muted px-1">yarn dev</code> 启动开发服务器
        </li>
        <li>确认开发服务器运行在指定端口（默认 1096）</li>
        <li>开启 Dev Mode 开关</li>
        <li>页面将自动切换到开发服务器，支持 HMR 热重载</li>
        <li>调试完成后，关闭 Dev Mode 返回正式版本</li>
      </ol>
    </Card.Content>
  </Card.Root>
</div>
