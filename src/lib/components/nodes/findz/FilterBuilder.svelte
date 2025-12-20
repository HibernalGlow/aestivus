<script lang="ts">
  /**
   * FilterBuilder - 直观的文件过滤器构建器
   * 不是 SQL 可视化，而是重新设计的易用交互
   * 支持预设保存/加载系统
   */
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Select from '$lib/components/ui/select';
  import * as Dialog from '$lib/components/ui/dialog';
  import { 
    Plus, X, Code, Sparkles, FileText, Calendar, HardDrive,
    Archive, Folder, Image, Video, Music, FileCode, File,
    Save, FolderOpen, Trash2, Star, Package, Pencil, Check,
    GripVertical, ArrowUp, ArrowDown
  } from '@lucide/svelte';

  // 过滤器配置类型
  interface FilterConfig {
    // 文件类型快捷选择
    fileTypes: string[];
    // 大小范围
    sizeEnabled: boolean;
    sizeMin: string;
    sizeMax: string;
    // 日期范围
    dateEnabled: boolean;
    datePreset: string; // today, week, month, year, custom
    dateStart: string;
    dateEnd: string;
    // 名称匹配
    nameEnabled: boolean;
    namePattern: string;
    nameMode: 'contains' | 'starts' | 'ends' | 'regex';
    // 位置
    locationEnabled: boolean;
    inArchive: 'any' | 'yes' | 'no';
    // 类型
    itemType: 'any' | 'file' | 'dir';
    // 自定义扩展名
    customExts: string[];
  }

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
  }

  let { 
    value,
    onchange,
    disabled = false,
    showAdvanced = true,
    advancedMode = false,
    sqlValue = '1',
    onAdvancedChange
  }: Props = $props();

  // 默认配置
  const defaultConfig: FilterConfig = {
    fileTypes: [],
    sizeEnabled: false,
    sizeMin: '',
    sizeMax: '',
    dateEnabled: false,
    datePreset: 'any',
    dateStart: '',
    dateEnd: '',
    nameEnabled: false,
    namePattern: '',
    nameMode: 'contains',
    locationEnabled: false,
    inArchive: 'any',
    itemType: 'any',
    customExts: [],
  };

  let config = $state<FilterConfig>(value ?? { ...defaultConfig });
  let customExtInput = $state('');
  let internalSql = $state(sqlValue);

  // 预设系统
  interface Preset {
    id: string;
    name: string;
    config: FilterConfig;
    isBuiltin?: boolean;
  }

  // 内置预设
  const BUILTIN_PRESETS: Preset[] = [
    {
      id: 'jxl-in-archive',
      name: '压缩包内JXL',
      isBuiltin: true,
      config: {
        ...defaultConfig,
        customExts: ['jxl'],
        locationEnabled: true,
        inArchive: 'yes',
      }
    },
    {
      id: 'large-files',
      name: '大文件 (>100MB)',
      isBuiltin: true,
      config: {
        ...defaultConfig,
        sizeEnabled: true,
        sizeMin: '100M',
        sizeMax: '',
      }
    },
    {
      id: 'recent-images',
      name: '本周图片',
      isBuiltin: true,
      config: {
        ...defaultConfig,
        fileTypes: ['images'],
        dateEnabled: true,
        datePreset: 'week',
      }
    },
    {
      id: 'nested-archives',
      name: '嵌套压缩包',
      isBuiltin: true,
      config: {
        ...defaultConfig,
        fileTypes: ['archives'],
        locationEnabled: true,
        inArchive: 'yes',
      }
    },
  ];

  const STORAGE_KEY = 'findz-filter-presets';
  let userPresets = $state<Preset[]>([]);
  let presetDialogOpen = $state(false);
  let saveDialogOpen = $state(false);
  let newPresetName = $state('');
  
  // 编辑模式状态
  let editMode = $state(false);
  let editingPresetId = $state<string | null>(null);
  let editingPresetName = $state('');

  // 加载用户预设
  function loadUserPresets() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        userPresets = JSON.parse(saved);
      }
    } catch (e) {
      console.error('加载预设失败:', e);
    }
  }

  // 保存用户预设到 localStorage
  function saveUserPresets() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(userPresets));
    } catch (e) {
      console.error('保存预设失败:', e);
    }
  }

  // 应用预设
  function applyPreset(preset: Preset) {
    config = { ...preset.config };
    emitChange();
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
    newPresetName = '';
    saveDialogOpen = false;
  }

  // 删除用户预设
  function deletePreset(presetId: string) {
    userPresets = userPresets.filter(p => p.id !== presetId);
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
    userPresets = userPresets.map(p => 
      p.id === editingPresetId ? { ...p, name: editingPresetName.trim() } : p
    );
    saveUserPresets();
    editingPresetId = null;
    editingPresetName = '';
  }

  // 取消重命名
  function cancelRename() {
    editingPresetId = null;
    editingPresetName = '';
  }

  // 移动预设位置
  function movePreset(presetId: string, direction: 'up' | 'down') {
    const index = userPresets.findIndex(p => p.id === presetId);
    if (index === -1) return;
    
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= userPresets.length) return;
    
    const newPresets = [...userPresets];
    [newPresets[index], newPresets[newIndex]] = [newPresets[newIndex], newPresets[index]];
    userPresets = newPresets;
    saveUserPresets();
  }

  // 切换编辑模式
  function toggleEditMode() {
    editMode = !editMode;
    if (!editMode) {
      editingPresetId = null;
      editingPresetName = '';
    }
  }

  // 初始化加载预设
  $effect(() => {
    loadUserPresets();
  });

  // 文件类型预设
  const FILE_TYPE_PRESETS = [
    { id: 'images', label: '图片', icon: Image, exts: ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'ico', 'jxl', 'avif'] },
    { id: 'videos', label: '视频', icon: Video, exts: ['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v'] },
    { id: 'audio', label: '音频', icon: Music, exts: ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma'] },
    { id: 'docs', label: '文档', icon: FileText, exts: ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'rtf'] },
    { id: 'archives', label: '压缩包', icon: Archive, exts: ['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz'] },
    { id: 'code', label: '代码', icon: FileCode, exts: ['py', 'js', 'ts', 'java', 'c', 'cpp', 'h', 'go', 'rs', 'rb', 'php', 'html', 'css', 'json', 'xml', 'yaml', 'yml'] },
    { id: 'jxl', label: 'JXL', icon: Image, exts: ['jxl'] },
  ];

  // 日期预设
  const DATE_PRESETS = [
    { value: 'any', label: '不限' },
    { value: 'today', label: '今天' },
    { value: 'week', label: '本周' },
    { value: 'month', label: '本月' },
    { value: 'year', label: '今年' },
    { value: 'custom', label: '自定义' },
  ];

  // 大小预设
  const SIZE_PRESETS = [
    { label: '微小 (<10KB)', min: '', max: '10K' },
    { label: '小 (<1MB)', min: '', max: '1M' },
    { label: '中 (1-100MB)', min: '1M', max: '100M' },
    { label: '大 (100MB-1GB)', min: '100M', max: '1G' },
    { label: '超大 (>1GB)', min: '1G', max: '' },
  ];

  // 切换文件类型
  function toggleFileType(typeId: string) {
    if (config.fileTypes.includes(typeId)) {
      config.fileTypes = config.fileTypes.filter(t => t !== typeId);
    } else {
      config.fileTypes = [...config.fileTypes, typeId];
    }
    emitChange();
  }

  // 添加自定义扩展名
  function addCustomExt() {
    const ext = customExtInput.trim().replace(/^\./, '').toLowerCase();
    if (ext && !config.customExts.includes(ext)) {
      config.customExts = [...config.customExts, ext];
      customExtInput = '';
      emitChange();
    }
  }

  // 移除自定义扩展名
  function removeCustomExt(ext: string) {
    config.customExts = config.customExts.filter(e => e !== ext);
    emitChange();
  }

  // 应用大小预设
  function applySizePreset(preset: typeof SIZE_PRESETS[0]) {
    config.sizeEnabled = true;
    config.sizeMin = preset.min;
    config.sizeMax = preset.max;
    emitChange();
  }

  // 生成 SQL
  function generateSql(): string {
    const conditions: string[] = [];

    // 文件类型
    const allExts: string[] = [];
    for (const typeId of config.fileTypes) {
      const preset = FILE_TYPE_PRESETS.find(p => p.id === typeId);
      if (preset) allExts.push(...preset.exts);
    }
    allExts.push(...config.customExts);
    
    if (allExts.length > 0) {
      const extList = allExts.map(e => `"${e}"`).join(', ');
      conditions.push(`ext IN (${extList})`);
    }

    // 大小
    if (config.sizeEnabled) {
      if (config.sizeMin && config.sizeMax) {
        conditions.push(`size BETWEEN ${config.sizeMin} AND ${config.sizeMax}`);
      } else if (config.sizeMin) {
        conditions.push(`size >= ${config.sizeMin}`);
      } else if (config.sizeMax) {
        conditions.push(`size <= ${config.sizeMax}`);
      }
    }

    // 日期
    if (config.dateEnabled && config.datePreset !== 'any') {
      if (config.datePreset === 'today') {
        conditions.push('date = today');
      } else if (config.datePreset === 'week') {
        conditions.push('date >= mo');
      } else if (config.datePreset === 'month') {
        // 获取本月第一天
        const now = new Date();
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        conditions.push(`date >= "${firstDay.toISOString().split('T')[0]}"`);
      } else if (config.datePreset === 'year') {
        const year = new Date().getFullYear();
        conditions.push(`date >= "${year}-01-01"`);
      } else if (config.datePreset === 'custom') {
        if (config.dateStart && config.dateEnd) {
          conditions.push(`date BETWEEN "${config.dateStart}" AND "${config.dateEnd}"`);
        } else if (config.dateStart) {
          conditions.push(`date >= "${config.dateStart}"`);
        } else if (config.dateEnd) {
          conditions.push(`date <= "${config.dateEnd}"`);
        }
      }
    }

    // 名称匹配
    if (config.nameEnabled && config.namePattern) {
      const pattern = config.namePattern;
      switch (config.nameMode) {
        case 'contains':
          conditions.push(`name ILIKE "%${pattern}%"`);
          break;
        case 'starts':
          conditions.push(`name ILIKE "${pattern}%"`);
          break;
        case 'ends':
          conditions.push(`name ILIKE "%${pattern}"`);
          break;
        case 'regex':
          conditions.push(`name RLIKE "${pattern}"`);
          break;
      }
    }

    // 位置（是否在压缩包内）
    if (config.locationEnabled && config.inArchive !== 'any') {
      if (config.inArchive === 'yes') {
        conditions.push('archive <> ""');
      } else {
        conditions.push('archive = ""');
      }
    }

    // 类型
    if (config.itemType !== 'any') {
      conditions.push(`type = "${config.itemType}"`);
    }

    return conditions.length > 0 ? conditions.join(' AND ') : '1';
  }

  // 生成 JSON 配置
  function generateJsonConfig(): object {
    const conditions: object[] = [];

    // 文件类型
    const allExts: string[] = [];
    for (const typeId of config.fileTypes) {
      const preset = FILE_TYPE_PRESETS.find(p => p.id === typeId);
      if (preset) allExts.push(...preset.exts);
    }
    allExts.push(...config.customExts);
    
    if (allExts.length > 0) {
      conditions.push({ field: 'ext', op: 'in', value: allExts });
    }

    // 大小
    if (config.sizeEnabled) {
      if (config.sizeMin && config.sizeMax) {
        conditions.push({ field: 'size', op: 'between', value: [config.sizeMin, config.sizeMax] });
      } else if (config.sizeMin) {
        conditions.push({ field: 'size', op: '>=', value: config.sizeMin });
      } else if (config.sizeMax) {
        conditions.push({ field: 'size', op: '<=', value: config.sizeMax });
      }
    }

    // 日期
    if (config.dateEnabled && config.datePreset !== 'any') {
      if (config.datePreset === 'today') {
        conditions.push({ field: 'date', op: '=', value: 'today' });
      } else if (config.datePreset === 'week') {
        conditions.push({ field: 'date', op: '>=', value: 'mo' });
      } else if (config.datePreset === 'custom') {
        if (config.dateStart && config.dateEnd) {
          conditions.push({ field: 'date', op: 'between', value: [config.dateStart, config.dateEnd] });
        } else if (config.dateStart) {
          conditions.push({ field: 'date', op: '>=', value: config.dateStart });
        } else if (config.dateEnd) {
          conditions.push({ field: 'date', op: '<=', value: config.dateEnd });
        }
      }
    }

    // 名称
    if (config.nameEnabled && config.namePattern) {
      const opMap = { contains: 'ilike', starts: 'ilike', ends: 'ilike', regex: 'rlike' };
      const patternMap = {
        contains: `%${config.namePattern}%`,
        starts: `${config.namePattern}%`,
        ends: `%${config.namePattern}`,
        regex: config.namePattern
      };
      conditions.push({ field: 'name', op: opMap[config.nameMode], value: patternMap[config.nameMode] });
    }

    // 位置
    if (config.locationEnabled && config.inArchive !== 'any') {
      conditions.push({ field: 'archive', op: config.inArchive === 'yes' ? '!=' : '=', value: '' });
    }

    // 类型
    if (config.itemType !== 'any') {
      conditions.push({ field: 'type', op: '=', value: config.itemType });
    }

    return { op: 'and', conditions };
  }

  // 触发变化
  function emitChange() {
    const sql = generateSql();
    internalSql = sql;
    onchange?.(config, sql);
  }

  // 重置
  function reset() {
    config = { ...defaultConfig };
    emitChange();
  }

  // 切换高级模式
  function toggleAdvanced() {
    onAdvancedChange?.(!advancedMode);
  }
</script>

<div class="filter-builder space-y-3">
  <!-- 模式切换和预设按钮 -->
  {#if showAdvanced}
    <div class="flex items-center justify-between gap-2">
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
                  <Button variant="ghost" size="sm" class="h-7 text-xs" onclick={toggleEditMode}>
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
                <div class="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                  <Star class="w-3 h-3" />内置预设
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
                  <div class="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
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
                              onclick={() => movePreset(preset.id, 'up')}
                              disabled={index === 0}
                            >
                              <ArrowUp class="w-3 h-3" />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              class="h-7 w-7" 
                              onclick={() => movePreset(preset.id, 'down')}
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
                                if (e.key === 'Enter') confirmRename();
                                if (e.key === 'Escape') cancelRename();
                              }}
                            />
                            <Button variant="ghost" size="icon" class="h-7 w-7" onclick={confirmRename}>
                              <Check class="w-3 h-3 text-green-500" />
                            </Button>
                            <Button variant="ghost" size="icon" class="h-7 w-7" onclick={cancelRename}>
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
                            <Button variant="ghost" size="icon" class="h-7 w-7" onclick={() => startRenamePreset(preset)}>
                              <Pencil class="w-3 h-3 text-muted-foreground" />
                            </Button>
                            <Button variant="ghost" size="icon" class="h-7 w-7" onclick={() => deletePreset(preset.id)}>
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
                onkeydown={(e) => e.key === 'Enter' && saveAsPreset()}
              />
              <div class="flex justify-end gap-2">
                <Button variant="outline" onclick={() => saveDialogOpen = false}>取消</Button>
                <Button onclick={saveAsPreset} disabled={!newPresetName.trim()}>保存</Button>
              </div>
            </div>
          </Dialog.Content>
        </Dialog.Root>
      </div>

      <!-- 模式切换 -->
      <Button variant="ghost" size="sm" class="h-6 text-xs" onclick={toggleAdvanced}>
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
      placeholder='例: size > 10M and ext in ("zip", "rar")'
      class="font-mono text-xs"
      {disabled}
      oninput={() => onchange?.(config, internalSql)}
    />
  {:else}
    <!-- 可视化模式 -->
    
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
              {isActive ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/80'}"
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
          onkeydown={(e) => e.key === 'Enter' && addCustomExt()}
        />
        <Button variant="outline" size="sm" class="h-7" onclick={addCustomExt} {disabled}>
          <Plus class="w-3 h-3" />
        </Button>
      </div>
      {#if config.customExts.length > 0}
        <div class="flex flex-wrap gap-1 mt-1">
          {#each config.customExts as ext}
            <span class="inline-flex items-center gap-1 px-1.5 py-0.5 bg-blue-500/20 text-blue-600 rounded text-xs">
              .{ext}
              <button onclick={() => removeCustomExt(ext)} class="hover:text-red-500">
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
        <input type="checkbox" bind:checked={config.sizeEnabled} onchange={emitChange} {disabled} class="w-3.5 h-3.5" />
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
            oninput={emitChange}
          />
          <span class="text-xs text-muted-foreground">~</span>
          <Input 
            bind:value={config.sizeMax}
            placeholder="最大 (如 1G)"
            class="h-7 text-xs flex-1"
            {disabled}
            oninput={emitChange}
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
        <input type="checkbox" bind:checked={config.dateEnabled} onchange={emitChange} {disabled} class="w-3.5 h-3.5" />
      </div>
      {#if config.dateEnabled}
        <div class="flex flex-wrap gap-1">
          {#each DATE_PRESETS as preset}
            <button
              class="px-2 py-0.5 rounded text-xs transition-colors
                {config.datePreset === preset.value ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/80'}"
              onclick={() => { config.datePreset = preset.value; emitChange(); }}
              {disabled}
            >
              {preset.label}
            </button>
          {/each}
        </div>
        {#if config.datePreset === 'custom'}
          <div class="flex items-center gap-2 mt-2">
            <Input 
              type="date"
              bind:value={config.dateStart}
              class="h-7 text-xs flex-1"
              {disabled}
              oninput={emitChange}
            />
            <span class="text-xs text-muted-foreground">~</span>
            <Input 
              type="date"
              bind:value={config.dateEnd}
              class="h-7 text-xs flex-1"
              {disabled}
              oninput={emitChange}
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
        <input type="checkbox" bind:checked={config.nameEnabled} onchange={emitChange} {disabled} class="w-3.5 h-3.5" />
      </div>
      {#if config.nameEnabled}
        <div class="flex items-center gap-2">
          <Select.Root type="single" value={config.nameMode} onValueChange={(v) => { config.nameMode = v as any; emitChange(); }}>
            <Select.Trigger class="h-7 text-xs w-24" {disabled}>
              {{ contains: '包含', starts: '开头', ends: '结尾', regex: '正则' }[config.nameMode]}
            </Select.Trigger>
            <Select.Content>
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
            oninput={emitChange}
          />
        </div>
      {/if}
    </div>

    <!-- 其他选项 -->
    <div class="flex items-center gap-4 text-xs">
      <!-- 位置 -->
      <div class="flex items-center gap-2">
        <span class="text-muted-foreground">位置:</span>
        <select 
          bind:value={config.inArchive}
          onchange={emitChange}
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
          onchange={emitChange}
          {disabled}
          class="h-6 px-1 rounded border bg-background text-xs"
        >
          <option value="any">全部</option>
          <option value="file">仅文件</option>
          <option value="dir">仅目录</option>
        </select>
      </div>
    </div>

    <!-- 生成的条件预览 -->
    <div class="text-[10px] text-muted-foreground font-mono bg-muted/30 rounded px-2 py-1 truncate" title={internalSql}>
      {internalSql === '1' ? '匹配所有文件' : internalSql}
    </div>
  {/if}
</div>
