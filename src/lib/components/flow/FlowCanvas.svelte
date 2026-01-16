<script lang="ts">
  import { onMount, tick } from "svelte";
  import {
    SvelteFlow,
    SvelteFlowProvider,
    Background,
    Controls,
    MiniMap,
    Panel,
    type NodeTypes,
    type Node,
    type Edge,
    SelectionMode,
  } from "@xyflow/svelte";
  import "@xyflow/svelte/dist/style.css";
  import ELK from "elkjs/lib/elk.bundled.js";

  import { flowStore } from "$lib/stores";
  import { getNodeTypes } from "$lib/stores/nodeRegistry";
  import NodeContextMenu from "./NodeContextMenu.svelte";
  import CanvasContextMenu from "./CanvasContextMenu.svelte";

  let nodeIdCounter = 1;
  let containerRef: HTMLDivElement;

  // 使用 $derived 确保节点变化时自动更新
  // 深拷贝节点确保 SvelteFlow 检测到属性变化（如 draggable）
  let nodes = $derived($flowStore.nodes.map((n) => ({ ...n })) as any[]);
  let edges = $derived($flowStore.edges.map((e) => ({ ...e })) as any[]);

  // 从注册表获取节点类型映射
  const nodeTypes: NodeTypes = getNodeTypes();

  function handleKeyDown(e: KeyboardEvent) {
    // 如果焦点在输入框、文本域等可编辑元素内，不处理删除键
    const target = e.target as HTMLElement;
    const isEditable =
      target.tagName === "INPUT" ||
      target.tagName === "TEXTAREA" ||
      target.isContentEditable ||
      target.closest('input, textarea, [contenteditable="true"]');

    if (isEditable) {
      return; // 让输入框正常处理 Backspace/Delete
    }

    if (
      (e.key === "Delete" || e.key === "Backspace") &&
      $flowStore.selectedNodeId
    ) {
      e.preventDefault();
      flowStore.removeNode($flowStore.selectedNodeId);
    }
  }

  // 处理拖拽放置
  function handleDrop(event: DragEvent) {
    event.preventDefault();

    const data = event.dataTransfer?.getData("application/json");
    if (!data) return;

    try {
      const { type, label, nodeId: providedNodeId } = JSON.parse(data);

      // 获取容器的边界
      const bounds = containerRef?.getBoundingClientRect();
      if (!bounds) return;

      // 计算相对于容器的位置
      const position = {
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      };

      // 使用传入的 nodeId 或生成新的
      const nodeId = providedNodeId || `node-${nodeIdCounter++}-${Date.now()}`;

      const node = {
        id: nodeId,
        type,
        position,
        data: { label, status: "idle" as const },
      };

      flowStore.addNode(node);
    } catch (e) {
      console.error("Failed to parse drop data:", e);
    }
  }

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "move";
    }
  }

  // 记录节点的原始位置，用于固定节点时恢复
  let pinnedPositions: Map<string, { x: number; y: number }> = new Map();

  // 监听 flowStore 变化，记录固定节点的位置
  $effect(() => {
    $flowStore.nodes.forEach((node) => {
      if (node.draggable === false && node.position) {
        pinnedPositions.set(node.id, { ...node.position });
      } else {
        pinnedPositions.delete(node.id);
      }
    });
  });

  // Minimap 调整大小逻辑
  let miniMapWidth = $state(200);
  let miniMapHeight = $state(150);
  let isResizing = $state(false);

  function handleResizePointerDown(e: PointerEvent) {
    e.preventDefault();
    e.stopPropagation();
    isResizing = true;

    const startX = e.clientX;
    const startY = e.clientY;
    const startWidth = miniMapWidth;
    const startHeight = miniMapHeight;

    function onPointerMove(moveEvent: PointerEvent) {
      if (!isResizing) return;
      // 由于 minimap 在右下角，向左上方拖拽会增加宽高
      const deltaX = startX - moveEvent.clientX;
      const deltaY = startY - moveEvent.clientY;

      miniMapWidth = Math.max(100, startWidth + deltaX);
      miniMapHeight = Math.max(80, startHeight + deltaY);
    }

    function onPointerUp() {
      isResizing = false;
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    }

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  }

  onMount(() => {
    const saved = localStorage.getItem("aestivus-minimap-size");
    if (saved) {
      try {
        const { w, h } = JSON.parse(saved);
        miniMapWidth = w;
        miniMapHeight = h;
      } catch (e) {}
    }
  });

  $effect(() => {
    if (!isResizing) {
      localStorage.setItem(
        "aestivus-minimap-size",
        JSON.stringify({ w: miniMapWidth, h: miniMapHeight })
      );
    }
  });

  // 右键菜单状态
  let nodeContextMenu = $state<{ id: string; x: number; y: number } | null>(
    null
  );
  let canvasContextMenu = $state<{ x: number; y: number } | null>(null);

  function handleNodeContextMenu({
    event,
    node,
  }: {
    event: MouseEvent;
    node: any;
  }) {
    event.preventDefault();
    canvasContextMenu = null; // 关闭画布菜单
    nodeContextMenu = {
      id: node.id,
      x: event.clientX,
      y: event.clientY,
    };
  }

  function handlePaneContextMenu({ event }: { event: MouseEvent }) {
    event.preventDefault();
    nodeContextMenu = null; // 关闭节点菜单
    canvasContextMenu = {
      x: event.clientX,
      y: event.clientY,
    };
  }

  // 自动布局逻辑 (ELK)
  const elk = new ELK();

  async function handleAutoLayout() {
    const elkNodes = nodes.map((n) => ({
      id: n.id,
      width: 250, // 假设节点平均宽度
      height: 150, // 假设节点平均高度
    }));

    const elkEdges = edges.map((e) => ({
      id: e.id,
      sources: [e.source],
      targets: [e.target],
    }));

    const graph = {
      id: "root",
      layoutOptions: {
        "elk.algorithm": "layered",
        "elk.direction": "RIGHT",
        "elk.spacing.nodeNode": "80",
        "elk.layered.spacing.nodeNodeLayered": "100",
      },
      children: elkNodes,
      edges: elkEdges,
    };

    try {
      const layoutedGraph = await elk.layout(graph);

      layoutedGraph.children?.forEach((node) => {
        if (node.x !== undefined && node.y !== undefined) {
          flowStore.updateNode(node.id, {
            position: { x: node.x, y: node.y },
          });
        }
      });

      // 等待 DOM 更新后调整视图
      await tick();
    } catch (e) {
      console.error("Layout failed:", e);
    }
  }

  // 监听外部布局触发器
  $effect(() => {
    if ($flowStore.layoutTrigger) {
      handleAutoLayout();
    }
  });
</script>

<svelte:window onkeydown={handleKeyDown} />

<SvelteFlowProvider>
  <div
    bind:this={containerRef}
    class="h-full w-full"
    ondrop={handleDrop}
    ondragover={handleDragOver}
    role="application"
  >
    <SvelteFlow
      {nodes}
      {edges}
      {nodeTypes}
      onnodeclick={({ node }) => flowStore.selectNode(node.id)}
      onnodecontextmenu={handleNodeContextMenu}
      selectionMode={SelectionMode.Partial}
      selectionOnDrag={true}
      onnodedragstop={({ targetNode }) => {
        // 检查节点是否被固定
        const originalPos = pinnedPositions.get(targetNode.id);
        if (originalPos) {
          // 固定节点：恢复到原始位置
          flowStore.updateNode(targetNode.id, { position: originalPos });
        } else {
          // 非固定节点：更新到新位置
          flowStore.updateNode(targetNode.id, {
            position: targetNode.position,
          });
        }
      }}
      onpaneclick={() => {
        flowStore.selectNode(null);
        nodeContextMenu = null;
        canvasContextMenu = null;
      }}
      onpanecontextmenu={handlePaneContextMenu}
      onconnect={(conn) => {
        flowStore.addEdge({
          id: `e-${conn.source}-${conn.target}-${Date.now()}`,
          source: conn.source,
          target: conn.target,
          sourceHandle: conn.sourceHandle,
          targetHandle: conn.targetHandle,
          animated: true,
        });
      }}
      ondelete={({ nodes: deletedNodes, edges: deletedEdges }) => {
        deletedNodes?.forEach((n) => flowStore.removeNode(n.id));
        deletedEdges?.forEach((e) => flowStore.removeEdge(e.id));
      }}
      fitView
      snapGrid={[15, 15]}
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={20} class="opacity-10" />
      <Controls />
      <MiniMap
        width={miniMapWidth}
        height={miniMapHeight}
        position="bottom-right"
        nodeColor={(node) => {
          if (
            node.type === "repacku" ||
            node.type === "rawfilter" ||
            node.type === "crashu" ||
            node.type === "trename"
          )
            return "#3b82f6";
          if (node.type?.includes("input")) return "#22c55e";
          if (node.type?.includes("output") || node.type === "terminal")
            return "#f59e0b";
          return "#64748b";
        }}
      />

      {#if nodeContextMenu}
        <NodeContextMenu
          id={nodeContextMenu.id}
          x={nodeContextMenu.x}
          y={nodeContextMenu.y}
          onClose={() => (nodeContextMenu = null)}
          onDelete={(id) => flowStore.removeNode(id)}
          onDuplicate={(id) => flowStore.duplicateNode(id)}
        />
      {/if}

      {#if canvasContextMenu}
        <CanvasContextMenu
          x={canvasContextMenu.x}
          y={canvasContextMenu.y}
          onClose={() => (canvasContextMenu = null)}
          onAutoLayout={handleAutoLayout}
        />
      {/if}

      <!-- Minimap Resize Handle -->
      <div
        class="minimap-resize-handle"
        class:resizing={isResizing}
        style="right: {miniMapWidth + 15 - 10}px; bottom: {miniMapHeight +
          15 -
          10}px;"
        onpointerdown={handleResizePointerDown}
        role="button"
        tabindex="0"
        aria-label="Resize minimap"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
          ><path d="m15 15 6 6" /><path d="m9 9-6-6" /><path
            d="M21 15v6h-6"
          /><path d="M9 3H3v6" /></svg
        >
      </div>
    </SvelteFlow>
  </div>
</SvelteFlowProvider>

<style>
  :global(.svelte-flow) {
    background: transparent !important;
  }
  :global(.svelte-flow__selection) {
    background: color-mix(in srgb, var(--primary) 10%, transparent) !important;
    border: 1px solid var(--primary) !important;
    border-radius: 4px;
  }
  :global(.svelte-flow__node) {
    cursor: pointer;
    overflow: hidden !important;
  }
  /* 确保节点内容正确继承高度 */
  :global(.svelte-flow__node > div) {
    height: 100% !important;
    overflow: hidden !important;
  }
  :global(.svelte-flow__background) {
    opacity: 0.3;
  }
  /* Controls 工具栏样式 */
  :global(.svelte-flow__controls) {
    background: color-mix(in srgb, var(--card) 85%, transparent) !important;
    backdrop-filter: blur(12px);
    border: none !important;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  }
  :global(.svelte-flow__controls-button) {
    background: transparent !important;
    border: none !important;
    color: var(--foreground) !important;
    fill: var(--foreground) !important;
  }
  :global(.svelte-flow__controls-button:hover) {
    background: color-mix(in srgb, var(--muted) 80%, transparent) !important;
  }
  :global(.svelte-flow__controls-button svg) {
    fill: currentColor !important;
  }
  /* MiniMap 样式 */
  :global(.svelte-flow__minimap) {
    background: color-mix(in srgb, var(--card) 85%, transparent) !important;
    backdrop-filter: blur(12px);
    border: none !important;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  }
  :global(.svelte-flow__minimap-mask) {
    fill: color-mix(in srgb, var(--background) 60%, transparent) !important;
  }

  /* Minimap Resize Handle Style */
  .minimap-resize-handle {
    position: absolute;
    z-index: 1001;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: color-mix(in srgb, var(--card) 85%, transparent);
    backdrop-filter: blur(12px);
    border: 1px solid color-mix(in srgb, var(--border) 50%, transparent);
    border-radius: 4px;
    cursor: nwse-resize;
    color: var(--muted-foreground);
    transition: all 0.2s;
    opacity: 0;
    pointer-events: auto;
  }

  :global(.svelte-flow:hover) .minimap-resize-handle {
    opacity: 1;
  }

  .minimap-resize-handle:hover,
  .minimap-resize-handle.resizing {
    opacity: 1;
    color: var(--primary);
    background: var(--card);
    border-color: var(--primary);
    box-shadow: 0 0 10px color-mix(in srgb, var(--primary) 20%, transparent);
  }

  .minimap-resize-handle svg {
    transform: rotate(0deg);
  }

  .minimap-resize-handle svg {
    transform: rotate(0deg);
  }
</style>
