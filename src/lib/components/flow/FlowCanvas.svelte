<script lang="ts">
  import {
    SvelteFlow,
    Background,
    Controls,
    MiniMap,
    type NodeTypes
  } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css';

  import { flowStore } from '$lib/stores';
  import InputNode from '$lib/components/nodes/InputNode.svelte';
  import ToolNode from '$lib/components/nodes/ToolNode.svelte';
  import OutputNode from '$lib/components/nodes/OutputNode.svelte';

  const nodeTypes: NodeTypes = {
    clipboard_input: InputNode,
    folder_input: InputNode,
    path_input: InputNode,
    tool_repacku: ToolNode,
    tool_samea: ToolNode,
    tool_crashu: ToolNode,
    tool_migratef: ToolNode,
    tool_nameu: ToolNode,
    tool_formatv: ToolNode,
    log_output: OutputNode
  };

  let nodes = $derived($flowStore.nodes as any[]);
  let edges = $derived($flowStore.edges as any[]);
</script>

<div class="h-full w-full">
  <SvelteFlow
    {nodes}
    {edges}
    {nodeTypes}
    onnodeclick={(event) => flowStore.selectNode(event.detail.node.id)}
    onpaneclick={() => flowStore.selectNode(null)}
    onnodeschange={(event) => flowStore.setNodes(event.detail as any)}
    onedgeschange={(event) => flowStore.setEdges(event.detail as any)}
    onconnect={(event) => {
      const conn = event.detail;
      flowStore.addEdge({
        id: `e-${conn.source}-${conn.target}-${Date.now()}`,
        source: conn.source,
        target: conn.target,
        sourceHandle: conn.sourceHandle,
        targetHandle: conn.targetHandle,
        animated: true
      });
    }}
    fitView
    snapToGrid
    deleteKeyCode="Delete"
  >
    <Background />
    <Controls />
    <MiniMap 
      nodeColor={(node) => {
        if (node.type?.startsWith('tool_')) return '#3b82f6';
        if (node.type?.includes('input')) return '#22c55e';
        if (node.type?.includes('output')) return '#f59e0b';
        return '#64748b';
      }}
    />
  </SvelteFlow>
</div>

<style>
  :global(.svelte-flow) {
    background: #f8fafc;
  }
  :global(.svelte-flow__node) {
    cursor: pointer;
  }
</style>
