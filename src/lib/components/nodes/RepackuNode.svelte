<script lang="ts">
  import BaseNode from './BaseNode.svelte';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Label } from '$lib/components/ui/label';
  import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '$lib/components/ui/select';
  import { api } from '$lib/services/api';
  
  // Props from SvelteFlow
  export let id: string;
  export let data: {
    config: {
      path: string;
      types: string[];
      delete_after: boolean;
    };
    status: 'idle' | 'running' | 'completed' | 'error';
    hasInputConnection: boolean;
    logs: string[];
  };
  
  // 类型选项
  const typeOptions = [
    { value: 'all', label: '全部类型' },
    { value: 'image', label: '图片' },
    { value: 'document', label: '文档' },
    { value: 'video', label: '视频' }
  ];
  
  let selectedType = 'all';
  
  // 执行节点
  async function handleExecute() {
    data.status = 'running';
    data.logs = [...data.logs, `开始执行 repacku...`];
    
    try {
      const result = await api.executeNode('repacku', {
        path: data.config.path,
        types: selectedType === 'all' ? [] : [selectedType],
        delete_after: data.config.delete_after
      });
      
      if (result.success) {
        data.status = 'completed';
        data.logs = [...data.logs, result.message];
      } else {
        data.status = 'error';
        data.logs = [...data.logs, `错误: ${result.message}`];
      }
    } catch (error) {
      data.status = 'error';
      data.logs = [...data.logs, `执行失败: ${error}`];
    }
  }
</script>

<BaseNode
  {id}
  icon="📦"
  displayName="文件重打包"
  bind:status={data.status}
  bind:hasInputConnection={data.hasInputConnection}
  bind:path={data.config.path}
  bind:logs={data.logs}
  onExecute={handleExecute}
>
  <div slot="config" class="space-y-3">
    <!-- 类型过滤 -->
    <div class="space-y-1">
      <Label class="text-xs">文件类型</Label>
      <Select bind:value={selectedType}>
        <SelectTrigger class="h-8">
          <SelectValue placeholder="选择类型" />
        </SelectTrigger>
        <SelectContent>
          {#each typeOptions as option}
            <SelectItem value={option.value}>{option.label}</SelectItem>
          {/each}
        </SelectContent>
      </Select>
    </div>
    
    <!-- 删除源文件选项 -->
    <div class="flex items-center gap-2">
      <Checkbox 
        id="delete-after-{id}" 
        bind:checked={data.config.delete_after}
        disabled={data.status === 'running'}
      />
      <Label for="delete-after-{id}" class="text-xs cursor-pointer">
        压缩后删除源文件
      </Label>
    </div>
  </div>
</BaseNode>
