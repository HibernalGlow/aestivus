<script lang="ts">
  /**
   * 布局预设选择器 - 横向布局
   * 显示在标题栏下方，支持选择预设、保存当前布局、导入导出
   */
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { 
    getAllPresets, savePreset, deletePreset, exportPreset, importPreset,
    type LayoutPreset 
  } from '$lib/stores/layoutPresets';
  import type { GridItem } from './dashboard-grid.svelte';
  import { 
    Save, Trash2, Download, Upload, Check, X
  } from '@lucide/svelte';

  interface Props {
    nodeType: string;
    currentLayout: GridItem[];
    onApply: (layout: GridItem[]) => void;
  }

  let { nodeType, currentLayout, onApply }: Props = $props();

  let presets = $state<LayoutPreset[]>([]);
  let showSaveInput = $state(false);
  let newPresetName = $state('');
  let saveSuccess = $state(false);

  // 加载预设列表
  function refreshPresets() {
    presets = getAllPresets(nodeType);
  }

  // 初始化
  $effect(() => {
    refreshPresets();
  });

  // 应用预设
  function applyPreset(preset: LayoutPreset) {
    onApply(JSON.parse(JSON.stringify(preset.layout)));
  }

  // 保存当前布局为预设
  function handleSave() {
    if (!newPresetName.trim()) return;
    savePreset(newPresetName.trim(), nodeType, currentLayout);
    newPresetName = '';
    showSaveInput = false;
    saveSuccess = true;
    setTimeout(() => saveSuccess = false, 2000);
    refreshPresets();
  }

  // 删除预设
  function handleDelete(id: string) {
    deletePreset(id);
    refreshPresets();
  }

  // 导出预设
  function handleExport(id: string) {
    const json = exportPreset(id);
    if (json) {
      navigator.clipboard.writeText(json);
    }
  }

  // 导入预设
  async function handleImport() {
    try {
      const json = await navigator.clipboard.readText();
      const preset = importPreset(json);
      if (preset) {
        refreshPresets();
      }
    } catch (e) {
      console.error('导入失败:', e);
    }
  }
</script>

<div class="flex items-center gap-2 flex-wrap">
  <!-- 预设按钮列表 -->
  <span class="text-xs text-muted-foreground shrink-0">预设:</span>
  {#each presets as preset}
    <div class="flex items-center gap-0.5 group">
      <Button 
        variant="outline" 
        size="sm" 
        class="h-6 text-xs px-2"
        onclick={() => applyPreset(preset)}
      >
        {preset.name}
      </Button>
      {#if !preset.isBuiltin}
        <button 
          class="p-0.5 opacity-0 group-hover:opacity-100 hover:text-primary rounded transition-opacity"
          onclick={() => handleExport(preset.id)}
          title="复制到剪贴板"
        >
          <Download class="h-3 w-3" />
        </button>
        <button 
          class="p-0.5 opacity-0 group-hover:opacity-100 hover:text-destructive rounded transition-opacity"
          onclick={() => handleDelete(preset.id)}
          title="删除"
        >
          <Trash2 class="h-3 w-3" />
        </button>
      {/if}
    </div>
  {/each}

  <!-- 分隔线 -->
  <div class="w-px h-4 bg-border mx-1"></div>

  <!-- 保存当前布局 -->
  {#if showSaveInput}
    <div class="flex items-center gap-1">
      <Input 
        bind:value={newPresetName} 
        placeholder="预设名称..." 
        class="h-6 text-xs w-24"
        onkeydown={(e) => e.key === 'Enter' && handleSave()}
      />
      <Button size="sm" class="h-6 w-6 p-0" onclick={handleSave}>
        <Check class="h-3 w-3" />
      </Button>
      <Button variant="ghost" size="sm" class="h-6 w-6 p-0" onclick={() => { showSaveInput = false; newPresetName = ''; }}>
        <X class="h-3 w-3" />
      </Button>
    </div>
  {:else}
    <Button 
      variant="ghost" 
      size="sm" 
      class="h-6 text-xs px-2 gap-1"
      onclick={() => showSaveInput = true}
    >
      <Save class="h-3 w-3" />
      {saveSuccess ? '已保存!' : '保存'}
    </Button>
  {/if}

  <!-- 导入 -->
  <Button 
    variant="ghost" 
    size="sm" 
    class="h-6 text-xs px-2 gap-1"
    onclick={handleImport}
  >
    <Upload class="h-3 w-3" />
    导入
  </Button>
</div>
