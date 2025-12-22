<script lang="ts">
  /**
   * NodeTreePalette - 基于 Wunderbaum 的节点树面板
   * 支持拖拽排序、虚拟文件夹、搜索过滤
   */
  import { onMount, onDestroy } from 'svelte';
  import { Wunderbaum } from 'wunderbaum';
  import 'wunderbaum/dist/wunderbaum.css';
  import { NODE_DEFINITIONS } from '$lib/stores/nodeRegistry';
  import { flowStore } from '$lib/stores';
  import { Search, FolderPlus, RotateCcw } from '@lucide/svelte';

  // 从 localStorage 加载保存的树结构
  const STORAGE_KEY = 'node-tree-layout';
  
  let treeContainer: HTMLDivElement;
  let tree: Wunderbaum | null = null;
  let searchQuery = $state('');
  let nodeIdCounter = 1;

  // 工具节点子分类
  const toolSubcategories = [
    { id: 'file', label: '📁 文件操作', types: ['repacku', 'movea', 'dissolvef', 'trename', 'migratef', 'linku'] },
    { id: 'archive', label: '📦 压缩包', types: ['bandia', 'rawfilter', 'findz', 'encodeb'] },
    { id: 'media', label: '🎬 媒体', types: ['enginev', 'formatv', 'kavvka'] },
    { id: 'system', label: '💻 系统', types: ['sleept', 'scoolp', 'reinstallp', 'recycleu', 'owithu'] },
    { id: 'text', label: '📝 文本', types: ['linedup', 'crashu', 'seriex'] },
  ];

  // 构建树数据
  function buildTreeData(): any[] {
    // 尝试从 localStorage 加载
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.warn('加载节点树布局失败:', e);
      }
    }

    // 默认结构
    const data: any[] = [];

    // 收藏夹（空）
    data.push({
      title: '⭐ 收藏',
      key: 'favorites',
      type: 'folder',
      expanded: true,
      children: [],
    });

    // 输入节点
    const inputNodes = NODE_DEFINITIONS.filter(n => n.category === 'input');
    data.push({
      title: '📥 输入',
      key: 'input',
      type: 'folder',
      expanded: true,
      children: inputNodes.map(n => ({
        title: n.label,
        key: n.type,
        nodeType: n.type,
      })),
    });

    // 工具节点（分子类）
    const toolChildren = toolSubcategories.map(sub => {
      const nodes = NODE_DEFINITIONS.filter(n => sub.types.includes(n.type));
      return {
        title: sub.label,
        key: `tool-${sub.id}`,
        type: 'folder',
        expanded: false,
        children: nodes.map(n => ({
          title: n.label,
          key: n.type,
          nodeType: n.type,
        })),
      };
    }).filter(sub => sub.children.length > 0);

    data.push({
      title: '🔧 工具',
      key: 'tool',
      type: 'folder',
      expanded: true,
      children: toolChildren,
    });

    // 输出节点
    const outputNodes = NODE_DEFINITIONS.filter(n => n.category === 'output');
    data.push({
      title: '📤 输出',
      key: 'output',
      type: 'folder',
      expanded: true,
      children: outputNodes.map(n => ({
        title: n.label,
        key: n.type,
        nodeType: n.type,
      })),
    });

    return data;
  }

  // 保存树结构到 localStorage
  function saveTreeLayout() {
    if (!tree) return;
    // 手动序列化树结构
    const serializeNode = (node: any): any => {
      const data: any = {
        title: node.title,
        key: node.key,
      };
      if (node.type) data.type = node.type;
      if (node.data?.nodeType) data.nodeType = node.data.nodeType;
      if (node.expanded) data.expanded = node.expanded;
      if (node.children && node.children.length > 0) {
        data.children = node.children.map(serializeNode);
      }
      return data;
    };
    
    const rootChildren = tree.root.children || [];
    const data = rootChildren.map(serializeNode);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }

  // 添加节点到画布
  function addNodeToCanvas(nodeType: string, label: string) {
    const node = {
      id: `node-${nodeIdCounter++}-${Date.now()}`,
      type: nodeType,
      position: { x: 250 + Math.random() * 100, y: 150 + Math.random() * 100 },
      data: { label, status: 'idle' as const },
    };
    flowStore.addNode(node);
  }

  // 创建新文件夹
  function createFolder() {
    if (!tree) return;
    const activeNode = tree.getActiveNode();
    const parent = activeNode?.type === 'folder' ? activeNode : tree.root;
    
    parent.addChildren({
      title: '📁 新文件夹',
      key: `folder-${Date.now()}`,
      type: 'folder',
      expanded: true,
      children: [],
    });
    saveTreeLayout();
  }

  // 重置布局
  function resetLayout() {
    localStorage.removeItem(STORAGE_KEY);
    if (tree) {
      tree.clear();
      tree.load(buildTreeData());
    }
  }

  // 搜索过滤
  function handleSearch() {
    if (!tree) return;
    if (searchQuery) {
      tree.filterNodes(searchQuery, { mode: 'hide' });
    } else {
      tree.clearFilter();
    }
  }

  onMount(() => {
    tree = new Wunderbaum({
      element: treeContainer,
      source: buildTreeData(),
      // 启用拖拽
      dnd: {
        effectAllowed: 'all',
        dropEffectDefault: 'move',
        guessDropEffect: true,
        dragStart: (e) => {
          // 所有节点都可以拖
          return true;
        },
        dragEnter: (e) => {
          // 文件夹可以放入，非文件夹只能放在前后
          if (e.node.type === 'folder') {
            return 'over';
          }
          return new Set(['before', 'after'] as const);
        },
        drag: () => {},
        drop: (e) => {
          // 执行移动
          if (e.sourceNode && e.suggestedDropMode) {
            e.sourceNode.moveTo(e.node, e.suggestedDropMode);
            saveTreeLayout();
          }
        },
      },
      // 点击事件
      click: (e) => {
        const node = e.node;
        if (node.type !== 'folder' && node.data.nodeType) {
          addNodeToCanvas(node.data.nodeType, node.title);
        }
      },
      // 双击展开/折叠
      dblclick: (e) => {
        if (e.node.type === 'folder') {
          e.node.setExpanded(!e.node.expanded);
        }
      },
    });
  });

  onDestroy(() => {
    tree = null;
  });

  // 监听搜索变化
  $effect(() => {
    if (searchQuery !== undefined) {
      handleSearch();
    }
  });
</script>

<div class="node-tree-palette h-full flex flex-col bg-card">
  <!-- 工具栏 -->
  <div class="p-2 border-b flex items-center gap-2">
    <div class="relative flex-1">
      <Search class="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
      <input
        type="text"
        placeholder="搜索节点..."
        class="w-full pl-8 pr-2 py-1.5 text-sm rounded border bg-background"
        bind:value={searchQuery}
      />
    </div>
    <button
      class="p-1.5 rounded hover:bg-muted transition-colors"
      onclick={createFolder}
      title="新建文件夹"
    >
      <FolderPlus class="w-4 h-4" />
    </button>
    <button
      class="p-1.5 rounded hover:bg-muted transition-colors"
      onclick={resetLayout}
      title="重置布局"
    >
      <RotateCcw class="w-4 h-4" />
    </button>
  </div>

  <!-- 树容器 -->
  <div class="flex-1 overflow-auto p-2">
    <div bind:this={treeContainer} class="wunderbaum-container"></div>
  </div>

  <!-- 提示 -->
  <div class="p-2 border-t text-xs text-muted-foreground">
    点击添加节点 · 拖拽排序 · 双击展开
  </div>
</div>

<style>
  /* Wunderbaum 主题适配 */
  :global(.wunderbaum) {
    --wb-font-family: inherit;
    --wb-font-size: 13px;
    --wb-node-height: 28px;
    --wb-icon-width: 1.2em;
    --wb-indent: 1.2em;
    --wb-color-hover: hsl(var(--muted));
    --wb-color-active: hsl(var(--accent));
    --wb-color-selected: hsl(var(--accent));
  }

  :global(.wunderbaum .wb-row) {
    border-radius: 4px;
    margin: 1px 0;
  }

  :global(.wunderbaum .wb-row:hover) {
    background: hsl(var(--muted) / 0.5);
  }

  :global(.wunderbaum .wb-row.wb-active) {
    background: hsl(var(--accent));
  }

  :global(.wunderbaum .wb-node.wb-folder > .wb-row .wb-title) {
    font-weight: 500;
  }

  /* 拖拽指示器 */
  :global(.wunderbaum .wb-row.wb-drag-over) {
    outline: 2px dashed hsl(var(--primary));
    outline-offset: -2px;
  }

  :global(.wunderbaum .wb-row.wb-drop-target) {
    background: hsl(var(--primary) / 0.1);
  }
</style>
