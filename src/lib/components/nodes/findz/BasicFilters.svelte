<script lang="ts">
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import * as Select from "$lib/components/ui/select";
  import { Plus, X, File, HardDrive, Calendar, FileText } from "@lucide/svelte";
  import {
    type FilterConfig,
    FILE_TYPE_PRESETS,
    SIZE_PRESETS,
    DATE_PRESETS,
  } from "./FilterTypes";

  interface Props {
    config: FilterConfig;
    disabled?: boolean;
    onchange: () => void;
  }

  let { config = $bindable(), disabled = false, onchange }: Props = $props();

  let customExtInput = $state("");
  let excludeExtInput = $state("");

  function toggleFileType(typeId: string) {
    if (config.fileTypes.includes(typeId)) {
      config.fileTypes = config.fileTypes.filter((t) => t !== typeId);
    } else {
      config.fileTypes = [...config.fileTypes, typeId];
    }
    onchange();
  }

  function addCustomExt() {
    const ext = customExtInput.trim().replace(/^\./, "").toLowerCase();
    if (ext && !config.customExts.includes(ext)) {
      config.customExts = [...config.customExts, ext];
      customExtInput = "";
      onchange();
    }
  }

  function removeCustomExt(ext: string) {
    config.customExts = config.customExts.filter((e) => e !== ext);
    onchange();
  }

  function addExcludeExt() {
    const ext = excludeExtInput.trim().replace(/^\./, "").toLowerCase();
    if (ext && !config.excludeExts.includes(ext)) {
      config.excludeExts = [...config.excludeExts, ext];
      excludeExtInput = "";
      onchange();
    }
  }

  function removeExcludeExt(ext: string) {
    config.excludeExts = config.excludeExts.filter((e) => e !== ext);
    onchange();
  }

  function applySizePreset(preset: (typeof SIZE_PRESETS)[0]) {
    config.sizeEnabled = true;
    config.sizeMin = preset.min;
    config.sizeMax = preset.max;
    onchange();
  }
</script>

<div class="space-y-3">
  <!-- 文件类型快捷选择 -->
  <div>
    <div class="text-xs font-medium mb-1.5 flex items-center gap-1">
      <File class="w-3 h-3" />文件类型
    </div>
    <div class="flex flex-wrap gap-1.5">
      {#each FILE_TYPE_PRESETS as preset}
        {@const isActive = config.fileTypes.includes(preset.id)}
        <button
          class="flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors
            {isActive
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted hover:bg-muted/80'}"
          onclick={() => toggleFileType(preset.id)}
          {disabled}
        >
          <preset.icon class="w-3 h-3" />
          {preset.label}
        </button>
      {/each}
    </div>

    <!-- 自定义扩展名 -->
    <div class="flex items-center gap-1 mt-2">
      <Input
        bind:value={customExtInput}
        placeholder="自定义扩展名"
        class="h-7 text-xs flex-1"
        {disabled}
        onkeydown={(e) => e.key === "Enter" && addCustomExt()}
      />
      <Button
        variant="outline"
        size="sm"
        class="h-7"
        onclick={addCustomExt}
        {disabled}
      >
        <Plus class="w-3 h-3" />
      </Button>
    </div>
    {#if config.customExts.length > 0}
      <div class="flex flex-wrap gap-1 mt-1">
        {#each config.customExts as ext}
          <span
            class="inline-flex items-center gap-1 px-1.5 py-0.5 bg-blue-500/20 text-blue-600 rounded text-xs"
          >
            .{ext}
            <button
              onclick={() => removeCustomExt(ext)}
              class="hover:text-red-500"
            >
              <X class="w-3 h-3" />
            </button>
          </span>
        {/each}
      </div>
    {/if}

    <!-- 排除扩展名 -->
    <div class="flex items-center gap-1 mt-2">
      <Input
        bind:value={excludeExtInput}
        placeholder="排除扩展名"
        class="h-7 text-xs flex-1"
        {disabled}
        onkeydown={(e) => e.key === "Enter" && addExcludeExt()}
      />
      <Button
        variant="outline"
        size="sm"
        class="h-7"
        onclick={addExcludeExt}
        {disabled}
      >
        <X class="w-3 h-3" />
      </Button>
    </div>
    {#if config.excludeExts.length > 0}
      <div class="flex flex-wrap gap-1 mt-1">
        {#each config.excludeExts as ext}
          <span
            class="inline-flex items-center gap-1 px-1.5 py-0.5 bg-red-500/20 text-red-600 rounded text-xs"
          >
            .{ext}
            <button
              onclick={() => removeExcludeExt(ext)}
              class="hover:text-red-700"
            >
              <X class="w-3 h-3" />
            </button>
          </span>
        {/each}
      </div>
    {/if}
  </div>

  <!-- 文件大小 -->
  <div>
    <div class="flex items-center justify-between mb-1.5">
      <label class="text-xs font-medium flex items-center gap-1">
        <HardDrive class="w-3 h-3" />文件大小
      </label>
      <input
        type="checkbox"
        bind:checked={config.sizeEnabled}
        {onchange}
        {disabled}
        class="w-3.5 h-3.5"
      />
    </div>
    {#if config.sizeEnabled}
      <div class="flex flex-wrap gap-1 mb-2">
        {#each SIZE_PRESETS as preset}
          <button
            class="px-2 py-0.5 rounded text-xs bg-muted hover:bg-muted/80"
            onclick={() => applySizePreset(preset)}
            {disabled}
          >
            {preset.label}
          </button>
        {/each}
      </div>
      <div class="flex items-center gap-2">
        <Input
          bind:value={config.sizeMin}
          placeholder="最小 (如 10M)"
          class="h-7 text-xs flex-1"
          {disabled}
          oninput={onchange}
        />
        <span class="text-xs text-muted-foreground">~</span>
        <Input
          bind:value={config.sizeMax}
          placeholder="最大 (如 1G)"
          class="h-7 text-xs flex-1"
          {disabled}
          oninput={onchange}
        />
      </div>
    {/if}
  </div>

  <!-- 修改日期 -->
  <div>
    <div class="flex items-center justify-between mb-1.5">
      <label class="text-xs font-medium flex items-center gap-1">
        <Calendar class="w-3 h-3" />修改日期
      </label>
      <input
        type="checkbox"
        bind:checked={config.dateEnabled}
        {onchange}
        {disabled}
        class="w-3.5 h-3.5"
      />
    </div>
    {#if config.dateEnabled}
      <div class="flex flex-wrap gap-1">
        {#each DATE_PRESETS as preset}
          <button
            class="px-2 py-0.5 rounded text-xs transition-colors
              {config.datePreset === preset.value
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted hover:bg-muted/80'}"
            onclick={() => {
              config.datePreset = preset.value;
              onchange();
            }}
            {disabled}
          >
            {preset.label}
          </button>
        {/each}
      </div>
      {#if config.datePreset === "custom"}
        <div class="flex items-center gap-2 mt-2">
          <Input
            type="date"
            bind:value={config.dateStart}
            class="h-7 text-xs flex-1"
            {disabled}
            oninput={onchange}
          />
          <span class="text-xs text-muted-foreground">~</span>
          <Input
            type="date"
            bind:value={config.dateEnd}
            class="h-7 text-xs flex-1"
            {disabled}
            oninput={onchange}
          />
        </div>
      {/if}
    {/if}
  </div>

  <!-- 文件名匹配 -->
  <div>
    <div class="flex items-center justify-between mb-1.5">
      <label class="text-xs font-medium flex items-center gap-1">
        <FileText class="w-3 h-3" />文件名
      </label>
      <input
        type="checkbox"
        bind:checked={config.nameEnabled}
        {onchange}
        {disabled}
        class="w-3.5 h-3.5"
      />
    </div>
    {#if config.nameEnabled}
      <div class="flex items-center gap-2">
        <Select.Root
          type="single"
          value={config.nameMode}
          onValueChange={(v) => {
            config.nameMode = v as any;
            onchange();
          }}
        >
          <Select.Trigger class="h-7 text-xs w-24" {disabled}>
            {{
              contains: "包含",
              starts: "开头",
              ends: "结尾",
              regex: "正则",
            }[config.nameMode]}
          </Select.Trigger>
          <Select.Content class="z-100">
            <Select.Item value="contains">包含</Select.Item>
            <Select.Item value="starts">开头是</Select.Item>
            <Select.Item value="ends">结尾是</Select.Item>
            <Select.Item value="regex">正则</Select.Item>
          </Select.Content>
        </Select.Root>
        <Input
          bind:value={config.namePattern}
          placeholder="输入关键词"
          class="h-7 text-xs flex-1"
          {disabled}
          oninput={onchange}
        />
      </div>
    {/if}
  </div>
</div>
