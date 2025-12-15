<script lang="ts">
  /**
   * 全屏节点模态框
   * 用于以全屏方式显示节点内容
   */
  import { fullscreenNodeStore } from '$lib/stores/fullscreenNode.svelte';
  import { X, Minimize2 } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  
  // 动态导入节点组件
  import TrenameNode from '$lib/components/nodes/TrenameNode.svelte';
  import RepackuNode from '$lib/components/nodes/RepackuNode.svelte';
  import TerminalNode from '$lib/components/nodes/TerminalNode.svelte';
  import CrashuNode from '$lib/components/nodes/CrashuNode.svelte';
  import RawfilterNode from '$lib/components/nodes/RawfilterNode.svelte';

  const nodeComponents: Record<string, any> = {
    trename: TrenameNode,
    repacku: RepackuNode,
    terminal: TerminalNode,
    crashu: CrashuNode,
    rawfilter: RawfilterNode
  };

  function handleClose() {
    fullscreenNodeStore.close();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      handleClose();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if $fullscreenNodeStore.isOpen && $fullscreenNodeStore.nodeType}
  {@const NodeComponent = nodeComponents[$fullscreenNodeStore.nodeType]}
  
  <!-- 背景遮罩 -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div 
    class="fixed inset-0 z-[100] bg-background/80 backdrop-blur-sm"
    onclick={handleClose}
  ></div>
  
  <!-- 全屏内容 -->
  <div class="fixed inset-4 z-[101] bg-card border rounded-lg shadow-2xl flex flex-col overflow-hidden">
    <!-- 标题栏 -->
    <div class="flex items-center justify-between px-4 py-2 border-b bg-muted/30 shrink-0">
      <span class="font-semibold">{$fullscreenNodeStore.nodeType} - 全屏模式</span>
      <div class="flex items-center gap-1">
        <Button variant="ghost" size="icon" class="h-7 w-7" onclick={handleClose} title="退出全屏">
          <Minimize2 class="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="icon" class="h-7 w-7" onclick={handleClose} title="关闭">
          <X class="w-4 h-4" />
        </Button>
      </div>
    </div>
    
    <!-- 节点内容 -->
    <div class="flex-1 overflow-auto p-4">
      {#if NodeComponent}
        <div class="h-full w-full">
          <svelte:component 
            this={NodeComponent} 
            id={$fullscreenNodeStore.nodeId}
            data={$fullscreenNodeStore.nodeData}
          />
        </div>
      {:else}
        <div class="text-muted-foreground text-center py-8">
          不支持全屏显示的节点类型: {$fullscreenNodeStore.nodeType}
        </div>
      {/if}
    </div>
  </div>
{/if}
