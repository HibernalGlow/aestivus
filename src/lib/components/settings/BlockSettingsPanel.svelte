<script lang="ts">
  /**
   * 区块管理设置面板
   * 使用 tab 切换不同节点的区块配置
   */
  import { Badge } from '$lib/components/ui/badge';
  import { nodeBlockRegistry } from '$lib/components/blocks/blockRegistry';
  import { LayoutGrid, Eye, EyeOff, Package, FilePenLine } from '@lucide/svelte';

  // 节点类型图标映射
  const nodeIcons: Record<string, typeof Package> = {
    repacku: Package,
    trename: FilePenLine
  };

  // 获取所有节点类型
  const nodeTypes = Object.keys(nodeBlockRegistry);
  
  // 当前选中的节点 tab
  let activeNode = $state<string>(nodeTypes[0] || 'repacku');
</script>

<div class="p-6 space-y-4">
  <!-- 标题 -->
  <div>
    <h3 class="text-lg font-semibold flex items-center gap-2">
      <LayoutGrid class="w-5 h-5" />
      区块管理
    </h3>
    <p class="text-sm text-muted-foreground mt-1">管理各节点的区块显示和布局</p>
  </div>

  <!-- 节点 Tab 切换 -->
  <div class="flex gap-1 border-b">
    {#each nodeTypes as nodeType}
      {@const NodeIcon = nodeIcons[nodeType] || LayoutGrid}
      {@const isActive = activeNode === nodeType}
      <button
        type="button"
        class="flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors {isActive 
          ? 'border-primary text-primary' 
          : 'border-transparent text-muted-foreground hover:text-foreground'}"
        onclick={() => activeNode = nodeType}
      >
        <NodeIcon class="w-4 h-4" />
        {nodeType}
      </button>
    {/each}
  </div>


  <!-- 区块列表 -->
  {#if nodeBlockRegistry[activeNode]}
    {@const layout = nodeBlockRegistry[activeNode]}
    <div class="space-y-2">
      {#each layout.blocks as block}
        {@const BlockIcon = block.icon}
        <div class="flex items-center justify-between p-3 rounded-lg border bg-card hover:border-primary/50 transition-colors">
          <div class="flex items-center gap-3">
            {#if BlockIcon}
              <BlockIcon class="w-4 h-4 {block.iconClass || 'text-muted-foreground'}" />
            {/if}
            <div>
              <span class="font-medium text-sm">{block.title}</span>
              <div class="flex gap-1.5 mt-1">
                {#if block.colSpan === 2}
                  <Badge variant="outline" class="text-[10px] px-1.5 py-0">宽</Badge>
                {/if}
                {#if block.fullHeight}
                  <Badge variant="outline" class="text-[10px] px-1.5 py-0">高</Badge>
                {/if}
                {#if block.collapsible}
                  <Badge variant="outline" class="text-[10px] px-1.5 py-0">可折叠</Badge>
                {/if}
              </div>
            </div>
          </div>
          
          <div class="flex items-center gap-3">
            <!-- 普通模式可见性 -->
            <div class="flex items-center gap-1.5 text-xs">
              <span class="text-muted-foreground">普通</span>
              {#if block.visibleInNormal !== false}
                <Eye class="w-3.5 h-3.5 text-green-500" />
              {:else}
                <EyeOff class="w-3.5 h-3.5 text-muted-foreground/50" />
              {/if}
            </div>
            
            <!-- 全屏模式可见性 -->
            <div class="flex items-center gap-1.5 text-xs">
              <span class="text-muted-foreground">全屏</span>
              {#if block.visibleInFullscreen !== false}
                <Eye class="w-3.5 h-3.5 text-green-500" />
              {:else}
                <EyeOff class="w-3.5 h-3.5 text-muted-foreground/50" />
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>
    
    <!-- 提示 -->
    <div class="text-xs text-muted-foreground p-3 bg-muted/30 rounded-lg">
      💡 区块配置目前为只读。后续版本将支持自定义区块显示和顺序。
    </div>
  {/if}
</div>
