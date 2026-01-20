<script lang="ts">
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import * as Dialog from "$lib/components/ui/dialog";
  import {
    FolderOpen,
    Save,
    Star,
    Package,
    Pencil,
    Check,
    X,
    ArrowUp,
    ArrowDown,
    Trash2,
  } from "@lucide/svelte";
  import {
    type FilterConfig,
    type Preset,
    STORAGE_KEY,
    BUILTIN_PRESETS,
  } from "./FilterTypes";

  interface Props {
    config: FilterConfig;
    onApply: (config: FilterConfig) => void;
    disabled?: boolean;
  }

  let { config, onApply, disabled = false }: Props = $props();

  let userPresets = $state<Preset[]>([]);
  let presetDialogOpen = $state(false);
  let saveDialogOpen = $state(false);
  let newPresetName = $state("");

  let editMode = $state(false);
  let editingPresetId = $state<string | null>(null);
  let editingPresetName = $state("");

  // 加载用户预设
  function loadUserPresets() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        userPresets = JSON.parse(saved);
      }
    } catch (e) {
      console.error("加载预设失败:", e);
    }
  }

  // 保存用户预设到 localStorage
  function saveUserPresets() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(userPresets));
    } catch (e) {
      console.error("保存预设失败:", e);
    }
  }

  // 应用预设
  function applyPreset(preset: Preset) {
    onApply(preset.config);
    presetDialogOpen = false;
  }

  // 保存当前配置为新预设
  function saveAsPreset() {
    if (!newPresetName.trim()) return;
    const newPreset: Preset = {
      id: `user-${Date.now()}`,
      name: newPresetName.trim(),
      config: { ...config },
    };
    userPresets = [...userPresets, newPreset];
    saveUserPresets();
    newPresetName = "";
    saveDialogOpen = false;
  }

  // 删除用户预设
  function deletePreset(presetId: string) {
    userPresets = userPresets.filter((p) => p.id !== presetId);
    saveUserPresets();
  }

  // 开始重命名预设
  function startRenamePreset(preset: Preset) {
    editingPresetId = preset.id;
    editingPresetName = preset.name;
  }

  // 确认重命名
  function confirmRename() {
    if (!editingPresetId || !editingPresetName.trim()) return;
    userPresets = userPresets.map((p) =>
      p.id === editingPresetId ? { ...p, name: editingPresetName.trim() } : p,
    );
    saveUserPresets();
    editingPresetId = null;
    editingPresetName = "";
  }

  // 取消重命名
  function cancelRename() {
    editingPresetId = null;
    editingPresetName = "";
  }

  // 移动预设位置
  function movePreset(presetId: string, direction: "up" | "down") {
    const index = userPresets.findIndex((p) => p.id === presetId);
    if (index === -1) return;

    const newIndex = direction === "up" ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= userPresets.length) return;

    const newPresets = [...userPresets];
    [newPresets[index], newPresets[newIndex]] = [
      newPresets[newIndex],
      newPresets[index],
    ];
    userPresets = newPresets;
    saveUserPresets();
  }

  // 切换编辑模式
  function toggleEditMode() {
    editMode = !editMode;
    if (!editMode) {
      editingPresetId = null;
      editingPresetName = "";
    }
  }

  // 初始化加载预设
  $effect(() => {
    loadUserPresets();
  });
</script>

<div class="flex items-center gap-1">
  <!-- 预设按钮 -->
  <Dialog.Root bind:open={presetDialogOpen}>
    <Dialog.Trigger>
      <Button variant="outline" size="sm" class="h-6 text-xs" {disabled}>
        <FolderOpen class="w-3 h-3 mr-1" />预设
      </Button>
    </Dialog.Trigger>
    <Dialog.Content class="max-w-md">
      <Dialog.Header>
        <div class="flex items-center justify-between">
          <Dialog.Title>选择预设</Dialog.Title>
          {#if userPresets.length > 0}
            <Button
              variant="ghost"
              size="sm"
              class="h-7 text-xs"
              onclick={toggleEditMode}
            >
              {#if editMode}
                <Check class="w-3 h-3 mr-1" />完成
              {:else}
                <Pencil class="w-3 h-3 mr-1" />编辑
              {/if}
            </Button>
          {/if}
        </div>
        <Dialog.Description>选择一个预设快速配置过滤器</Dialog.Description>
      </Dialog.Header>
      <div class="space-y-3 max-h-80 overflow-y-auto">
        <!-- 内置预设 -->
        <div>
          <div
            class="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1"
          >
            < Star class="w-3 h-3" />内置预设
          </div>
          <div class="space-y-1">
            {#each BUILTIN_PRESETS as preset}
              <button
                class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors text-left"
                onclick={() => applyPreset(preset)}
              >
                <span class="text-sm">{preset.name}</span>
                <Package class="w-4 h-4 text-muted-foreground" />
              </button>
            {/each}
          </div>
        </div>

        <!-- 用户预设 -->
        {#if userPresets.length > 0}
          <div>
            <div
              class="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1"
            >
              <Save class="w-3 h-3" />我的预设
            </div>
            <div class="space-y-1">
              {#each userPresets as preset, index}
                <div class="flex items-center gap-1">
                  {#if editMode}
                    <!-- 编辑模式 -->
                    <div class="flex items-center gap-1 shrink-0">
                      <Button
                        variant="ghost"
                        size="icon"
                        class="h-7 w-7"
                        onclick={() => movePreset(preset.id, "up")}
                        disabled={index === 0}
                      >
                        <ArrowUp class="w-3 h-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        class="h-7 w-7"
                        onclick={() => movePreset(preset.id, "down")}
                        disabled={index === userPresets.length - 1}
                      >
                        <ArrowDown class="w-3 h-3" />
                      </Button>
                    </div>

                    {#if editingPresetId === preset.id}
                      <!-- 重命名输入框 -->
                      <Input
                        bind:value={editingPresetName}
                        class="h-8 text-sm flex-1"
                        onkeydown={(e) => {
                          if (e.key === "Enter") confirmRename();
                          if (e.key === "Escape") cancelRename();
                        }}
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        class="h-7 w-7"
                        onclick={confirmRename}
                      >
                        <Check class="w-3 h-3 text-green-500" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        class="h-7 w-7"
                        onclick={cancelRename}
                      >
                        <X class="w-3 h-3" />
                      </Button>
                    {:else}
                      <!-- 预设名称（可点击重命名） -->
                      <button
                        class="flex-1 p-2 rounded-lg hover:bg-muted/50 transition-colors text-left text-sm"
                        onclick={() => startRenamePreset(preset)}
                      >
                        {preset.name}
                      </button>
                      <Button
                        variant="ghost"
                        size="icon"
                        class="h-7 w-7"
                        onclick={() => startRenamePreset(preset)}
                      >
                        <Pencil class="w-3 h-3 text-muted-foreground" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        class="h-7 w-7"
                        onclick={() => deletePreset(preset.id)}
                      >
                        <Trash2 class="w-3 h-3 text-destructive" />
                      </Button>
                    {/if}
                  {:else}
                    <!-- 普通模式 -->
                    <button
                      class="flex-1 flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors text-left"
                      onclick={() => applyPreset(preset)}
                    >
                      <span class="text-sm">{preset.name}</span>
                    </button>
                  {/if}
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </Dialog.Content>
  </Dialog.Root>

  <!-- 保存预设按钮 -->
  <Dialog.Root bind:open={saveDialogOpen}>
    <Dialog.Trigger>
      <Button variant="ghost" size="sm" class="h-6 text-xs" {disabled}>
        <Save class="w-3 h-3" />
      </Button>
    </Dialog.Trigger>
    <Dialog.Content class="max-w-sm">
      <Dialog.Header>
        <Dialog.Title>保存预设</Dialog.Title>
        <Dialog.Description>将当前配置保存为预设</Dialog.Description>
      </Dialog.Header>
      <div class="space-y-3">
        <Input
          bind:value={newPresetName}
          placeholder="预设名称"
          onkeydown={(e) => e.key === "Enter" && saveAsPreset()}
        />
        <div class="flex justify-end gap-2">
          <Button variant="outline" onclick={() => (saveDialogOpen = false)}
            >取消</Button
          >
          <Button onclick={saveAsPreset} disabled={!newPresetName.trim()}
            >保存</Button
          >
        </div>
      </div>
    </Dialog.Content>
  </Dialog.Root>
</div>
