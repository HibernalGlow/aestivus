<script lang="ts">
  import { goto } from '$app/navigation';
  import { Button } from "$lib/components/ui/button";
  import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
  } from "$lib/components/ui/card";
  import { Plus, Workflow, Clock, Trash2 } from '@lucide/svelte';

  interface FlowItem {
    id: string;
    name: string;
    description?: string;
    updatedAt: string;
    nodeCount: number;
  }

  let flows = $state<FlowItem[]>([]);
  let loading = $state(true);

  async function loadFlows() {
    loading = true;
    try {
      const saved = localStorage.getItem('aestival_flows');
      if (saved) {
        flows = JSON.parse(saved);
      }
    } catch (e) {
      console.error('加载流程列表失败:', e);
    }
    loading = false;
  }

  function createNewFlow() {
    goto('/flow/new');
  }

  function openFlow(id: string) {
    goto(`/flow/${id}`);
  }

  function deleteFlow(id: string, event: MouseEvent) {
    event.stopPropagation();
    if (confirm('确定删除此流程？')) {
      flows = flows.filter(f => f.id !== id);
      localStorage.setItem('aestival_flows', JSON.stringify(flows));
    }
  }

  function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  $effect(() => {
    loadFlows();
  });
</script>

<div class="min-h-screen w-full bg-gray-50">
  <header class="bg-white border-b border-gray-200">
    <div class="mx-auto max-w-7xl px-6 py-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">AestivalFlow</h1>
          <p class="text-sm text-gray-500 mt-1">Python工具链可视化编排平台</p>
        </div>
        <Button onclick={createNewFlow}>
          <Plus class="w-4 h-4 mr-2" />
          新建流程
        </Button>
      </div>
    </div>
  </header>

  <main class="mx-auto max-w-7xl px-6 py-8">
    {#if loading}
      <div class="text-center py-12 text-gray-500">加载中...</div>
    {:else if flows.length === 0}
      <Card class="text-center py-16">
        <CardContent>
          <Workflow class="w-16 h-16 mx-auto text-gray-300 mb-4" />
          <h3 class="text-lg font-medium text-gray-900 mb-2">暂无流程</h3>
          <p class="text-gray-500 mb-6">创建第一个流程，开始可视化编排你的Python工具</p>
          <Button onclick={createNewFlow}>
            <Plus class="w-4 h-4 mr-2" />
            创建流程
          </Button>
        </CardContent>
      </Card>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {#each flows as flow}
          <Card 
            class="cursor-pointer hover:shadow-md transition-shadow"
            onclick={() => openFlow(flow.id)}
          >
            <CardHeader class="pb-2">
              <div class="flex items-start justify-between">
                <CardTitle class="text-lg">{flow.name}</CardTitle>
                <button
                  class="p-1 text-gray-400 hover:text-red-500 transition-colors"
                  onclick={(e) => deleteFlow(flow.id, e)}
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
              {#if flow.description}
                <CardDescription>{flow.description}</CardDescription>
              {/if}
            </CardHeader>
            <CardContent>
              <div class="flex items-center gap-4 text-sm text-gray-500">
                <span class="flex items-center gap-1">
                  <Workflow class="w-4 h-4" />
                  {flow.nodeCount} 节点
                </span>
                <span class="flex items-center gap-1">
                  <Clock class="w-4 h-4" />
                  {formatDate(flow.updatedAt)}
                </span>
              </div>
            </CardContent>
          </Card>
        {/each}
      </div>
    {/if}
  </main>
</div>
