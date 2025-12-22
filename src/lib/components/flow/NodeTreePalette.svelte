<script lang="ts">
  /**
   * NodeTreePalette - 基于 tree-view 的节点树面板
   * 支持分类展示、搜索过滤、JSON 导入导出
   */
  import { NODE_DEFINITIONS } from '$lib/stores/nodeRegistry';
  import { flowStore } from '$lib/stores';
  import * as TreeView from '$lib/components/ui/tree-view';
  import { Search, Download, Upload, Terminal, Package, Folder, FileText } from '@lucide/svelte';

  // 从 localStorage 加载保存的树结构
  const STORAGE_KEY = 'node-tree-layout';

  let searchQuery = $state('');
  let nodeIdCounter = 1;
  let fileInput: HTMLInputElement;

  // 树结构类型
  interface TreeNode {
    id: string;
    name: string;
    type: 'folder' | 'node';
    nodeType?: string;  // 节点类型（仅 type='node' 时有效）
    children?: TreeNode[];
    expanded?: boolean;
  }

  // 默认分类结构
  const defaultTreeData: TreeNode[] = [
    {
      id: 'favorites',
      name: '⭐ 收藏',
      type: 'folder',
      expanded: true,
      children: [],
    },
    {
      id: 'input',
      name: '📥 输入',
      type: 'folder',
      expanded: true,
      children: NODE_DEFINITIONS.filter(n => n.category === 'input').map(n => ({
        id: n.type,
        name: n.label,
        type: 'node' as const,
        nodeType: n.type,
      })),
    },
    {
      id: 'tool',
      name: '🔧 工具',
      type: 'folder',
      expanded: true,
      children: [
        {
          id: 'tool-file',
          name: '📁 文件操作',
          type: 'folder',
          expanded: false,
          children: NODE_DEFINITIONS.filter(n => 
            ['repacku', 'movea', 'dissolvef', 'trename', 'migratef', 'linku'].includes(n.type)
          ).map(n => ({ id: n.type, name: n.label, type: 'node' as const, nodeType: n.type })),
        },
        {
          id: 'tool-archive',
          name: '📦 压缩包',
          type: 'folder',
          expanded: false,
          children: NODE_DEFINITIONS.filter(n => 
            ['bandia', 'rawfilter', 'findz', 'encodeb'].includes(n.type)
          ).map(n => ({ id: n.type, name: n.label, type: 'node' as const, nodeType: n.type })),
        },
        {
          id: 'tool-media',
          name: '🎬 媒体',
          type: 'folder',
          expanded: false,
          children: NODE_DEFINITIONS.filter(n => 
            ['enginev', 'formatv', 'kavvka'].includes(n.type)
          ).map(n => ({ id: n.type, name: n.label, type: 'node' as const, nodeType: n.type })),
        },
        {
          id: 'tool-system',
          name: '💻 系统',
          type: 'folder',
          expanded: false,
          children: NODE_DEFINITIONS.filter(n => 
            ['sleept', 'scoolp', 'reinstallp', 'recycleu', 'owithu'].includes(n.type)
          ).map(n => ({ id: n.type, name: n.label, type: 'node' as const, nodeType: n.type })),
        },
        {
          id: 'tool-text',
          name: '📝 文本',
          type: 'folder',
          expanded: false,
          children: NODE_DEFINITIONS.filter(n => 
            ['linedup', 'crashu', 'seriex'].includes(n.type)
          ).map(n => ({ id: n.type, name: n.label, type: 'node' as const, nodeType: n.type })),
        },
      ],
    },
    {
      id: 'output',
      name: '📤 输出',
      type: 'folder',
      expanded: true,
      children: NODE_DEFINITIONS.filter(n => n.category === 'output').map(n => ({
        id: n.type,
        name: n.label,
        type: 'node' as const,
        nodeType: n.type,
      })),
    },
  ];

  // 加载树数据
  function loadTreeData(): TreeNode[] {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.warn('加载节点树布局失败:', e);
      }
    }
    return defaultTreeData;
  }

  let treeData = $state<TreeNode[]>(loadTreeData());

  // 保存树数据
  function saveTreeData() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(treeData));
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

  // 导出 JSON
  function exportJson() {
    const json = JSON.stringify(treeData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'node-tree-layout.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  // 导入 JSON
  function importJson(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        treeData = data;
        saveTreeData();
      } catch (err) {
        console.error('导入 JSON 失败:', err);
        alert('导入失败：JSON 格式错误');
      }
    };
    reader.readAsText(file);
    input.value = '';  // 重置以便再次选择同一文件
  }

  // 搜索过滤
  function filterNodes(nodes: TreeNode[], query: string): TreeNode[] {
    if (!query) return nodes;
    const q = query.toLowerCase();
    
    return nodes.map(node => {
      if (node.type === 'folder' && node.children) {
        const filteredChildren = filterNodes(node.children, query);
        if (filteredChildren.length > 0) {
          return { ...node, children: filteredChildren, expanded: true };
        }
        return null;
      }
      if (node.name.toLowerCase().includes(q)) {
        return node;
      }
      return null;
    }).filter(Boolean) as TreeNode[];
  }

  // 过滤后的树数据
  let filteredTreeData = $derived(filterNodes(treeData, searchQuery));

  // 文件夹展开状态 - 预先初始化所有文件夹
  function buildInitialFolderStates(nodes: TreeNode[]): Record<string, boolean> {
    const states: Record<string, boolean> = {};
    function traverse(nodes: TreeNode[]) {
      nodes.forEach(node => {
        if (node.type === 'folder') {
          states[node.id] = node.expanded ?? true;
          if (node.children) {
            traverse(node.children);
          }
        }
      });
    }
    traverse(nodes);
    return states;
  }

  let folderStates = $state<Record<string, boolean>>({});
  
  // 初始化文件夹状态
  $effect(() => {
    const newStates = buildInitialFolderStates(treeData);
    // 只添加新的，不覆盖已有的
    for (const [id, expanded] of Object.entries(newStates)) {
      if (folderStates[id] === undefined) {
        folderStates[id] = expanded;
      }
    }
  });

  // 获取文件夹展开状态（确保有默认值）
  function getFolderOpen(id: string): boolean {
    return folderStates[id] ?? true;
  }

  // 设置文件夹展开状态
  function setFolderOpen(id: string, open: boolean) {
    folderStates[id] = open;
  }
</script>

<div class="node-tree-palette h-full flex flex-col">
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
      onclick={exportJson}
      title="导出 JSON"
    >
      <Download class="w-4 h-4" />
    </button>
    <button
      class="p-1.5 rounded hover:bg-muted transition-colors"
      onclick={() => fileInput.click()}
      title="导入 JSON"
    >
      <Upload class="w-4 h-4" />
    </button>
    <input
      bind:this={fileInput}
      type="file"
      accept=".json"
      class="hidden"
      onchange={importJson}
    />
  </div>

  <!-- 树容器 -->
  <div class="flex-1 overflow-auto p-2">
    <TreeView.Root class="text-sm">
      {#each filteredTreeData as node (node.id)}
        {#if node.type === 'folder'}
          <TreeView.Folder name={node.name} open={getFolderOpen(node.id)}>
            {#if node.children}
              {#each node.children as child (child.id)}
                {#if child.type === 'folder'}
                  <TreeView.Folder name={child.name} open={getFolderOpen(child.id)}>
                    {#if child.children}
                      {#each child.children as grandchild (grandchild.id)}
                        <TreeView.File 
                          name={grandchild.name}
                          onclick={() => grandchild.nodeType && addNodeToCanvas(grandchild.nodeType, grandchild.name)}
                          class="hover:bg-muted rounded px-1 cursor-pointer"
                        />
                      {/each}
                    {/if}
                  </TreeView.Folder>
                {:else}
                  <TreeView.File 
                    name={child.name}
                    onclick={() => child.nodeType && addNodeToCanvas(child.nodeType, child.name)}
                    class="hover:bg-muted rounded px-1 cursor-pointer"
                  />
                {/if}
              {/each}
            {/if}
          </TreeView.Folder>
        {:else}
          <TreeView.File 
            name={node.name}
            onclick={() => node.nodeType && addNodeToCanvas(node.nodeType, node.name)}
            class="hover:bg-muted rounded px-1 cursor-pointer"
          />
        {/if}
      {/each}
    </TreeView.Root>
  </div>

  <!-- 提示 -->
  <div class="p-2 border-t text-xs text-muted-foreground">
    点击添加节点 · 导出/导入 JSON 自定义分类
  </div>
</div>
