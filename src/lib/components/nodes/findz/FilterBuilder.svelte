<script lang="ts">
  /**
   * FilterBuilder - 直观的文件过滤器构建器
   * 采用组件化重构，主文件保持精简
   */
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { Code, Sparkles } from "@lucide/svelte";
  import { type FilterConfig, defaultConfig } from "./FilterTypes";
  import { generateSql } from "./filterLogic";
  import PresetManager from "./PresetManager.svelte";
  import BasicFilters from "./BasicFilters.svelte";
  import AdvancedFilters from "./AdvancedFilters.svelte";

  interface Props {
    /** 当前配置 */
    value?: FilterConfig;
    /** 配置变化回调，返回 JSON 配置和生成的 SQL */
    onchange?: (config: FilterConfig, sql: string) => void;
    /** 是否禁用 */
    disabled?: boolean;
    /** 是否显示高级模式切换 */
    showAdvanced?: boolean;
    /** 高级模式（直接输入 SQL） */
    advancedMode?: boolean;
    /** SQL 值（高级模式用） */
    sqlValue?: string;
    /** 高级模式切换回调 */
    onAdvancedChange?: (advanced: boolean) => void;
    /** 图片元数据启用回调 */
    onImageMetaChange?: (enabled: boolean) => void;
  }

  let {
    value,
    onchange,
    disabled = false,
    showAdvanced = true,
    advancedMode = false,
    sqlValue = "1",
    onAdvancedChange,
    onImageMetaChange,
  }: Props = $props();

  let config = $state<FilterConfig>(value ?? { ...defaultConfig });
  let internalSql = $state(sqlValue);

  // 当外部传入的 sqlValue 改变时同步内部
  $effect(() => {
    if (advancedMode) {
      internalSql = sqlValue;
    }
  });

  // 触发变化
  function emitChange() {
    const sql = generateSql(config);
    internalSql = sql;

    // 如果启用了图片元数据，通知父组件（因为可能需要后端额外读取元数据）
    if (config.imageMetaEnabled && onImageMetaChange) {
      onImageMetaChange(true);
    }

    onchange?.(config, sql);
  }

  // 切换高级模式
  function toggleAdvanced() {
    onAdvancedChange?.(!advancedMode);
  }

  // 处理预设应用
  function handleApplyPreset(newConfig: FilterConfig) {
    config = { ...newConfig };
    emitChange();
  }
</script>

<div class="filter-builder space-y-3">
  <!-- 模式切换和预设按钮 -->
  {#if showAdvanced}
    <div class="flex items-center justify-between gap-2">
      <PresetManager {config} onApply={handleApplyPreset} {disabled} />

      <!-- 模式切换 -->
      <Button
        variant="ghost"
        size="sm"
        class="h-6 text-xs"
        onclick={toggleAdvanced}
      >
        {#if advancedMode}
          <Sparkles class="w-3 h-3 mr-1" />可视化
        {:else}
          <Code class="w-3 h-3 mr-1" />SQL
        {/if}
      </Button>
    </div>
  {/if}

  {#if advancedMode}
    <!-- SQL 直接输入模式 -->
    <Input
      bind:value={internalSql}
      placeholder="例: size > 10M and ext in ('zip', 'rar')"
      class="font-mono text-xs"
      {disabled}
      oninput={() => onchange?.(config, internalSql)}
    />
  {:else}
    <!-- 可视化模式 -->
    <div class="max-h-[500px] overflow-y-auto pr-1 space-y-4">
      <!-- 基础过滤器：类型、大小、日期、名称 -->
      <BasicFilters bind:config {disabled} onchange={emitChange} />

      <!-- 分割线 -->
      <div class="border-t pt-1"></div>

      <!-- 高级过滤器：图片尺寸、容器平均大小、位置、类型 -->
      <AdvancedFilters bind:config {disabled} onchange={emitChange} />
    </div>

    <!-- 生成的条件预览 -->
    <div
      class="text-[10px] text-muted-foreground font-mono bg-muted/30 rounded px-2 py-1 truncate mt-2"
      title={internalSql}
    >
      {internalSql === "1" ? "匹配所有文件" : internalSql}
    </div>
  {/if}
</div>
