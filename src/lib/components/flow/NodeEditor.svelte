<script lang="ts">
  import { flowStore, selectedNode } from '$lib/stores';
  import { getNodeDefinition } from '$lib/stores/nodeRegistry';
  import type { SchemaField } from '$lib/types';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { X, Trash2, FolderOpen } from '@lucide/svelte';

  let node = $derived($selectedNode);
  let definition = $derived(node?.type ? getNodeDefinition(node.type) : null);
  let schema = $derived(definition?.configSchema ?? {});

  function updateParam(key: string, value: any) {
    if (!node) return;
    const currentParams = (node.data.params as Record<string, any>) ?? {};
    flowStore.updateNodeData(node.id, {
      params: { ...currentParams, [key]: value }
    });
  }

  function getParamValue(key: string, field: SchemaField): any {
    if (!node) return field.default ?? '';
    const params = (node.data.params as Record<string, any>) ?? {};
    return params[key] ?? field.default ?? '';
  }

  function deleteNode() {
    if (!node) return;
    flowStore.removeNode(node.id);
  }

  function close() {
    flowStore.selectNode(null);
  }

  async function selectFolder(key: string) {
    const path = prompt('请输入目录路径:');
    if (path) updateParam(key, path);
  }

  async function selectFile(key: string) {
    const path = prompt('请输入文件路径:');
    if (path) updateParam(key, path);
  }
</script>

{#if node && definition}
  <div class="w-80 bg-white border-l border-gray-200 flex flex-col h-full">
    <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200">
      <div>
        <h3 class="font-semibold text-gray-900">{definition.label}</h3>
        <p class="text-xs text-gray-500">{node.type}</p>
      </div>
      <button 
        class="p-1 hover:bg-gray-100 rounded transition-colors"
        onclick={close}
      >
        <X class="w-5 h-5 text-gray-500" />
      </button>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-4">
      <div>
        <Label for="node-label">节点名称</Label>
        <Input
          id="node-label"
          value={node.data.label}
          oninput={(e) => flowStore.updateNodeData(node.id, { label: e.currentTarget.value })}
          class="mt-1"
        />
      </div>

      {#if Object.keys(schema).length > 0}
        <div class="border-t border-gray-100 pt-4">
          <h4 class="text-sm font-medium text-gray-700 mb-3">参数配置</h4>
          
          {#each Object.entries(schema) as [key, field]}
            {@const f = field as SchemaField}
            <div class="mb-3">
              <Label for={`param-${key}`} class="flex items-center gap-1">
                {f.label || key}
                {#if f.required}
                  <span class="text-red-500">*</span>
                {/if}
              </Label>
              
              {#if f.description}
                <p class="text-xs text-gray-400 mb-1">{f.description}</p>
              {/if}

              {#if f.type === 'select' && f.options}
                <select
                  id={`param-${key}`}
                  class="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={getParamValue(key, f)}
                  onchange={(e) => updateParam(key, e.currentTarget.value)}
                >
                  {#each f.options as opt}
                    <option value={opt}>{opt}</option>
                  {/each}
                </select>

              {:else if f.type === 'number'}
                <Input
                  id={`param-${key}`}
                  type="number"
                  value={getParamValue(key, f)}
                  oninput={(e) => updateParam(key, parseFloat(e.currentTarget.value))}
                  class="mt-1"
                />

              {:else if f.type === 'boolean'}
                <label class="flex items-center gap-2 mt-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={getParamValue(key, f)}
                    onchange={(e) => updateParam(key, e.currentTarget.checked)}
                    class="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span class="text-sm text-gray-600">启用</span>
                </label>

              {:else if f.type === 'path'}
                <div class="flex gap-2 mt-1">
                  <Input
                    id={`param-${key}`}
                    value={getParamValue(key, f)}
                    oninput={(e) => updateParam(key, e.currentTarget.value)}
                    placeholder="输入路径或点击选择"
                    class="flex-1"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onclick={() => selectFile(key)}
                    class="shrink-0"
                  >
                    <FolderOpen class="w-4 h-4" />
                  </Button>
                </div>

              {:else}
                <Input
                  id={`param-${key}`}
                  value={getParamValue(key, f)}
                  oninput={(e) => updateParam(key, e.currentTarget.value)}
                  class="mt-1"
                />
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="p-4 border-t border-gray-200">
      <Button
        variant="destructive"
        class="w-full"
        onclick={deleteNode}
      >
        <Trash2 class="w-4 h-4 mr-2" />
        删除节点
      </Button>
    </div>
  </div>
{/if}
