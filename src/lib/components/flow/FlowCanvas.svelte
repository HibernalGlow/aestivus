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

  function handleKeyDown(e: KeyboardEvent) {
    if ((e.key === 'Delete' || e.key === 'Backspace') && $flowStore.selectedNodeId) {
      e.preventDefault();
      flowStore.removeNode($flowStore.selectedNodeId);
    }
  }
</script>

<svelte:window onkeydown={handleKeyDown} />

<div class="h-full w-full">
  <SvelteFlow
    {nodes}
    {edges}
    {nodeTypes}
    onnodeclick={(event) => flowStore.selectNode(event.detail.node.id)}
    onpaneclick={() => flowStore.selectNode(null)}
    onnodeschange={(event) => {
      const changes = event.detail;
      if (Array.isArray(changes)) {
        const currentNodes = $flowStore.nodes;
        let newNodes = [...currentNodes];
        for (const change of changes) {
          if (change.type === 'remove') {
            newNodes = newNodes.filter(n => n.id !== change.id);
          } else if (change.type === 'position' && change.position) {
            newNodes = newNodes.map(n => 
              n.id === change.id ? { ...n, position: change.position } : n
            );
          } else if (change.type === 'select') {
            newNodes = newNodes.map(n =>
              n.id === change.id ? { ...n, selected: change.selected } : n
            );
          }
        }
        flowStore.setNodes(newNodes as any);
      }
    }}
    onedgeschange={(event) => {
      const changes = event.detail;
      if (Array.isArray(changes)) {
        const currentEdges = $flowStore.edges;
        let newEdges = [...currentEdges];
        for (const change of changes) {
          if (change.type === 'remove') {
            newEdges = newEdges.filter(e => e.id !== change.id);
          } else if (change.type === 'select') {
            newEdges = newEdges.map(e =>
              e.id === change.id ? { ...e, selected: change.selected } : e
            );
          }
        }
        flowStore.setEdges(newEdges as any);
      }
    }}
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
