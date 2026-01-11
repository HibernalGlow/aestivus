<script lang="ts">
  import { page } from "$app/stores";
  import { onMount } from "svelte";

  // 动态导入 node 组件
  const nodeComponents: Record<string, any> = {
    sleept: () => import("$lib/components/nodes/sleept/SleeptNode.svelte"),
    recycleu: () =>
      import("$lib/components/nodes/recycleu/RecycleuNode.svelte"),
    formatv: () => import("$lib/components/nodes/formatv/FormatVNode.svelte"),
    bandia: () => import("$lib/components/nodes/bandia/BandiaNode.svelte"),
    cleanf: () => import("$lib/components/nodes/cleanf/CleanfNode.svelte"),
    dissolvef: () =>
      import("$lib/components/nodes/dissolvef/DissolvefNode.svelte"),
    crashu: () => import("$lib/components/nodes/crashu/CrashuNode.svelte"),
    findz: () => import("$lib/components/nodes/findz/FindzNode.svelte"),
    owithu: () => import("$lib/components/nodes/owithu/OwithuNode.svelte"),
    movea: () => import("$lib/components/nodes/movea/MoveaNode.svelte"),
    marku: () => import("$lib/components/nodes/marku/MarkuNode.svelte"),
  };

  let { data } = $props();
  let NodeComponent: any = $state(null);
  let error = $state("");

  const nodeName = $derived($page.params.name);

  onMount(async () => {
    if (nodeComponents[nodeName]) {
      try {
        const module = await nodeComponents[nodeName]();
        NodeComponent = module.default;
      } catch (e) {
        error = `加载 ${nodeName} 组件失败: ${e}`;
      }
    } else {
      error = `未找到 node: ${nodeName}`;
    }
  });
</script>

<svelte:head>
  <title>{nodeName} | Aestivus</title>
</svelte:head>

<div class="h-screen w-screen bg-background overflow-hidden">
  {#if error}
    <div class="flex items-center justify-center h-full">
      <div class="text-center">
        <h1 class="text-2xl font-bold text-destructive mb-2">Error</h1>
        <p class="text-muted-foreground">{error}</p>
      </div>
    </div>
  {:else if NodeComponent}
    <div class="h-full w-full p-4">
      <NodeComponent id="standalone-{nodeName}" isFullscreenRender={true} />
    </div>
  {:else}
    <div class="flex items-center justify-center h-full">
      <div
        class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"
      ></div>
    </div>
  {/if}
</div>
