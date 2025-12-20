<script lang="ts">
  /**
   * AnalysisPanel - 文件分组分析面板
   * 支持按压缩包/扩展名/目录分组，提供多维度过滤和排序
   * 
   * 使用 Container Query 统一 UI 结构
   */
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Popover from '$lib/components/ui/popover';
  import {
    Package, File, Folder, ChartNoAxesColumn, ArrowUp, ArrowDown,
    Copy, Check, SlidersHorizontal
  } from '@lucide/svelte';
  import type { FileData, GroupAnalysis, AnalysisFilter } from './types';
  import { formatSize, parseSize, parseNumber } from './hooks';

  interface Props {
    files: FileData[];
  }

  let { files }: Props = $props();

  // 分组和排序状态
  type GroupByField = 'archive' | 'ext' | 'dir';
  type SortField = 'name' | 'count' | 'totalSize' | 'avgSize';
  type SortOrder = 'asc' | 'desc';

  let groupBy = $state<GroupByField>('archive');
  let sortField = $state<SortField>('avgSize');
  let sortOrder = $state<SortOrder>('desc');

  // 过滤状态
  let filter = $state<AnalysisFilter>({
    countMin: 1, countMax: null,
    avgSizeMin: null, avgSizeMax: null,
    totalSizeMin: null, totalSizeMax: null,
  });

  let filterInputs = $state({
    countMin: '1', countMax: '',
    avgSizeMin: '', avgSizeMax: '',
    totalSizeMin: '', totalSizeMax: '',
  });

  // 复制状态
  let copiedGroupKey = $state<string | null>(null);
  let copiedAll = $state(false);

  /** 分组配置 */
  const groupByOptions: { field: GroupByField; label: string; icon: typeof Package }[] = [
    { field: 'archive', label: '压缩包', icon: Package },
    { field: 'ext', label: '扩展名', icon: File },
    { field: 'dir', label: '目录', icon: Folder },
  ];

  const sortOptions: { field: SortField; label: string }[] = [
    { field: 'name', label: '名称' },
    { field: 'count', label: '数量' },
    { field: 'totalSize', label: '总计' },
    { field: 'avgSize', label: '平均' },
  ];

  function updateFilter() {
    filter = {
      countMin: parseNumber(filterInputs.countMin),
      countMax: parseNumber(filterInputs.countMax),
      avgSizeMin: parseSize(filterInputs.avgSizeMin),
      avgSizeMax: parseSize(filterInputs.avgSizeMax),
      totalSizeMin: parseSize(filterInputs.totalSizeMin),
      totalSizeMax: parseSize(filterInputs.totalSizeMax),
    };
  }

  function resetFilter() {
    filterInputs = { countMin: '1', countMax: '', avgSizeMin: '', avgSizeMax: '', totalSizeMin: '', totalSizeMax: '' };
    updateFilter();
  }

  let hasActiveFilter = $derived(
    (filter.countMin !== null && filter.countMin > 1) ||
    filter.countMax !== null || filter.avgSizeMin !== null ||
    filter.avgSizeMax !== null || filter.totalSizeMin !== null || filter.totalSizeMax !== null
  );

  /** 获取文件的分组键 */
  function getGroupKey(file: FileData): string | null {
    switch (groupBy) {
      case 'archive': return file.archive || file.container || null;
      case 'ext': return file.ext || '(无扩展名)';
      case 'dir': {
        const fullPath = file.container ? `${file.container}//${file.path}` : file.path;
        const parts = fullPath.split(/[/\\]|\/\//);
        return parts.length > 1 ? parts.slice(0, -1).join('/') : '(根目录)';
      }
    }
  }

  function getGroupName(key: string): string {
    switch (groupBy) {
      case 'archive': return key.split(/[/\\]/).pop() || key;
      case 'ext': return key.startsWith('(') ? key : `.${key}`;
      case 'dir': return key.split(/[/\\]|\/\//).pop() || key;
    }
  }

  /** 分组分析 */
  function analyzeByGroup(): GroupAnalysis[] {
    const groupMap = new Map<string, { files: FileData[], totalSize: number }>();
    for (const file of files) {
      const key = getGroupKey(file);
      if (key === null) continue;
      if (!groupMap.has(key)) groupMap.set(key, { files: [], totalSize: 0 });
      const data = groupMap.get(key)!;
      data.files.push(file);
      data.totalSize += file.size;
    }

    const results: GroupAnalysis[] = [];
    for (const [key, data] of groupMap) {
      const avgSize = data.files.length > 0 ? data.totalSize / data.files.length : 0;
      const subStats: Record<string, number> = {};
      if (groupBy === 'archive' || groupBy === 'dir') {
        for (const f of data.files) { const ext = f.ext || '无'; subStats[ext] = (subStats[ext] || 0) + 1; }
      } else {
        for (const f of data.files) {
          const container = f.archive || f.container || '文件系统';
          const name = container === '文件系统' ? container : container.split(/[/\\]/).pop() || container;
          subStats[name] = (subStats[name] || 0) + 1;
        }
      }
      results.push({ key, name: getGroupName(key), fileCount: data.files.length, totalSize: data.totalSize, avgSize, avgSizeFormatted: formatSize(avgSize), totalSizeFormatted: formatSize(data.totalSize), subStats });
    }

    return results
      .filter(a => {
        if (filter.countMin !== null && a.fileCount < filter.countMin) return false;
        if (filter.countMax !== null && a.fileCount > filter.countMax) return false;
        if (filter.avgSizeMin !== null && a.avgSize < filter.avgSizeMin) return false;
        if (filter.avgSizeMax !== null && a.avgSize > filter.avgSizeMax) return false;
        if (filter.totalSizeMin !== null && a.totalSize < filter.totalSizeMin) return false;
        if (filter.totalSizeMax !== null && a.totalSize > filter.totalSizeMax) return false;
        return true;
      })
      .sort((a, b) => {
        let cmp = 0;
        switch (sortField) {
          case 'name': cmp = a.name.localeCompare(b.name); break;
          case 'count': cmp = a.fileCount - b.fileCount; break;
          case 'totalSize': cmp = a.totalSize - b.totalSize; break;
          case 'avgSize': cmp = a.avgSize - b.avgSize; break;
        }
        return sortOrder === 'desc' ? -cmp : cmp;
      });
  }

  function toggleSort(field: SortField) {
    if (sortField === field) { sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'; }
    else { sortField = field; sortOrder = 'desc'; }
  }

  function getFilesInGroup(groupKey: string): FileData[] {
    return files.filter(f => getGroupKey(f) === groupKey);
  }

  async function copyGroupPaths(groupKey: string) {
    try {
      const groupFiles = getFilesInGroup(groupKey);
      const paths = groupFiles.map(f => f.container ? `${f.container}//${f.path}` : f.path).join('\n');
      await navigator.clipboard.writeText(paths);
      copiedGroupKey = groupKey;
      setTimeout(() => { copiedGroupKey = null; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  async function copyAllFilteredPaths() {
    try {
      const allFiles: FileData[] = [];
      for (const group of analysisData) { allFiles.push(...getFilesInGroup(group.key)); }
      const paths = allFiles.map(f => f.container ? `${f.container}//${f.path}` : f.path).join('\n');
      await navigator.clipboard.writeText(paths);
      copiedAll = true;
      setTimeout(() => { copiedAll = false; }, 2000);
    } catch (e) { console.error('复制失败:', e); }
  }

  let analysisData = $derived(analyzeByGroup());
  let currentGroupOption = $derived(groupByOptions.find(o => o.field === groupBy)!);
  let filteredFileCount = $derived(analysisData.reduce((sum, g) => sum + g.fileCount, 0));
</script>

<div class="h-full flex flex-col overflow-hidden">
  <!-- 标题栏：分组选择 + 过滤器 -->
  <div class="flex items-center justify-between cq-padding border-b bg-muted/30 shrink-0">
    <div class="flex items-center cq-gap-sm">
      {#each groupByOptions as opt}
        <button
          class="cq-padding-sm cq-rounded cq-text-sm flex items-center cq-gap-sm transition-colors {groupBy === opt.field ? 'bg-primary/20 text-primary' : 'hover:bg-muted text-muted-foreground'}"
          onclick={() => groupBy = opt.field}
          title={opt.label}
        >
          <opt.icon class="cq-icon-sm" />
          <span class="cq-wide-only-inline">{opt.label}</span>
        </button>
      {/each}
    </div>

    <!-- 过滤器弹出框 -->
    <Popover.Root>
      <Popover.Trigger>
        <button class="cq-padding-sm cq-rounded flex items-center cq-gap-sm hover:bg-muted transition-colors {hasActiveFilter ? 'text-primary' : 'text-muted-foreground'}">
          <SlidersHorizontal class="cq-icon-sm" />
          <span class="cq-wide-only-inline cq-text-sm">过滤</span>
          {#if hasActiveFilter}<span class="w-1.5 h-1.5 rounded-full bg-primary"></span>{/if}
        </button>
      </Popover.Trigger>
      <Popover.Content class="w-56 p-2 z-[200]" align="end">
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium">过滤条件</span>
            <Button variant="ghost" size="sm" class="h-5 px-1 text-[10px]" onclick={resetFilter}>重置</Button>
          </div>
          <div class="space-y-1">
            <span class="text-[10px] text-muted-foreground">文件数量</span>
            <div class="flex items-center gap-1">
              <Input type="number" placeholder="最小" bind:value={filterInputs.countMin} onchange={updateFilter} class="h-6 text-[10px]" />
              <span class="text-muted-foreground">-</span>
              <Input type="number" placeholder="最大" bind:value={filterInputs.countMax} onchange={updateFilter} class="h-6 text-[10px]" />
            </div>
          </div>
          <div class="space-y-1">
            <span class="text-[10px] text-muted-foreground">平均大小</span>
            <div class="flex items-center gap-1">
              <Input placeholder="100KB" bind:value={filterInputs.avgSizeMin} onchange={updateFilter} class="h-6 text-[10px]" />
              <span class="text-muted-foreground">-</span>
              <Input placeholder="5MB" bind:value={filterInputs.avgSizeMax} onchange={updateFilter} class="h-6 text-[10px]" />
            </div>
          </div>
          <div class="space-y-1">
            <span class="text-[10px] text-muted-foreground">总大小</span>
            <div class="flex items-center gap-1">
              <Input placeholder="1MB" bind:value={filterInputs.totalSizeMin} onchange={updateFilter} class="h-6 text-[10px]" />
              <span class="text-muted-foreground">-</span>
              <Input placeholder="1GB" bind:value={filterInputs.totalSizeMax} onchange={updateFilter} class="h-6 text-[10px]" />
            </div>
          </div>
          <div class="pt-1 border-t flex flex-wrap gap-1">
            <Button variant="outline" size="sm" class="h-5 px-1 text-[10px]" onclick={() => { filterInputs.avgSizeMax = '100KB'; updateFilter(); }}>&lt;100KB</Button>
            <Button variant="outline" size="sm" class="h-5 px-1 text-[10px]" onclick={() => { filterInputs.avgSizeMin = '1MB'; updateFilter(); }}>&gt;1MB</Button>
            <Button variant="outline" size="sm" class="h-5 px-1 text-[10px]" onclick={() => { filterInputs.countMin = '10'; updateFilter(); }}>≥10</Button>
          </div>
        </div>
      </Popover.Content>
    </Popover.Root>
  </div>

  <!-- 排序按钮 -->
  <div class="flex items-center cq-gap-sm cq-padding border-b shrink-0">
    <span class="cq-wide-only-inline cq-text-sm text-muted-foreground">排序:</span>
    {#each sortOptions as item}
      <button
        class="cq-padding-sm cq-rounded cq-text-sm flex items-center cq-gap-sm transition-colors {sortField === item.field ? 'bg-primary/20 text-primary' : 'hover:bg-muted'}"
        onclick={() => toggleSort(item.field)}
        title={item.label}
      >
        <span>{item.label}</span>
        {#if sortField === item.field}
          {#if sortOrder === 'desc'}<ArrowDown class="cq-icon-sm" />{:else}<ArrowUp class="cq-icon-sm" />{/if}
        {/if}
      </button>
    {/each}
  </div>

  <!-- 分析列表：统一 UI 结构 -->
  <div class="flex-1 overflow-y-auto cq-padding">
    {#if analysisData.length > 0}
      <div class="space-y-1">
        {#each analysisData as group}
          <!-- 统一结构：一行基础信息 + 可选详情 -->
          <div class="group/item cq-padding bg-muted/30 cq-rounded border border-transparent hover:border-primary/30 transition-colors">
            <!-- 主行：名称 + 统计 + 操作 -->
            <div class="flex items-center justify-between cq-gap">
              <span class="truncate flex-1 cq-text font-medium" title={group.key}>{group.name}</span>
              <div class="flex items-center cq-gap shrink-0">
                <span class="cq-text-sm text-muted-foreground tabular-nums">{group.fileCount}</span>
                <span class="cq-wide-only-inline cq-text-sm text-muted-foreground">·</span>
                <span class="cq-wide-only-inline cq-text-sm text-muted-foreground tabular-nums">{group.totalSizeFormatted}</span>
                <span class="cq-text-sm text-orange-600 tabular-nums">{group.avgSizeFormatted}</span>
                <button 
                  class="cq-padding-sm cq-rounded opacity-0 group-hover/item:opacity-100 hover:bg-muted transition-all" 
                  onclick={() => copyGroupPaths(group.key)} 
                  title="复制路径"
                >
                  {#if copiedGroupKey === group.key}<Check class="cq-icon-sm text-green-500" />{:else}<Copy class="cq-icon-sm" />{/if}
                </button>
              </div>
            </div>
            <!-- 详情行：仅宽屏显示 -->
            {#if Object.keys(group.subStats).length > 0}
              <div class="cq-wide-only flex flex-wrap cq-gap-sm mt-1">
                {#each Object.entries(group.subStats).sort((a, b) => b[1] - a[1]).slice(0, 4) as [label, count]}
                  <span class="cq-text-sm px-1 py-0.5 bg-muted rounded">{groupBy === 'ext' ? label : `.${label}`}: {count}</span>
                {/each}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {:else if files.length > 0}
      <div class="text-center text-muted-foreground py-4">
        <currentGroupOption.icon class="cq-icon-lg mx-auto mb-2 opacity-50" />
        <div class="cq-text">无匹配的分组数据</div>
        {#if hasActiveFilter}
          <button class="cq-text-sm text-primary hover:underline mt-1" onclick={resetFilter}>清除过滤</button>
        {/if}
      </div>
    {:else}
      <div class="text-center text-muted-foreground py-4">
        <ChartNoAxesColumn class="cq-icon-lg mx-auto mb-2 opacity-50" />
        <div class="cq-text">搜索后显示分析</div>
      </div>
    {/if}
  </div>

  <!-- 底部统计 + 复制全部 -->
  {#if analysisData.length > 0}
    <div class="cq-padding border-t bg-muted/20 shrink-0 flex items-center justify-between">
      <span class="cq-text-sm text-muted-foreground">
        {analysisData.length}<span class="cq-wide-only-inline">个{currentGroupOption.label}</span><span class="cq-compact-only-inline">组</span>
        · {filteredFileCount}文件
      </span>
      <button class="flex items-center cq-gap-sm cq-text-sm text-primary hover:underline" onclick={copyAllFilteredPaths} title="复制所有过滤结果的文件路径">
        {#if copiedAll}<Check class="cq-icon-sm" /><span class="text-green-600">已复制</span>{:else}<Copy class="cq-icon-sm" /><span>复制全部</span>{/if}
      </button>
    </div>
  {/if}
</div>
