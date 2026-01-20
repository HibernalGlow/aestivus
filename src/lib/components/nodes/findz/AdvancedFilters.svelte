<script lang="ts">
  import { Input } from "$lib/components/ui/input";
  import { Checkbox } from "$lib/components/ui/checkbox";
  import { Label } from "$lib/components/ui/label";
  import * as Select from "$lib/components/ui/select";
  import { Image } from "@lucide/svelte";
  import { type FilterConfig } from "./FilterTypes";

  interface Props {
    config: FilterConfig;
    disabled?: boolean;
    onchange: () => void;
  }

  let { config = $bindable(), disabled = false, onchange }: Props = $props();

  function applyResolutionPreset(preset: string) {
    config.resolutionPreset = preset;
    if (preset !== "any") {
      config.widthMin = "";
      config.widthMax = "";
      config.heightMin = "";
      config.heightMax = "";
    }
    onchange();
  }
</script>

<div class="space-y-3">
  <!-- 图片元数据 -->
  <div>
    <div class="flex items-center justify-between mb-1.5">
      <label class="text-xs font-medium flex items-center gap-1">
        <Image class="w-3 h-3" />图片尺寸
      </label>
      <input
        type="checkbox"
        bind:checked={config.imageMetaEnabled}
        {onchange}
        {disabled}
        class="w-3.5 h-3.5"
      />
    </div>
    {#if config.imageMetaEnabled}
      <!-- 分辨率预设 -->
      <div class="flex flex-wrap gap-1 mb-2">
        {#each ["1080p", "4k", "8k", "social-cover"] as preset}
          <button
            class="px-2 py-0.5 rounded text-xs transition-colors
              {config.resolutionPreset === preset
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted hover:bg-muted/80'}"
            onclick={() => applyResolutionPreset(preset)}
            {disabled}
          >
            {preset === "social-cover" ? "封面" : preset.toUpperCase()}
          </button>
        {/each}
        <button
          class="px-2 py-0.5 rounded text-xs bg-muted hover:bg-muted/80"
          onclick={() => applyResolutionPreset("any")}
          {disabled}
        >
          自定义
        </button>
      </div>

      <!-- 宽度范围 -->
      <div class="space-y-1.5">
        <div class="flex items-center gap-2">
          <span class="text-xs text-muted-foreground w-10">宽度</span>
          <Input
            bind:value={config.widthMin}
            placeholder="最小"
            type="number"
            class="h-7 text-xs flex-1"
            {disabled}
            oninput={() => {
              config.resolutionPreset = "any";
              onchange();
            }}
          />
          <span class="text-xs text-muted-foreground">~</span>
          <Input
            bind:value={config.widthMax}
            placeholder="最大"
            type="number"
            class="h-7 text-xs flex-1"
            {disabled}
            oninput={() => {
              config.resolutionPreset = "any";
              onchange();
            }}
          />
        </div>

        <!-- 高度范围 -->
        <div class="flex items-center gap-2">
          <span class="text-xs text-muted-foreground w-10">高度</span>
          <Input
            bind:value={config.heightMin}
            placeholder="最小"
            type="number"
            class="h-7 text-xs flex-1"
            {disabled}
            oninput={() => {
              config.resolutionPreset = "any";
              onchange();
            }}
          />
          <span class="text-xs text-muted-foreground">~</span>
          <Input
            bind:value={config.heightMax}
            placeholder="最大"
            type="number"
            class="h-7 text-xs flex-1"
            {disabled}
            oninput={() => {
              config.resolutionPreset = "any";
              onchange();
            }}
          />
        </div>
      </div>

      <div class="text-[10px] text-muted-foreground mt-1">
        💡 需要在节点中启用"图片元数据"选项
      </div>
    {/if}
  </div>

  <!-- 容器内平均大小 -->
  <div class="space-y-1 pt-2 border-t mt-1">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-1.5 font-medium text-xs">
        <Checkbox
          id="avgSizeEnabled"
          bind:checked={config.avgSizeEnabled}
          {disabled}
          onchange={() => onchange()}
        />
        <Label for="avgSizeEnabled" class="text-[11px] cursor-pointer"
          >按容器内平均大小筛选</Label
        >
      </div>
      {#if config.avgSizeEnabled}
        <div class="flex items-center gap-1">
          <Select.Root
            type="single"
            bind:value={config.avgSizeFormat}
            disabled={!config.avgSizeEnabled || disabled}
            onValueChange={(v: any) => {
              if (v) config.avgSizeFormat = v;
              onchange();
            }}
          >
            <Select.Trigger class="h-6 w-16 text-[10px] px-1.5 capitalize">
              {config.avgSizeFormat === "images"
                ? "图片"
                : config.avgSizeFormat === "videos"
                  ? "视频"
                  : "自定义"}
            </Select.Trigger>
            <Select.Content>
              <Select.Item value="images">图片</Select.Item>
              <Select.Item value="videos">视频</Select.Item>
              <Select.Item value="custom">自定义扩展名</Select.Item>
            </Select.Content>
          </Select.Root>
        </div>
      {/if}
    </div>

    {#if config.avgSizeEnabled}
      <div class="grid grid-cols-2 gap-2 pl-6 pt-1 mb-2">
        {#if config.avgSizeFormat === "custom"}
          <div class="col-span-2">
            <Input
              bind:value={config.avgSizeCustomExts}
              placeholder="扩展名 (如 jpg, png)"
              class="h-7 text-xs"
              {disabled}
              oninput={onchange}
            />
          </div>
        {/if}
        <div class="flex items-center gap-1.5">
          <span
            class="text-[10px] text-muted-foreground whitespace-nowrap min-w-[24px]"
            >最小</span
          >
          <Input
            bind:value={config.avgSizeMin}
            placeholder="500K"
            class="h-7 text-xs flex-1"
            {disabled}
            oninput={onchange}
          />
        </div>
        <div class="flex items-center gap-1.5">
          <span
            class="text-[10px] text-muted-foreground whitespace-nowrap min-w-[24px]"
            >最大</span
          >
          <Input
            bind:value={config.avgSizeMax}
            placeholder="无"
            class="h-7 text-xs flex-1"
            {disabled}
            oninput={onchange}
          />
        </div>
        <div class="col-span-2 text-[10px] text-muted-foreground italic">
          💡 针对压缩包，计算其内部指定格式文件的平均大小。
        </div>
      </div>
    {/if}
  </div>

  <!-- 其他选项 -->
  <div class="flex items-center gap-4 text-xs pt-2 border-t mt-1">
    <!-- 位置 -->
    <div class="flex items-center gap-2">
      <span class="text-muted-foreground">位置:</span>
      <select
        bind:value={config.inArchive}
        {onchange}
        {disabled}
        class="h-6 px-1 rounded border bg-background text-xs"
      >
        <option value="any">全部</option>
        <option value="no">仅文件系统</option>
        <option value="yes">仅压缩包内</option>
      </select>
    </div>

    <!-- 类型 -->
    <div class="flex items-center gap-2">
      <span class="text-muted-foreground">类型:</span>
      <select
        bind:value={config.itemType}
        {onchange}
        {disabled}
        class="h-6 px-1 rounded border bg-background text-xs"
      >
        <option value="file">仅文件</option>
        <option value="any">全部(含目录)</option>
        <option value="dir">仅目录</option>
      </select>
    </div>
  </div>
</div>
